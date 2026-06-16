# Démarche d'optimisation

Base de données WMS NordTransit Logistics. Ce document décrit la méthode suivie pour optimiser les accès, les choix d'index, et les résultats mesurés sur le volume de test.

## 1. Méthode

L'optimisation part des usages, pas de l'intuition. La démarche a suivi quatre étapes.

1. Imaginer les requêtes les plus fréquentes du WMS, à partir du métier décrit dans le cahier des charges.
2. Choisir les index en fonction de ces requêtes, en évitant les index inutiles qui ralentissent les écritures.
3. Charger un volume représentatif pour mesurer sur des données réalistes.
4. Mesurer les temps de réponse et vérifier les plans d'exécution avec EXPLAIN ANALYZE.

## 2. Usages fréquents identifiés

Le WMS sollicite la base en continu pendant les heures de quai. Les requêtes structurantes sont les suivantes.

| Usage métier | Requête type | Fréquence |
|--------------|--------------|-----------|
| Consultation du stock d'un article | stock courant par article_id | très fréquent, à chaque préparation et contrôle |
| Historique des mouvements d'un article | mouvements d'un article sur une période | fréquent, suivi et litiges |
| Activité d'un site sur une période | volume de mouvements par site sur quelques jours | quotidien, pilotage |
| Recherche d'un article | par SKU et par client | très fréquent, saisie terminaux |
| Stock consolidé par site | vue de service v_stock_par_site | reporting |

## 3. Choix d'index

Les index sont choisis pour coller à ces usages.

| Index | Table et colonnes | Type | Usage couvert |
|-------|-------------------|------|---------------|
| idx_stock_article | stock(article_id) | B-tree | Stock courant d'un article |
| idx_stock_loc | stock(localisation_id) | B-tree | Contenu d'un emplacement |
| idx_stock_client | stock(client_id) | B-tree | Filtrage par client, appui RLS |
| idx_articles_client | articles(client_id) | B-tree | Catalogue d'un client |
| uq_articles_client_sku | articles(client_id, sku) | B-tree unique | Recherche par SKU |
| idx_loc_site | localisations(site_id) | B-tree | Emplacements d'un site |
| idx_mvt_article | mouvements(article_id, date_mouvement desc) | B-tree | Historique d'un article, le plus récent en tête |
| idx_mvt_site_date | mouvements(site_id, date_mouvement desc) | B-tree | Activité d'un site sur une période |
| idx_mvt_client | mouvements(client_id) | B-tree | Filtrage par client |
| idx_mvt_date_brin | mouvements(date_mouvement) | BRIN | Balayages par plage de dates sur table volumineuse |

### Pourquoi un index BRIN sur la date des mouvements

La table des mouvements est la plus volumineuse, et elle croît dans l'ordre chronologique. Les lignes proches dans le temps sont physiquement proches sur le disque. C'est exactement le cas d'usage de l'index BRIN, qui ne mémorise que des bornes par bloc plutôt qu'une entrée par ligne. Le résultat est un index très compact, de l'ordre de mille fois plus petit qu'un B-tree équivalent, tout en restant efficace pour les requêtes par plage de dates. Pour les accès très ciblés au dernier mouvement d'un article, on garde en parallèle un B-tree composite, mieux adapté à ce besoin précis.

## 4. Résultats mesurés

Mesures réalisées sur le cluster déployé, avec le volume de test de 1 800 articles et 131 800 mouvements.

| Requête fréquente | Plan retenu | Temps |
|-------------------|-------------|-------|
| Stock courant d'un article | Index Scan sur idx_stock_article | 0,10 ms |
| Historique d'un article sur 30 jours | Index Scan sur idx_mvt_article | 0,14 ms |
| Volume de mouvements par site sur 7 jours | Index Only Scan sur idx_mvt_site_date | 7,4 ms |

Les deux premières requêtes, les plus fréquentes, répondent en une fraction de milliseconde grâce aux index ciblés. La troisième, plus large, reste sous dix millisecondes en exploitant un Index Only Scan, qui lit l'index sans retourner à la table.

## 5. Optimisations complémentaires

- Colonne calculée et stockée pour le volume des articles. Le volume n'est pas recalculé à chaque requête d'expédition, il est figé à l'écriture.
- Pool de connexions PgBouncer en mode transaction. Il évite au moteur de subir le coût d'ouverture et de fermeture des connexions des terminaux RF, nombreuses et brèves.
- Séparation lecture et écriture par HAProxy. Le reporting est dirigé vers le réplica, ce qui décharge le primaire pendant les heures de quai.
- Clés étrangères composites indexées par les contraintes d'unicité sous-jacentes, ce qui sert à la fois l'intégrité et les jointures.

## 6. Vérification et entretien

L'optimisation n'est pas un acte unique. Le guide de supervision suit la latence et les requêtes lentes. L'extension `pg_stat_statements` permet de repérer en continu les requêtes coûteuses. Un `ANALYZE` régulier maintient les statistiques du planificateur à jour, ce qui garantit que les plans restent pertinents quand le volume grandit.
