# Analyse de journaux

Base de données WMS NordTransit Logistics. Identification des journaux pertinents et méthode d'analyse, à savoir quelles traces surveiller, quels motifs, quels seuils et quelle corrélation.

## 1. Sources de journaux

L'infrastructure produit plusieurs flux de journaux. Chacun éclaire une couche.

| Source | Où la lire | Ce qu'elle révèle |
|--------|------------|-------------------|
| PostgreSQL | journal du moteur, `journalctl -u patroni` | erreurs FATAL, attentes de verrou, requêtes lentes, connexions refusées |
| Patroni | `journalctl -u patroni` | élections, bascules, perte de contact avec etcd |
| etcd | `journalctl -u etcd` | perte de quorum, latence de l'annuaire |
| HAProxy | page de stats sur le port 7000, journal HAProxy | serveurs amont up ou down, suivi de bascule |
| pgBackRest | `/var/log/pgbackrest/`, `wms-backup.log` | échec de sauvegarde ou d'archivage WAL |
| Réplication | `pg_stat_replication` | retard du réplica, état du streaming |
| Système | journaux OS, node_exporter | espace disque, charge, mémoire |

## 2. Motifs à surveiller

Pour chaque source, des motifs précis méritent une alerte ou une investigation.

| Source | Motif | Interprétation |
|--------|-------|----------------|
| PostgreSQL | `FATAL` ou `PANIC` | échec de connexion, problème grave du moteur |
| PostgreSQL | `deadlock detected` | interblocage applicatif, à corriger côté requêtes |
| PostgreSQL | `duration:` au dessus du seuil | requête lente, voir log_min_duration_statement à 500 ms |
| PostgreSQL | `could not receive data from WAL stream` | rupture de réplication |
| Patroni | `promoted self to leader` | une bascule vient d'avoir lieu |
| Patroni | `demoted self` ou perte de leader | l'ancien primaire a perdu son rôle |
| etcd | `lost the TCP streaming connection` | instabilité de l'annuaire, risque de bascule |
| HAProxy | `Server ... is DOWN` | un noeud ne répond plus à la sonde |
| pgBackRest | `ERROR` | sauvegarde ou archivage en échec, RPO menacé |

## 3. Seuils

Les seuils relient les journaux à des décisions. Ils sont alignés sur le guide de supervision.

| Mesure issue des journaux | Seuil d'alerte | Seuil critique |
|---------------------------|----------------|----------------|
| Requêtes au dessus de la durée seuil | p95 supérieur à 500 ms | p95 supérieur à 2 secondes |
| Nombre de FATAL par fenêtre de 5 minutes | au dessus de 5 | au dessus de 20 |
| Échec d'archivage WAL | premier échec | échecs répétés |
| Bascules Patroni par jour | plus d'une non planifiée | bascules en boucle |
| Lag de réplication tiré de pg_stat_replication | supérieur à 30 secondes | supérieur à 120 secondes |

## 4. Méthode de corrélation

Un incident se lit rarement dans un seul journal. La méthode consiste à recouper les sources par horodatage.

Exemple type, une latence applicative signalée par les équipes de quai.

1. Repérer l'heure de l'incident.
2. Vérifier dans Patroni si une bascule a eu lieu au même moment.
3. Croiser avec HAProxy, un serveur amont est-il passé hors service puis revenu.
4. Croiser avec etcd, une instabilité de l'annuaire a-t-elle déclenché la bascule.
5. Croiser avec les requêtes lentes de PostgreSQL et l'espace disque système.

La chaîne typique se lit ainsi : instabilité etcd, perte du verrou de leader, bascule Patroni, bascule des serveurs amont HAProxy, brève coupure perçue par les applications. Une fois cette chaîne reconstituée, la cause racine est l'instabilité de l'annuaire, pas la base elle-même, ce qui oriente correctement la correction.

## 5. Mise en oeuvre pratique

- Centraliser la lecture par `journalctl` sur chaque noeud pour les services systemd.
- Activer log_min_duration_statement à 500 ms pour capturer les requêtes lentes sans noyer le journal.
- Activer log_lock_waits pour tracer les attentes de verrou.
- Conserver les journaux de sauvegarde de pgBackRest pour l'audit du PRA.
- À terme, agréger ces journaux dans un collecteur central et brancher des alertes, ce qui figure dans les perspectives du projet.
