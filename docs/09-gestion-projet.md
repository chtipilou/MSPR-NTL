# Gestion de projet

Base de données WMS NordTransit Logistics. Organisation de l'équipe, planning, suivi des tâches, registre de risques et journal des décisions.

Les noms des membres sont à compléter par l'équipe, ils sont marqués entre crochets.

## 1. Organisation de l'équipe

Équipe de quatre personnes. La répartition s'appuie sur les compétences des blocs E6.3 et E6.4.

| Rôle | Responsable | Périmètre |
|------|-------------|-----------|
| Chef de projet | [Prénom Nom] | Planning, jalons, animation des points, relation avec la direction, soutenance |
| Administrateur base de données | [Prénom Nom] | Modèle de données, déploiement du cluster, haute disponibilité, sauvegardes |
| Référent sécurité | [Prénom Nom] | Politique d'accès, moindre privilège, cloisonnement, chiffrement |
| Référent supervision et exploitation | [Prénom Nom] | Indicateurs, tableau de bord, RunBook, analyse de journaux |

Les rôles ne sont pas étanches. Le déploiement et les tests ont mobilisé toute l'équipe, chacun documentant son périmètre.

## 2. Planning et jalons

Préparation cadrée sur 19 heures, conformément au cahier des charges.

| Jalon | Contenu | Livrable associé |
|-------|---------|------------------|
| J1, cadrage | Analyse du besoin, contraintes RTO et RPO, choix du SGBD | Document d'architecture, section choix SGBD |
| J2, conception | Modèle de données, règles d'intégrité, politique d'accès | Modèle de données, politique de sécurité |
| J3, déploiement | Installation du cluster, réplication, répartiteur, pool | Document d'architecture, configurations |
| J4, sécurisation et sauvegardes | Rôles, RLS, chiffrement, pgBackRest, automatisation | Politique de sécurité, scripts de sauvegarde |
| J5, supervision et tests | Indicateurs, tableau de bord, bascule, restauration | Guide de supervision, PRA, RunBook |
| J6, documentation et soutenance | Rédaction des livrables, support de présentation | Tous les documents, slides |

## 3. Suivi des tâches

| Tâche | Responsable | Statut |
|-------|-------------|--------|
| Choix et justification du SGBD | Chef de projet, DBA | Terminé |
| Conception du schéma et des contraintes | DBA | Terminé |
| Déploiement PostgreSQL, Patroni, etcd | DBA | Terminé |
| Mise en place HAProxy et PgBouncer | DBA, exploitation | Terminé |
| Politique de rôles et moindre privilège | Sécurité | Terminé |
| Row Level Security et cloisonnement | Sécurité | Terminé |
| Chiffrement TLS et SCRAM | Sécurité | Terminé |
| Sauvegardes pgBackRest et automatisation | DBA, exploitation | Terminé |
| Test de bascule | DBA | Terminé |
| Test de restauration | DBA, exploitation | Terminé |
| Tableau de bord et indicateurs | Supervision | Terminé |
| Rédaction des livrables | Toute l'équipe | Terminé |
| Note de direction | Chef de projet, sécurité | Terminé |
| Support de soutenance | Chef de projet | Terminé |

## 4. Registre de risques

| Risque | Probabilité | Impact | Mesure de mitigation |
|--------|-------------|--------|----------------------|
| Perte du noeud primaire | Moyenne | Élevé, arrêt des quais | Bascule automatique Patroni sous 30 secondes, réplica synchrone |
| Rançongiciel chiffrant la base et les sauvegardes | Faible | Très élevé, perte de données et arrêt | Sauvegardes vérifiées et restauration testée, copie immuable externalisée recommandée en priorité |
| Mauvaise restauration le jour J | Moyenne | Élevé | Tests de restauration périodiques planifiés, procédure écrite dans le RunBook |
| Fuite de données entre clients | Faible | Élevé, risque RGPD | Cloisonnement par Row Level Security, moindre privilège, chiffrement du transport |
| Erreur ou malveillance interne | Moyenne | Moyen à élevé | Aucun compte applicatif tout puissant, un compte par usage, journalisation des accès |
| Point de défaillance du répartiteur ou de l'annuaire | Moyenne | Moyen | Identifié, parade documentée, second HAProxy et etcd en trois noeuds en perspective |
| Mot de passe root vide sur les VM | Élevée | Moyen | Signalé à l'équipe système, correctif sans coût, hors périmètre base |

Le cahier des charges demandait au moins cinq risques. Sept sont documentés, avec leur mesure.

## 5. Journal des décisions

Trois arbitrages majeurs ont structuré le projet.

### Décision 1, PostgreSQL plutôt que MySQL

Le sujet partait sur MySQL. L'équipe a retenu PostgreSQL 17 pour sa haute disponibilité mature avec Patroni, sa restauration à un instant précis avec pgBackRest, et sa Row Level Security native. Le périmètre fonctionnel reste identique, seul le moteur change. Cette décision est justifiée en détail dans le document d'architecture.

### Décision 2, architecture à trois machines

Plutôt que de tout poser sur une seule machine, l'équipe a séparé les deux moteurs de base sur deux machines distinctes et regroupé les services d'accès et l'annuaire sur une troisième. Une panne matérielle d'un noeud de base n'emporte pas l'autre. Le compromis assumé est la conservation d'un annuaire etcd et d'un répartiteur uniques sur la maquette, avec leur parade documentée.

### Décision 3, dépôt de sauvegarde séparé et restauration testée

Le point faible initial de NTL était des sauvegardes jamais éprouvées. L'équipe a placé le dépôt pgBackRest sur une machine distincte des noeuds de base, automatisé les sauvegardes par minuteries systemd, et surtout réalisé un test de restauration complet. Une sauvegarde non testée n'est pas considérée comme une sauvegarde.

## 6. Communication

Les points d'avancement ont jalonné le projet. La note de direction prépare la communication vers le comité, en langage non technique, et le support de soutenance synthétise le travail pour la présentation finale devant la DSI.
