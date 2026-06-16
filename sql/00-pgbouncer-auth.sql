-- Fonction sécurisée pour l'auth_query PgBouncer (principe de moindre privilège)
CREATE SCHEMA IF NOT EXISTS pgbouncer;
CREATE OR REPLACE FUNCTION pgbouncer.get_auth(p_usename TEXT)
RETURNS TABLE(usename TEXT, passwd TEXT)
LANGUAGE sql SECURITY DEFINER SET search_path = pg_catalog AS
$$ SELECT usename::text, passwd::text FROM pg_shadow WHERE usename = p_usename; $$;
REVOKE ALL ON FUNCTION pgbouncer.get_auth(TEXT) FROM PUBLIC;
