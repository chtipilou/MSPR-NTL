-- =====================================================================
--  Sécurité WMS NTL - Politique d'accès au moindre privilège
--  Mots de passe injectés via variables psql (-v pw_xxx=...).
--  Modèle : rôles de GROUPE (NOLOGIN, porteurs de droits) + rôles de
--  CONNEXION (LOGIN) qui héritent. Aucun compte applicatif superuser.
-- =====================================================================
\set ON_ERROR_STOP on
SET search_path = wms, public;

-- ---------- 1. Verrouiller la base et le schéma ----------------------
REVOKE ALL ON DATABASE wms FROM PUBLIC;
REVOKE ALL ON SCHEMA wms  FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

-- ---------- 2. Rôles de GROUPE (porteurs de droits, NOLOGIN) ---------
DO $$ BEGIN
  CREATE ROLE wms_reader  NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE ROLE wms_writer  NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
DO $$ BEGIN
  CREATE ROLE wms_catalog NOLOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- Lecteur : USAGE schéma + SELECT sur toutes les tables/vues
GRANT CONNECT ON DATABASE wms TO wms_reader;
GRANT USAGE  ON SCHEMA   wms  TO wms_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA wms TO wms_reader;

-- Writer (application opérationnelle) : lecteur + INSERT des mouvements
-- (le stock est maintenu par le trigger, jamais écrit directement).
GRANT wms_reader TO wms_writer;
GRANT INSERT ON wms.mouvements TO wms_writer;

-- Catalog (gestion du référentiel) : CRUD sur articles/localisations
GRANT wms_reader TO wms_catalog;
GRANT INSERT, UPDATE, DELETE ON wms.articles, wms.localisations,
      wms.clients, wms.sites TO wms_catalog;

-- ---------- 3. Rôles de CONNEXION (LOGIN, moindre privilège) ---------
-- 3a. Compte applicatif principal (écriture mouvements + lecture)
DO $$ BEGIN CREATE ROLE wms_app LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER ROLE wms_app  WITH PASSWORD :'pw_app' CONNECTION LIMIT 100;
GRANT wms_writer TO wms_app;

-- 3b. Compte lecture seule (reporting / lectures via port 5001)
DO $$ BEGIN CREATE ROLE wms_readonly LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER ROLE wms_readonly WITH PASSWORD :'pw_ro' CONNECTION LIMIT 50;
GRANT wms_reader TO wms_readonly;

-- 3c. Compte ULTRA-CIBLÉ : n'écrit QUE la table mouvements
--     (illustration "1 compte = 1 table", terminaux RF de réception/expé)
DO $$ BEGIN CREATE ROLE wms_mvt LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER ROLE wms_mvt WITH PASSWORD :'pw_mvt' CONNECTION LIMIT 50;
GRANT CONNECT ON DATABASE wms TO wms_mvt;
GRANT USAGE  ON SCHEMA wms TO wms_mvt;
GRANT INSERT ON wms.mouvements TO wms_mvt;                 -- écriture
GRANT SELECT ON wms.articles, wms.localisations, wms.sites,
               wms.stock     TO wms_mvt;                    -- lectures nécessaires
--   -> aucun droit sur clients, aucune lecture d'historique global, aucun DDL

-- 3d. Compte DBA applicatif (DDL sur wms) - PAS superuser
DO $$ BEGIN CREATE ROLE wms_dba LOGIN CREATEROLE; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER ROLE wms_dba WITH PASSWORD :'pw_dba';
GRANT ALL ON SCHEMA wms TO wms_dba;
GRANT ALL ON ALL TABLES    IN SCHEMA wms TO wms_dba;
GRANT ALL ON ALL SEQUENCES IN SCHEMA wms TO wms_dba;

-- 3e. Compte d'authentification PgBouncer (auth_query) - ultra-restreint
DO $$ BEGIN CREATE ROLE pgbouncer_auth LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER ROLE pgbouncer_auth WITH PASSWORD :'pw_pgb';
GRANT CONNECT ON DATABASE wms TO pgbouncer_auth;
GRANT USAGE ON SCHEMA pgbouncer TO pgbouncer_auth;
GRANT EXECUTE ON FUNCTION pgbouncer.get_auth(text) TO pgbouncer_auth;

-- 3f. Compte de supervision (exporter Prometheus) - pg_monitor
DO $$ BEGIN CREATE ROLE wms_exporter LOGIN; EXCEPTION WHEN duplicate_object THEN NULL; END $$;
ALTER ROLE wms_exporter WITH PASSWORD :'pw_exp' CONNECTION LIMIT 5;
GRANT pg_monitor TO wms_exporter;
GRANT CONNECT ON DATABASE wms TO wms_exporter;

-- ---------- 4. Privilèges par défaut (tables futures) ----------------
ALTER DEFAULT PRIVILEGES IN SCHEMA wms GRANT SELECT ON TABLES TO wms_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA wms GRANT INSERT ON TABLES TO wms_writer;

-- ---------- 5. Row Level Security : cloisonnement par client ---------
-- L'application fixe le client courant :  SET app.client_id = '<id>';
ALTER TABLE wms.articles   ENABLE ROW LEVEL SECURITY;
ALTER TABLE wms.stock      ENABLE ROW LEVEL SECURITY;
ALTER TABLE wms.mouvements ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS p_client ON wms.articles;
CREATE POLICY p_client ON wms.articles  USING (client_id = current_setting('app.client_id', true)::int);
DROP POLICY IF EXISTS p_client ON wms.stock;
CREATE POLICY p_client ON wms.stock     USING (client_id = current_setting('app.client_id', true)::int);
DROP POLICY IF EXISTS p_client ON wms.mouvements;
CREATE POLICY p_client ON wms.mouvements
    USING      (client_id = current_setting('app.client_id', true)::int)
    WITH CHECK (client_id = current_setting('app.client_id', true)::int);

-- Le DBA applicatif contourne la RLS pour l'exploitation
ALTER ROLE wms_dba BYPASSRLS;

-- ---------- 6. Durcissement des comptes système ---------------------
ALTER ROLE postgres   CONNECTION LIMIT 10;

\echo 'SECURITE_OK'
