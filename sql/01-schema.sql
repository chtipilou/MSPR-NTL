-- =====================================================================
--  WMS NordTransit Logistics (NTL) - Schéma métier
--  SGBD : PostgreSQL 17   |   Schéma : wms
--  Couvre : Clients, Sites, Articles/SKU, Localisations, Stock, Mouvements
--  Intégrité : clés étrangères, CHECK, unicité, types ENUM, trigger de
--  cohérence stock <-> mouvements. Séparation multi-clients (client_id +
--  RLS appliquée dans le script de sécurité).
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS wms;
SET search_path = wms, public;

-- ---------- Types ----------------------------------------------------
DO $$ BEGIN
  CREATE TYPE wms.type_mouvement AS ENUM ('ENTREE','SORTIE','TRANSFERT','AJUSTEMENT');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE wms.type_localisation AS ENUM ('PICKING','MASSE','QUAI','CROSSDOCK','RETOUR');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ---------- Clients (cloisonnement des données) ----------------------
CREATE TABLE IF NOT EXISTS wms.clients (
    client_id    int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code         text NOT NULL UNIQUE CHECK (code ~ '^[A-Z0-9_]{2,20}$'),
    raison_sociale text NOT NULL,
    actif        boolean NOT NULL DEFAULT true,
    cree_le      timestamptz NOT NULL DEFAULT now()
);

-- ---------- Sites / entrepôts ---------------------------------------
CREATE TABLE IF NOT EXISTS wms.sites (
    site_id      int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code         text NOT NULL UNIQUE CHECK (code ~ '^[A-Z0-9]{2,10}$'),
    libelle      text NOT NULL,
    ville        text NOT NULL,
    actif        boolean NOT NULL DEFAULT true
);

-- ---------- Articles / SKU ------------------------------------------
-- Catalogue par client ; dimensions/poids indispensables aux calculs
-- d'expédition (volume, poids transport).
CREATE TABLE IF NOT EXISTS wms.articles (
    article_id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id    int  NOT NULL REFERENCES wms.clients(client_id) ON DELETE RESTRICT,
    sku          text NOT NULL,
    libelle      text NOT NULL,
    longueur_mm  int  NOT NULL CHECK (longueur_mm > 0),
    largeur_mm   int  NOT NULL CHECK (largeur_mm  > 0),
    hauteur_mm   int  NOT NULL CHECK (hauteur_mm  > 0),
    poids_g      int  NOT NULL CHECK (poids_g     > 0),
    actif        boolean NOT NULL DEFAULT true,
    cree_le      timestamptz NOT NULL DEFAULT now(),
    -- volume calculé (litres), utile aux requêtes d'expédition
    volume_l     numeric(12,3) GENERATED ALWAYS AS
                 ((longueur_mm::numeric*largeur_mm*hauteur_mm)/1000000.0) STORED,
    CONSTRAINT uq_articles_client_sku UNIQUE (client_id, sku),
    -- clé candidate pour FK composite (garantit la cohérence du client)
    CONSTRAINT uq_articles_id_client  UNIQUE (article_id, client_id)
);

-- ---------- Localisations (emplacements de stockage) ----------------
CREATE TABLE IF NOT EXISTS wms.localisations (
    localisation_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    site_id      int  NOT NULL REFERENCES wms.sites(site_id) ON DELETE RESTRICT,
    code         text NOT NULL,                 -- ex: A-12-3 (allée-travée-niveau)
    type         wms.type_localisation NOT NULL DEFAULT 'PICKING',
    capacite_max int  NOT NULL DEFAULT 1000 CHECK (capacite_max > 0),
    actif        boolean NOT NULL DEFAULT true,
    CONSTRAINT uq_loc_site_code UNIQUE (site_id, code),
    CONSTRAINT uq_loc_id_site   UNIQUE (localisation_id, site_id)
);

-- ---------- Stock actuel --------------------------------------------
-- Quantité courante d'un article à une localisation. Cohérence assurée
-- par le trigger sur wms.mouvements. quantite >= 0 garantie.
CREATE TABLE IF NOT EXISTS wms.stock (
    stock_id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id       int    NOT NULL,
    article_id      bigint NOT NULL,
    localisation_id bigint NOT NULL REFERENCES wms.localisations(localisation_id) ON DELETE RESTRICT,
    quantite        int    NOT NULL DEFAULT 0 CHECK (quantite >= 0),
    maj_le          timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT uq_stock_article_loc UNIQUE (article_id, localisation_id),
    -- FK composite : le stock appartient bien au client de l'article
    CONSTRAINT fk_stock_article FOREIGN KEY (article_id, client_id)
        REFERENCES wms.articles(article_id, client_id) ON DELETE RESTRICT
);

