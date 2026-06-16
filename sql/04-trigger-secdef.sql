-- Le trigger doit pouvoir maintenir wms.stock même pour des rôles qui
-- n'ont AUCUN droit direct sur stock (moindre privilège préservé).
ALTER FUNCTION wms.appliquer_mouvement() SECURITY DEFINER SET search_path = wms, pg_catalog;
REVOKE ALL ON FUNCTION wms.appliquer_mouvement() FROM PUBLIC;
