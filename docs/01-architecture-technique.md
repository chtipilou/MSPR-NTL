# Document d'architecture technique

Base de données WMS NordTransit Logistics. Cluster PostgreSQL 17 en haute disponibilité.

## 1. Contexte et contraintes

NordTransit Logistics exploite quatre sites (siège à Lille, entrepôts de Lens, Valenciennes et Arras) plus un cross-dock saisonnier. L'application coeur de métier est le WMS, qui pilote les réceptions à partir de 5 h 30 et les expéditions jusqu'à 18 h 30 environ. Une indisponibilité de sa base de données arrête immédiatement la réception et l'expédition sur les quatre sites.

Les contraintes structurantes pour la base de données sont les suivantes.

- Fenêtres de maintenance courtes, principalement nocturnes. Toute intervention en journée doit se faire sans immobiliser les quais.
- RTO de 1 heure et RPO de 15 minutes fixés par la direction.
- Sauvegardes existantes sur NAS sans campagne de restauration planifiée ni objectifs clairs. C'est le point faible à corriger.
- Données clients à cloisonner, exigence de moindre privilège sur les accès.
- Équipe informatique réduite, donc une exploitation qui doit rester simple et documentée.

## 2. Choix du SGBD : PostgreSQL 17

Le sujet partait sur MySQL. Nous avons retenu PostgreSQL 17 pour les raisons suivantes, toutes directement liées aux exigences du cahier des charges.

| Exigence | Apport de PostgreSQL |
|----------|----------------------|
| Intégrité forte du stock et des mouvements | Contraintes CHECK riches, clés étrangères composites, types ENUM, colonnes générées, transactions sur le DDL |
| Haute disponibilité avec bascule automatique | Réplication en streaming native et orchestration par Patroni, solution mature et répandue |
| RPO court | Archivage continu des journaux WAL et restauration à un instant précis avec pgBackRest |
| Cloisonnement des données clients | Row Level Security appliquée directement dans le moteur |
| Sécurité des accès | Authentification SCRAM-SHA-256, chiffrement TLS natif, gestion fine des rôles |
| Volumétrie des mouvements horodatés | Index BRIN, très compact sur les colonnes chronologiques |
| Coût | Open source, sans licence pour l'équivalent haute disponibilité |

Le périmètre fonctionnel du sujet est respecté. Seul le moteur change. La migration depuis MySQL ne porte que sur le SGBD, pas sur le métier.

## 3. Architecture de haute disponibilité

### 3.1 Vue d'ensemble

```
                Applications WMS (terminaux RF, EDI, web)
                                 |
                                 v
              +-------------------------------------------+
              |          pgsql-lb  192.168.10.62          |
              |  PgBouncer 6432  (pool de connexions)     |
              |  HAProxy   5000  = ecritures (primaire)   |
              |  HAProxy   5001  = lectures  (replica)    |
              |  HAProxy   7000  = page de stats          |
              |  etcd      2379  (annuaire de cluster)    |
              |  Depot pgBackRest (sauvegardes + WAL)     |
              +----------------+-------------+------------+
          sonde REST 8008      |             |  sonde REST 8008
                               v             v
              +--------------------+   +--------------------+
              | pgsql-01  .61      |   | pgsql-02  .60      |
              | PostgreSQL PRIMAIRE| ->| PostgreSQL REPLICA |
              | Patroni            |rep| Patroni (streaming)|
              +--------------------+slot+-------------------+
```

### 3.2 Rôle de chaque composant

| Composant | Version | Rôle |
|-----------|---------|------|
| PostgreSQL | 17.10 | Moteur de base de données, un primaire et un réplica |
| Patroni | 4.0.7 | Orchestration de la haute disponibilité, élection du primaire, bascule automatique, réintégration de l'ancien primaire |
| etcd | 3.5 | Annuaire de cluster, magasin de vérité qui arbitre l'élection du primaire |
| HAProxy | 3.0 | Répartiteur de charge, sépare les écritures et les lectures, suit le primaire courant |
| PgBouncer | 1.24 | Pool de connexions en mode transaction, limite la charge sur le moteur |
| pgBackRest | 2.55 | Sauvegardes complètes, différentielles, incrémentales et archivage WAL |

### 3.3 Mécanisme de bascule

Patroni s'appuie sur etcd pour maintenir un verrou de leader avec une durée de vie limitée. Le primaire renouvelle ce verrou en permanence. S'il cesse de le renouveler (panne, perte réseau, arrêt), le verrou expire, le réplica le plus à jour est promu, et l'ancien primaire est marqué hors service.

