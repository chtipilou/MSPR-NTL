-- =====================================================================
--  Jeu de données WMS NTL - références + volume de test (performances)
--  Idempotent au 1er chargement (TRUNCATE puis insertion).
-- =====================================================================
SET search_path = wms, public;

-- Réinitialisation (ordre des dépendances)
TRUNCATE wms.mouvements, wms.stock, wms.localisations, wms.articles,
         wms.sites, wms.clients RESTART IDENTITY CASCADE;

-- ---------- Clients --------------------------------------------------
INSERT INTO wms.clients(code, raison_sociale) VALUES
 ('DECATHL','Decathlon Logistique'),
 ('LEROYM' ,'Leroy Merlin Nord'),
 ('AUCHAN' ,'Auchan Retail HDF');

-- ---------- Sites (réseau NTL) --------------------------------------
INSERT INTO wms.sites(code, libelle, ville) VALUES
 ('WH1','Entrepôt Lens'        ,'Lens'),
 ('WH2','Entrepôt Valenciennes','Valenciennes'),
 ('WH3','Entrepôt Arras'       ,'Arras'),
 ('CDK','Cross-dock saisonnier','Lille');

-- ---------- Localisations : 60 par site (allées A-F, 10 travées) -----
INSERT INTO wms.localisations(site_id, code, type, capacite_max)
SELECT s.site_id,
       chr(65 + (g/10)) || '-' || lpad((g%10+1)::text,2,'0') || '-1' AS code,
       (ARRAY['PICKING','PICKING','PICKING','MASSE']::wms.type_localisation[])[1+(g%4)],
       1000
FROM wms.sites s, generate_series(0,59) g;

-- ---------- Articles : 600 par client (1800 SKU) ---------------------
INSERT INTO wms.articles(client_id, sku, libelle, longueur_mm, largeur_mm, hauteur_mm, poids_g)
SELECT c.client_id,
       c.code || '-SKU-' || lpad(g::text,5,'0'),
       'Article ' || c.code || ' ' || g,
       50 + (g*7  % 1150),
       50 + (g*13 % 750),
       20 + (g*5  % 480),
       100 + (g*17 % 24900)
FROM wms.clients c, generate_series(1,600) g;

-- ---------- Mapping article -> localisation "maison" -----------------
CREATE TEMP TABLE art_home AS
SELECT a.article_id, a.client_id,
       l.localisation_id, l.site_id,
       row_number() OVER (ORDER BY a.article_id) AS rn
FROM wms.articles a
JOIN LATERAL (
    SELECT localisation_id, site_id
    FROM wms.localisations
    WHERE type IN ('PICKING','MASSE')
    ORDER BY (a.article_id * 2654435761)::bigint % 1000, localisation_id
    LIMIT 1
) l ON true;

-- ---------- Phase A : stock initial (1 ENTREE par article) -----------
INSERT INTO wms.mouvements(client_id, article_id, site_id, type, quantite,
                           localisation_dst, reference, date_mouvement)
SELECT client_id, article_id, site_id, 'ENTREE', 2000, localisation_id,
       'INIT-STOCK', now() - interval '90 days'
FROM art_home;

-- ---------- Phase B : 120 000 mouvements d'historique (picking) ------
-- SORTIE de 1 à 3 unités depuis la localisation maison (stock toujours > 0).
INSERT INTO wms.mouvements(client_id, article_id, site_id, type, quantite,
                           localisation_src, reference, date_mouvement)
SELECT h.client_id, h.article_id, h.site_id, 'SORTIE',
       1 + (g % 3),
       h.localisation_id,
       'CMD-' || lpad((g%100000)::text,6,'0'),
       now() - (interval '90 days') + (g * interval '60 seconds')
FROM generate_series(1,120000) g
JOIN art_home h ON h.rn = 1 + (g::bigint * 48271) % 1800;

-- ---------- Quelques ENTREE de réappro (volume + diversité) ----------
INSERT INTO wms.mouvements(client_id, article_id, site_id, type, quantite,
                           localisation_dst, reference, date_mouvement)
SELECT h.client_id, h.article_id, h.site_id, 'ENTREE', 500,
       h.localisation_id, 'REAPPRO',
       now() - (interval '30 days') + (g * interval '30 seconds')
FROM generate_series(1,10000) g
JOIN art_home h ON h.rn = 1 + (g::bigint * 40503) % 1800;

ANALYZE;

-- ---------- Contrôles ------------------------------------------------
SELECT 'clients'      AS table, count(*) FROM wms.clients
UNION ALL SELECT 'sites',        count(*) FROM wms.sites
UNION ALL SELECT 'localisations',count(*) FROM wms.localisations
UNION ALL SELECT 'articles',     count(*) FROM wms.articles
UNION ALL SELECT 'stock',        count(*) FROM wms.stock
UNION ALL SELECT 'mouvements',   count(*) FROM wms.mouvements
ORDER BY 1;
