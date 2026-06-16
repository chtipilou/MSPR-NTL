---
marp: true
theme: default
paginate: true
---

# Conception, exploitation et protection d'une base de données WMS

NordTransit Logistics
MSPR, blocs E6.3 et E6.4

Équipe projet : [Prénom Nom], [Prénom Nom], [Prénom Nom], [Prénom Nom]

---

## Le contexte

NTL, PME logistique des Hauts-de-France. Siège à Lille, entrepôts à Lens, Valenciennes et Arras, plus un cross-dock saisonnier.

Le WMS est l'application coeur de métier.

Le problème : si la base du WMS tombe, les quatre sites arrêtent réception et expédition entre 5 h 30 et 18 h 30. Fenêtres de maintenance très courtes, surtout la nuit.

Notre mission : concevoir et industrialiser la nouvelle base WMS. Technologie, haute disponibilité, sécurité, performances, exploitation.

---

## Notre démarche

1. Analyse du besoin et des contraintes, RTO 1 h, RPO 15 min, sites critiques.
2. Choix du SGBD et de l'architecture.
3. Conception du modèle de données.
4. Déploiement du cluster sur l'infrastructure Proxmox de NTL.
5. Sécurisation, sauvegardes, supervision.
6. Tests réels, bascule, restauration, contrôles de droits.

Tout a été déployé et testé, pas seulement décrit.

---

## Choix du SGBD, PostgreSQL

Le sujet partait sur MySQL. Nous avons retenu PostgreSQL 17.

Raisons principales.

- Haute disponibilité mature avec Patroni, bascule automatique.
- Sauvegarde incrémentale par blocs et restauration à un instant précis avec pgBackRest.
- Sécurité, Row Level Security, SCRAM-SHA-256, TLS natif.
- Index BRIN, adaptés aux mouvements horodatés volumineux.
- Open source, sans coût de licence pour l'équivalent haute disponibilité.

---

## L'architecture

Trois machines.

- pgsql-01, 192.168.10.61, PostgreSQL primaire.
- pgsql-02, 192.168.10.60, réplica en streaming.
- pgsql-lb, 192.168.10.62, etcd, HAProxy, PgBouncer, dépôt de sauvegarde.

Patroni orchestre les deux bases via etcd. HAProxy interroge l'API de Patroni, les écritures vont au primaire sur le port 5000, les lectures au réplica sur le port 5001. PgBouncer mutualise les connexions sur le port 6432.

---

## Le modèle de données

Schéma wms, six entités reliées par des contraintes explicites. Clients, sites, articles avec dimensions et poids, localisations, stock, mouvements.

Intégrité garantie.

- Séparation des données par client, clé étrangère composite.
- Stock toujours positif, maintenu automatiquement par un déclencheur à chaque mouvement.
- Règles métier sur les types de mouvement, entrée, sortie, transfert.

Jeu de test, 1 800 articles, 131 800 mouvements.

---

## Performances

Index choisis selon les requêtes fréquentes, B-tree pour les recherches ponctuelles, BRIN pour l'historique des mouvements.

Mesures sur le volume réel.

- Stock courant d'un article, 0,10 ms.
- Historique d'un article sur 30 jours, 0,14 ms.
- Volume de mouvements par site sur 7 jours, 7,4 ms.

L'index BRIN sur les dates est environ mille fois plus petit qu'un B-tree.

---

## Sécurité, le moindre privilège

Aucun compte applicatif n'est superutilisateur. Un compte par usage.

- wms_app, lecture et écriture des mouvements.
- wms_readonly, lecture seule.
- wms_mvt, uniquement l'écriture des mouvements, terminaux RF.
- wms_dba, administration, sans droits superutilisateur.

Tests réalisés, wms_mvt ne peut pas lire les clients ni créer de table, wms_readonly ne peut pas écrire.

Cloisonnement par client en base avec Row Level Security, TLS obligatoire, mots de passe SCRAM-SHA-256.

---

## Haute disponibilité et reprise

Objectifs du cahier des charges, RTO 1 h, RPO 15 min.

Résultats obtenus.

- RPO inférieur à 1 minute, archivage WAL continu.
- RTO de l'ordre de 10 à 30 secondes sur bascule.

Démonstration faite en direct.

- Bascule du primaire vers le réplica en environ 10 secondes.
- HAProxy a suivi automatiquement le nouveau primaire.
- Restauration d'une sauvegarde testée, 131 801 mouvements retrouvés.

---

## Sauvegardes

pgBackRest, dépôt centralisé sur pgsql-lb.

- Complète hebdomadaire, différentielle quotidienne, incrémentale toutes les 6 heures.
- Archivage WAL continu pour la reprise au point dans le temps.
- Rotation et rétention automatiques.
- Vérification après chaque sauvegarde, notification en cas d'échec.

Automatisé par des minuteries systemd. Restauration testée et validée.

---

## Supervision

Prometheus collecte les métriques, Grafana affiche le tableau de bord.

Cinq indicateurs critiques avec seuils.

1. Lag de réplication, alerte 30 s, critique 120 s.
2. Connexions actives sur 200, alerte 70 pour cent, critique 90 pour cent.
3. Espace disque, alerte 75 pour cent, critique 90 pour cent.
4. Échecs d'archivage des sauvegardes, critique au premier échec.
5. Débit de transactions et latence.

Pour chaque alerte, une procédure d'analyse est documentée.

---

## Gestion de projet

Organisation de l'équipe, chef de projet, administrateur base, référent sécurité, référent supervision.

Jalons, analyse, conception, déploiement, sécurisation, tests, documentation.

Registre de risques, extrait.

- Perte de la base, couverte par haute disponibilité et sauvegardes.
- Mauvaise restauration, test de restauration périodique.
- Fuite de données, moindre privilège et cloisonnement.

Décisions majeures, PostgreSQL plutôt que MySQL, architecture à trois noeuds, dépôt de sauvegarde séparé.

---

## Difficultés rencontrées

- Réseau des machines isolé au départ, résolution de noms à réparer.
- Dépendance Patroni pour etcd à installer manuellement.
- Format de configuration Patroni à ajuster pour l'écoute réseau.
- Authentification PgBouncer en SCRAM, résolue par le pass through.

Chaque point a été diagnostiqué et corrigé, avec les preuves dans les livrables.

---

## Perspectives

- Copie de sauvegarde immuable et externalisée, anti-rançongiciel.
- etcd en trois noeuds et second répartiteur de charge pour supprimer les points de défaillance uniques.
- Authentification forte sur les accès d'administration.
- Intégration des alertes dans un outil de notification.

---

## Conclusion

Une base WMS en haute disponibilité, sécurisée, sauvegardée et supervisée, déployée et testée sur l'infrastructure de NTL.

Objectifs RTO et RPO non seulement atteints, mais dépassés.

Merci de votre attention.