HAProxy ne décide rien de lui-même. Il interroge l'API REST de Patroni sur chaque noeud, en visant le point de terminaison `/primary` pour le port d'écriture et `/replica` pour le port de lecture. Seul le noeud qui se déclare primaire répond favorablement sur `/primary`. Le routage suit donc l'état réel du cluster, sans configuration à modifier lors d'une bascule.

La réplication utilise un slot physique, ce qui garantit que le primaire conserve les journaux WAL nécessaires au réplica même si celui-ci décroche temporairement. Aucun trou de réplication n'est laissé au hasard.

## 4. Hébergement et matériel

Le cluster est déployé sur l'infrastructure de virtualisation existante de NTL, au siège de Lille.

| Élément | Détail |
|---------|--------|
| Hyperviseur | Proxmox VE sur serveur de classe Dell PowerEdge (référence annexe B du cahier des charges, 2 processeurs Xeon, 128 Go de RAM) |
| Stockage | Volumes virtuels sur le stockage de l'hyperviseur, dépôt de sauvegarde porté par la VM pgsql-lb |
| Réseau | Segment 192.168.10.0/24 du siège, pont `vmbr1` côté Proxmox |

Répartition des machines virtuelles.

| VM | Hôte logique | IP | Rôle |
|----|--------------|----|----|
| pgsql-01 | noeud base 1 | 192.168.10.61 | PostgreSQL primaire et Patroni |
| pgsql-02 | noeud base 2 | 192.168.10.60 | PostgreSQL réplica et Patroni |
| pgsql-lb | noeud services | 192.168.10.62 | etcd, HAProxy, PgBouncer, dépôt pgBackRest |

Le choix de séparer les deux moteurs de base sur deux machines distinctes est volontaire. Une panne matérielle de l'une ne doit pas emporter l'autre. Les services d'accès et l'annuaire de cluster sont regroupés sur une troisième machine pour ne pas mélanger les rôles.

## 5. Flux réseau et ports

| Source | Destination | Port | Usage |
|--------|-------------|------|-------|
| Applications WMS | pgsql-lb | 6432 | Connexion applicative via PgBouncer |
| PgBouncer | HAProxy (pgsql-lb) | 5000 | Écritures vers le primaire |
| Applications de reporting | HAProxy (pgsql-lb) | 5001 | Lectures vers le réplica |
| HAProxy | pgsql-01 et pgsql-02 | 8008 | Sonde de santé REST Patroni |
| HAProxy | pgsql-01 et pgsql-02 | 5432 | Trafic SQL réparti |
| Patroni | etcd (pgsql-lb) | 2379 | Annuaire de cluster |
| pgsql-01 et pgsql-02 | etcd (pgsql-lb) | 2379 | Verrou de leader |
| pgsql-01, pgsql-02 | pgsql-lb (dépôt) | 22 | Transfert des sauvegardes par SSH |
| Prometheus | exporters | 9187, 9100 | Collecte des métriques |

Toutes les connexions SQL sur le réseau sont chiffrées par TLS, imposées par les règles `hostssl` du fichier `pg_hba.conf`. Le détail figure dans la politique de sécurité.

## 6. Points de défaillance et limites assumées

L'architecture supprime les points de défaillance les plus coûteux mais en conserve deux, identifiés et assumés pour le périmètre de la maquette.

- etcd est déployé sur un seul noeud. En production il faut trois noeuds etcd pour disposer d'un quorum. Sur la maquette, un noeud unique suffit à démontrer le mécanisme.
- Le répartiteur de charge HAProxy est unique. La parade en production est un second HAProxy associé à une adresse IP virtuelle portée par keepalived. C'est une perspective d'évolution, documentée comme telle.

Ces deux points sont rappelés dans la note de direction et dans la gestion de projet, avec leur mesure de mitigation.

## 7. Pourquoi cette architecture répond au besoin de NTL

- La bascule automatique tient l'objectif de RTO largement, sans intervention humaine de nuit.
- L'archivage WAL continu tient l'objectif de RPO largement.
- La séparation lecture et écriture permet d'absorber le reporting sans peser sur les opérations de quai.
- Le pool de connexions protège le moteur des pics de connexions des terminaux RF.
- Le dépôt de sauvegarde séparé et les restaurations testées corrigent le point faible initial, à savoir des sauvegardes jamais éprouvées.
