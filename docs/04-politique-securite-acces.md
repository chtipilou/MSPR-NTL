# Politique de sécurité et d'accès

Base de données WMS NordTransit Logistics. Principe directeur : moindre privilège. Aucun compte applicatif n'est superutilisateur, chaque compte n'a que les droits strictement nécessaires à son usage. Le détail exécutable se trouve dans `sql/03-security.sql`.

## 1. Modèle de rôles

La politique sépare les rôles de groupe, qui portent les droits sans pouvoir se connecter, et les rôles de connexion, qui héritent des groupes. Ce découpage facilite l'audit et la révocation.

### Rôles de groupe (sans connexion)

| Rôle | Droits portés |
|------|---------------|
| wms_reader | USAGE sur le schéma et SELECT sur toutes les tables et vues |
| wms_writer | hérite de wms_reader, plus INSERT sur la table mouvements |
| wms_catalog | hérite de wms_reader, plus écriture sur le référentiel articles, localisations, clients, sites |

### Rôles de connexion (moindre privilège)

| Compte | Hérite ou droits | Usage métier |
|--------|------------------|--------------|
| wms_app | wms_writer | Application WMS, lecture et écriture des mouvements |
| wms_readonly | wms_reader | Reporting et lectures, branché sur le port de lecture 5001 |
| wms_mvt | INSERT mouvements et SELECT sur articles, localisations, sites, stock uniquement | Terminaux RF de réception et expédition, illustration un compte égale un usage très ciblé |
| wms_dba | tous droits sur le schéma wms, sans être superutilisateur | Administration applicative, DDL |
| pgbouncer_auth | EXECUTE sur une seule fonction d'authentification | Compte technique du pool PgBouncer |
| wms_exporter | pg_monitor | Compte de supervision Prometheus, lecture des métriques |

Le compte `wms_mvt` matérialise la demande de cloisonnement par usage. Il peut saisir un mouvement, il peut lire les référentiels nécessaires à cette saisie, mais il ne peut ni lire la table clients, ni consulter l'historique global, ni créer le moindre objet.

## 2. Le stock n'est jamais écrit directement

Aucun compte applicatif n'a le droit d'écrire dans la table `stock`. La quantité est maintenue uniquement par le déclencheur `appliquer_mouvement()`, qui s'exécute en `SECURITY DEFINER`. Concrètement, un terminal RF qui insère un mouvement déclenche la mise à jour du stock avec les droits du propriétaire du déclencheur, sans posséder lui-même de droit d'écriture sur `stock`. Cela ferme une voie de fraude évidente, la modification directe d'une quantité sans mouvement correspondant.

## 3. Cloisonnement par client (Row Level Security)

Les tables `articles`, `stock` et `mouvements` ont la Row Level Security activée. Une politique filtre les lignes selon le client courant, fixé par l'application au début de sa session.

```sql
SET app.client_id = '1';
-- a partir d'ici, les requetes ne voient que les donnees du client 1
```

La politique compare `client_id` à `current_setting('app.client_id')`. Sur la table des mouvements, la clause `WITH CHECK` empêche aussi d'insérer un mouvement pour un autre client que celui de la session. Un compte applicatif partagé entre plusieurs clients ne peut donc jamais lire ni écrire les données d'un client tiers.

Le compte `wms_dba` dispose de l'attribut `BYPASSRLS` pour les besoins d'exploitation et de maintenance. C'est un choix assumé, réservé à un compte d'administration, pas aux comptes applicatifs.

## 4. Verrouillage par défaut

Le schéma est fermé avant d'être ouvert.

- `REVOKE ALL` sur la base, sur le schéma wms et sur le schéma public retirés à PUBLIC. Rien n'est accessible par défaut.
- Les droits sont ensuite accordés rôle par rôle, table par table.
- Les privilèges par défaut sont définis pour que les futures tables héritent automatiquement de la bonne politique, lecture pour wms_reader, insertion mouvements pour wms_writer.

## 5. Authentification et chiffrement

| Mesure | Mise en oeuvre |
|--------|----------------|
| Chiffrement des mots de passe | SCRAM-SHA-256, aucun mot de passe en clair ni en MD5 |
| Chiffrement du transport | TLS imposé sur le réseau par les règles `hostssl` du fichier pg_hba.conf |
| Règles d'accès | pg_hba.conf restrictif, scram-sha-256 exigé, accès limités aux réseaux attendus |
| Pool de connexions | PgBouncer en SCRAM pass-through, aucun mot de passe applicatif n'est stocké sur le répartiteur |
| Limites de connexions | chaque compte a une limite de connexions adaptée à son usage |

Le mode SCRAM pass-through de PgBouncer mérite une note. PgBouncer ne conserve pas les mots de passe applicatifs. Il interroge la base avec son compte technique `pgbouncer_auth`, qui n'a le droit d'exécuter qu'une seule fonction d'authentification. Une compromission du répartiteur ne livre donc pas les identifiants applicatifs.

## 6. Validations réalisées

Les contrôles suivants ont été exécutés sur le cluster déployé et ont donné le résultat attendu.

| Contrôle | Résultat |
|----------|----------|
| wms_mvt insère un mouvement | autorisé |
| wms_mvt lit la table clients | refusé |
| wms_mvt crée une table | refusé |
| wms_readonly écrit une ligne | refusé |
| wms_app avec app.client_id = 1 liste les articles | ne voit que les articles du client 1, pas ceux des autres clients |
| écriture directe dans stock par un compte applicatif | impossible, aucun droit accordé |

Ces tests démontrent que le moindre privilège et le cloisonnement ne sont pas théoriques. Ils sont appliqués et vérifiés.

## 7. Point d'attention hors périmètre base

Au cours du déploiement, un défaut de configuration système a été relevé sur les machines virtuelles. Le compte root dispose d'un mot de passe vide, à cause d'une option `nullok` du module d'authentification. Ce point sort du périmètre PostgreSQL, il n'a donc pas été modifié, mais il est signalé à l'équipe système comme correctif prioritaire. Il figure aussi dans la note de direction.

## 8. Synthèse de la matrice d'accès

| Table | wms_app | wms_readonly | wms_mvt | wms_catalog | wms_dba |
|-------|---------|--------------|---------|-------------|---------|
| clients | lecture | lecture | aucun | lecture écriture | tous droits |
| sites | lecture | lecture | lecture | lecture écriture | tous droits |
| articles | lecture | lecture | lecture | lecture écriture | tous droits |
| localisations | lecture | lecture | lecture | lecture écriture | tous droits |
| stock | lecture | lecture | lecture | lecture | tous droits |
| mouvements | lecture écriture | lecture | écriture | lecture | tous droits |

La colonne stock ne comporte aucune écriture applicative, conformément au principe du point 2. La table mouvements est le seul point d'entrée des écritures opérationnelles.
