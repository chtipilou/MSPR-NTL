# MSPR NTL - Base de données WMS NordTransit Logistics

Conception, exploitation et protection de la base de données du système de gestion d'entrepôt (WMS) de NordTransit Logistics, via un SGBD relationnel en haute disponibilité.

Blocs E6.3 (gérer les données selon une approche DevOps ou SysOps) et E6.4 (gérer un projet selon une approche DevOps ou SysOps).

## Résultat livré

Un cluster PostgreSQL 17 en haute disponibilité avec bascule automatique, répartiteur de charge, sécurité au moindre privilège, sauvegardes automatisées et testées, et supervision. L'ensemble a été déployé et validé sur l'infrastructure Proxmox de NTL, pas seulement décrit sur le papier.

Le sujet d'origine décrivait une base MySQL. Le SGBD retenu et déployé est PostgreSQL 17. La justification de ce choix figure dans le document d'architecture.

Objectifs du cahier des charges : RTO 1 h, RPO 15 min. Résultats mesurés : RTO de l'ordre de 10 à 30 secondes sur bascule, RPO inférieur à 1 minute.

## Organisation du dépôt

| Dossier | Contenu |
|---------|---------|
| `docs/` | Les livrables rédigés (architecture, modèle de données, PRA, sécurité, exploitation, supervision, optimisation, analyse de logs, gestion de projet, note de direction) |
| `docs/soutenance/` | Support de présentation pour la soutenance |
| `sql/` | Schéma métier, jeu de données, politique de sécurité, déclencheurs |
| `configs/` | Configurations d'infrastructure (Patroni, HAProxy, PgBouncer, etcd, pgBackRest, Prometheus, Grafana) |
| `scripts/` | Script de sauvegarde et unités systemd associées |
| `mspr1/` | Archive de la MSPR précédente (suite d'outils NTL-SysToolbox), conservée pour mémoire |

## Les livrables

Les documents sont numérotés dans l'ordre de lecture conseillé.

| Document | Objet |
|----------|-------|
| [01 - Architecture technique](docs/01-architecture-technique.md) | Choix du SGBD, architecture HA, hébergement, composants, réseau |
| [02 - Modèle de données](docs/02-modele-donnees.md) | MCD, MLD, dictionnaire de données, règles d'intégrité |
| [03 - Plan de reprise d'activité](docs/03-plan-reprise-activite.md) | Scénarios de sinistre, RTO/RPO, procédures de reprise, tests |
| [04 - Politique de sécurité et d'accès](docs/04-politique-securite-acces.md) | Moindre privilège, cloisonnement par client, chiffrement |
| [05 - RunBook d'exploitation](docs/05-runbook-exploitation.md) | Démarrage/arrêt, contrôle de santé, incidents, escalade |
| [06 - Guide de supervision](docs/06-guide-supervision.md) | Cinq indicateurs critiques, seuils, procédures de remédiation |
| [07 - Démarche d'optimisation](docs/07-demarche-optimisation.md) | Usages, choix d'index, mesures, résultats |
| [08 - Analyse de journaux](docs/08-analyse-logs.md) | Sources, motifs, seuils, corrélation |
| [09 - Gestion de projet](docs/09-gestion-projet.md) | Rôles, planning, risques, décisions, suivi des tâches |
| [10 - Note de direction](docs/10-note-direction.md) | Risques cyber sur la base, impact métier, mesures |
| [11 - Technical documentation (EN)](docs/11-technical-documentation-en.md) | English summary of the architecture and operations |

## Architecture en bref

Trois machines virtuelles sur le réseau 192.168.10.0/24 :

- `pgsql-01` (192.168.10.61) : PostgreSQL primaire, orchestré par Patroni.
- `pgsql-02` (192.168.10.60) : réplica en streaming, candidat à la bascule.
- `pgsql-lb` (192.168.10.62) : etcd, HAProxy, PgBouncer, dépôt de sauvegarde pgBackRest.

Patroni arbitre l'élection du primaire via etcd. HAProxy interroge l'API REST de Patroni pour router les écritures vers le primaire courant (port 5000) et les lectures vers le réplica (port 5001). En cas de bascule, le répartiteur suit automatiquement le nouveau primaire.

## Mise en garde sur les secrets

Aucun mot de passe réel n'est versionné. Les configurations publiées remplacent les secrets par le marqueur `__MOT_DE_PASSE__`. Les scripts SQL injectent les mots de passe par variables psql au moment du déploiement. Le fichier `config.yaml` et tout fichier `secrets.env` sont exclus par `.gitignore`.

---

NordTransit Logistics, juin 2026.
