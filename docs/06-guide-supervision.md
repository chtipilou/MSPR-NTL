# Guide de supervision

Base de données WMS NordTransit Logistics. Cinq indicateurs critiques, leurs seuils, et la procédure d'analyse en cas d'alerte.

## 1. Chaîne de supervision

| Brique | Rôle |
|--------|------|
| postgres_exporter | Expose les métriques PostgreSQL sur le port 9187, via le compte wms_exporter doté de pg_monitor |
| node_exporter | Expose les métriques système, dont l'espace disque, sur le port 9100 |
| API REST Patroni | Renseigne l'état du cluster et la présence d'un primaire |
| Prometheus | Collecte et conserve les séries temporelles |
| Grafana | Affiche le tableau de bord et applique les seuils visuels |

Le tableau de bord Grafana est versionné dans `configs/grafana-dashboard.json`. La configuration de collecte Prometheus est dans `configs/prometheus.yml`.

## 2. Les cinq indicateurs critiques

| Indicateur | Source | Seuil d'alerte | Seuil critique |
|------------|--------|----------------|----------------|
| 1. Lag de réplication | pg_replication_lag_seconds | supérieur à 30 secondes | supérieur à 120 secondes ou 64 Mo de retard |
| 2. Connexions actives | numbackends sur max_connections | supérieur à 70 pour cent | supérieur à 90 pour cent |
| 3. Espace disque données et WAL | node_exporter, df | supérieur à 75 pour cent | supérieur à 90 pour cent |
| 4. Requêtes lentes et latence | log_min_duration_statement, pg_stat_statements | p95 supérieur à 500 ms | p95 supérieur à 2 secondes |
| 5. Succès des sauvegardes | âge du dernier backup, échecs d'archivage WAL | dernier backup de plus de 26 heures | échec de l'archive_command, ou échec de sauvegarde |

Un indicateur transverse complète l'ensemble, l'état du cluster Patroni, à savoir la présence effective d'un primaire. Sa perte est traitée comme un incident majeur.

## 3. Procédure d'analyse par indicateur

### Indicateur 1, lag de réplication

Une alerte signifie que le réplica prend du retard sur le primaire, ce qui dégrade le RPO et la capacité de bascule.

1. Vérifier l'état avec `SELECT * FROM pg_stat_replication;` sur le primaire.
2. Contrôler la charge du réplica, une requête de reporting lourde peut le ralentir.
3. Vérifier le réseau entre les deux noeuds.
4. Contrôler que le slot de réplication n'est pas saturé et que l'espace WAL est suffisant.
5. Si le retard persiste et croît, traiter en priorité, le cluster n'a plus de candidat fiable à la bascule.

### Indicateur 2, connexions actives

Une alerte signifie une montée du nombre de sessions vers la limite configurée.

1. Sur PgBouncer, `SHOW POOLS;` pour voir les files d'attente.
2. Identifier les requêtes longues ou bloquées, `pg_stat_activity` trié par durée.
3. Terminer les sessions fautives avec `pg_terminate_backend` si nécessaire.
4. Vérifier l'absence de fuite de connexions côté application, connexions ouvertes et jamais rendues.

### Indicateur 3, espace disque

Une alerte signifie un risque d'arrêt du moteur par saturation, notamment du répertoire WAL.

1. Identifier le point de montage en cause.
2. Contrôler que l'archivage WAL fonctionne, un archivage en échec fait gonfler le répertoire pg_wal.
3. Purger les WAL déjà archivés selon la politique de rétention.
4. Étendre le volume si la croissance est structurelle.

### Indicateur 4, requêtes lentes et latence

Une alerte signifie une dégradation des temps de réponse perçue par les applications.

1. Consulter `pg_stat_statements` pour repérer les requêtes les plus coûteuses.
2. Examiner le plan d'exécution avec `EXPLAIN ANALYZE`.
3. Vérifier la présence des index attendus, lancer `ANALYZE` si les statistiques sont périmées.
4. Corréler avec une éventuelle bascule récente ou un pic de charge.

### Indicateur 5, succès des sauvegardes

Une alerte signifie une dégradation de la couverture PRA.

1. Consulter le journal de sauvegarde et `pgbackrest info`.
2. Vérifier l'accès SSH au dépôt et lancer `pgbackrest check`.
3. Relancer la sauvegarde manquée.
4. Pour un échec d'archivage WAL, traiter en urgence, c'est le RPO qui est en jeu.

## 4. Lien avec l'exploitation

Chaque alerte renvoie à une procédure du RunBook. La supervision détecte, le RunBook corrige. La matrice d'escalade fixe les délais cibles selon le niveau de gravité.