-- ---------- Mouvements (entrées / sorties horodatées) ---------------
CREATE TABLE IF NOT EXISTS wms.mouvements (
    mouvement_id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id        int    NOT NULL,
    article_id       bigint NOT NULL,
    site_id          int    NOT NULL REFERENCES wms.sites(site_id) ON DELETE RESTRICT,
    type             wms.type_mouvement NOT NULL,
    quantite         int    NOT NULL CHECK (quantite > 0),
    localisation_src bigint REFERENCES wms.localisations(localisation_id),
    localisation_dst bigint REFERENCES wms.localisations(localisation_id),
    reference        text,                        -- n° réception/commande/EDI
    utilisateur      text NOT NULL DEFAULT current_user,
    date_mouvement   timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT fk_mvt_article FOREIGN KEY (article_id, client_id)
        REFERENCES wms.articles(article_id, client_id) ON DELETE RESTRICT,
    -- règles métier : source/destination selon le type
    CONSTRAINT chk_mvt_loc CHECK (
        (type = 'ENTREE'    AND localisation_dst IS NOT NULL) OR
        (type = 'SORTIE'    AND localisation_src IS NOT NULL) OR
        (type = 'TRANSFERT' AND localisation_src IS NOT NULL AND localisation_dst IS NOT NULL) OR
        (type = 'AJUSTEMENT')
    )
);

-- ---------- Index (requêtes fréquentes) -----------------------------
-- Stock : lecture par article et par localisation
CREATE INDEX IF NOT EXISTS idx_stock_article  ON wms.stock(article_id);
CREATE INDEX IF NOT EXISTS idx_stock_loc      ON wms.stock(localisation_id);
CREATE INDEX IF NOT EXISTS idx_stock_client   ON wms.stock(client_id);
-- Articles : recherche par SKU / par client
CREATE INDEX IF NOT EXISTS idx_articles_client ON wms.articles(client_id);
-- Localisations par site
CREATE INDEX IF NOT EXISTS idx_loc_site       ON wms.localisations(site_id);
-- Mouvements : très volumineux et chronologiques -> BRIN sur la date
CREATE INDEX IF NOT EXISTS idx_mvt_date_brin  ON wms.mouvements USING brin(date_mouvement);
CREATE INDEX IF NOT EXISTS idx_mvt_article    ON wms.mouvements(article_id, date_mouvement DESC);
CREATE INDEX IF NOT EXISTS idx_mvt_site_date  ON wms.mouvements(site_id, date_mouvement DESC);
CREATE INDEX IF NOT EXISTS idx_mvt_client     ON wms.mouvements(client_id);

-- ---------- Trigger de cohérence Stock <- Mouvements ----------------
CREATE OR REPLACE FUNCTION wms.appliquer_mouvement() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.type IN ('ENTREE','TRANSFERT') THEN
        INSERT INTO wms.stock(client_id, article_id, localisation_id, quantite, maj_le)
        VALUES (NEW.client_id, NEW.article_id, NEW.localisation_dst, NEW.quantite, now())
        ON CONFLICT (article_id, localisation_id)
        DO UPDATE SET quantite = wms.stock.quantite + EXCLUDED.quantite, maj_le = now();
    END IF;

    IF NEW.type IN ('SORTIE','TRANSFERT') THEN
        UPDATE wms.stock
           SET quantite = quantite - NEW.quantite, maj_le = now()
         WHERE article_id = NEW.article_id AND localisation_id = NEW.localisation_src;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Stock inexistant pour article % a la localisation source %',
                NEW.article_id, NEW.localisation_src;
        END IF;
        -- la contrainte CHECK (quantite >= 0) bloque tout stock négatif
    END IF;

    IF NEW.type = 'AJUSTEMENT' THEN
        INSERT INTO wms.stock(client_id, article_id, localisation_id, quantite, maj_le)
        VALUES (NEW.client_id, NEW.article_id, COALESCE(NEW.localisation_dst, NEW.localisation_src), NEW.quantite, now())
        ON CONFLICT (article_id, localisation_id)
        DO UPDATE SET quantite = EXCLUDED.quantite, maj_le = now();
    END IF;

    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS trg_mouvement ON wms.mouvements;
CREATE TRIGGER trg_mouvement
    AFTER INSERT ON wms.mouvements
    FOR EACH ROW EXECUTE FUNCTION wms.appliquer_mouvement();

-- ---------- Vue de service (stock consolidé) ------------------------
CREATE OR REPLACE VIEW wms.v_stock_par_site AS
SELECT s.client_id, si.code AS site, a.sku, a.libelle,
       sum(s.quantite) AS quantite_totale
FROM wms.stock s
JOIN wms.articles a      ON a.article_id = s.article_id
JOIN wms.localisations l ON l.localisation_id = s.localisation_id
JOIN wms.sites si        ON si.site_id = l.site_id
GROUP BY s.client_id, si.code, a.sku, a.libelle;

COMMENT ON SCHEMA wms IS 'Schéma métier WMS NordTransit Logistics';
