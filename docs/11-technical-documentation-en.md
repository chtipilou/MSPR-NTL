# Technical documentation (English)

WMS database for NordTransit Logistics. PostgreSQL 17 high availability cluster. This document is the English counterpart of the French deliverables, as required by the assignment.

## 1. Context

NordTransit Logistics runs four sites (headquarters in Lille, warehouses in Lens, Valenciennes and Arras) plus a seasonal cross-dock. The Warehouse Management System (WMS) is the core business application. If its database goes down, receiving and shipping stop on all four sites between 5:30 and 18:30. Maintenance windows are short and mostly at night.

The target service levels are a Recovery Time Objective of one hour and a Recovery Point Objective of fifteen minutes.

## 2. Database engine choice

The original subject described MySQL. We selected PostgreSQL 17 for reasons directly tied to the requirements.

- Mature high availability through streaming replication and Patroni, with automatic failover.
- Point in time recovery and block level incremental backups through pgBackRest, which gives a very short RPO.
- Row Level Security for per client data isolation, enforced by the engine.
- SCRAM-SHA-256 authentication and native TLS.
- BRIN indexes, well suited to the large time ordered movements table.
- Open source, no licensing cost for the high availability stack.

Only the engine changes. The functional scope of the subject is preserved.

## 3. Architecture

Three virtual machines on the 192.168.10.0/24 network.

- pgsql-01 at 192.168.10.61, primary PostgreSQL node, managed by Patroni.
- pgsql-02 at 192.168.10.60, streaming replica, failover candidate.
- pgsql-lb at 192.168.10.62, etcd, HAProxy, PgBouncer and the pgBackRest repository.

Patroni arbitrates the primary election through etcd. HAProxy queries the Patroni REST API and routes writes to the current primary on port 5000 and reads to the replica on port 5001. During a failover, the load balancer follows the new primary automatically, with no configuration change. Physical replication uses a slot, so the primary keeps the WAL the replica needs even if it disconnects briefly.

| Component | Version | Role |
|-----------|---------|------|
| PostgreSQL | 17.10 | Database engine, one primary and one replica |
| Patroni | 4.0.7 | High availability orchestration and automatic failover |
| etcd | 3.5 | Cluster store, leader election |
| HAProxy | 3.0 | Load balancer, read and write split |
| PgBouncer | 1.24 | Transaction pooling |
| pgBackRest | 2.55 | Backups and WAL archiving |

## 4. Data model

The wms schema covers six entities, clients, sites, articles or SKU, locations, current stock and movements. Integrity is explicit.

- Per client separation through composite foreign keys (article_id, client_id) on stock and movements, which makes a cross client record impossible at the engine level.
- Stock is never written directly. It is maintained by the appliquer_mouvement trigger, defined as SECURITY DEFINER, after every insert into movements. A check constraint keeps stock greater than or equal to zero, so an oversized withdrawal fails and the transaction rolls back.
- Business rules on movement types are enforced by a check constraint, an entry needs a destination, a withdrawal needs a source, a transfer needs both.

The full data dictionary and the conceptual and logical models are in the French deliverable. The executable DDL is in sql/01-schema.sql.

## 5. Access security

Least privilege is the guiding principle. No application account is a superuser.

| Account | Rights | Purpose |
|---------|--------|---------|
| wms_app | read plus insert into movements | WMS application |
| wms_readonly | read only | reporting, read port 5001 |
| wms_mvt | insert movements and select lookups only | RF handheld terminals, one tightly scoped account |
| wms_dba | full rights on the wms schema, not superuser | application administration |
| pgbouncer_auth | execute one authentication function | PgBouncer technical account |
| wms_exporter | pg_monitor | monitoring |

Row Level Security isolates clients on articles, stock and movements, based on a session setting. TLS is enforced on the network through hostssl rules. PgBouncer runs in SCRAM pass through mode, so no application password is stored on the load balancer.

## 6. High availability and disaster recovery

Measured results exceed the targets. Failover takes ten to thirty seconds, well under the one hour RTO. Continuous WAL archiving keeps the RPO under one minute, well under the fifteen minute target.

A live failover was demonstrated, primary switched from pgsql-01 to pgsql-02 in about ten seconds, HAProxy followed automatically, then the cluster was switched back to nominal state. A full restore test was performed in an isolated instance, 1800 articles and 131801 movements were recovered, which confirms integrity.

## 7. Backups

pgBackRest with a repository on pgsql-lb, full weekly, differential daily, incremental every six hours, plus continuous WAL archiving for point in time recovery. Retention and rotation are automatic. Each backup is verified. Backups are scheduled by systemd timers.

## 8. Monitoring

Prometheus collects metrics from postgres_exporter and node_exporter, Grafana displays the dashboard. Five critical indicators with thresholds, replication lag, active connections, disk usage, slow queries and backup success. Each alert maps to an analysis procedure in the operations runbook.

## 9. Known limits and next steps

- Single node etcd, move to three nodes for quorum in production.
- Single load balancer, add a second HAProxy with a virtual IP through keepalived.
- Local backup repository, add an immutable off site copy against ransomware.
