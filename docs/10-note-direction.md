# Note à la direction

De : équipe infrastructure et données
À : comité de direction de NordTransit Logistics
Objet : risques cyber sur la base de données du WMS, impact métier et plan d'action
Date : 16 juin 2026

Document non technique, une page.

## En une phrase

La base de données du WMS est le coeur vital de l'exploitation. Si elle s'arrête ou si elle est compromise, les quatre sites cessent de réceptionner et d'expédier. Nous avons mis en place une architecture qui élimine la plupart de ces risques. Cette note explique lesquels, leur impact pour l'activité, et ce qui reste à décider.

## Pourquoi c'est critique pour NTL

Le WMS pilote les réceptions dès 5 h 30, les préparations et les expéditions jusqu'à 18 h 30, sur Lens, Valenciennes, Arras et le cross-dock. Une indisponibilité, c'est concrètement des quais bloqués et des transporteurs en attente, l'impression d'étiquettes et les terminaux radio à l'arrêt, des commandes e-commerce non honorées en pleine montée de charge. Chaque heure d'arrêt en journée a un coût opérationnel direct et un risque commercial.

## Les quatre risques cyber majeurs et notre réponse

| Risque | Impact métier | Mesure en place | Reste à décider |
|--------|---------------|-----------------|-----------------|
| Rançongiciel chiffrant les données | Arrêt total, perte de données, demande de rançon | Sauvegardes vérifiées et restauration testée, données récupérables en moins d'une heure | Copie immuable hors site, investissement à valider |
| Panne du serveur de base | Arrêt des quatre sites | Bascule automatique sur un second serveur en moins d'une minute, sans intervention | En place |
| Vol ou fuite de données clients | Atteinte au RGPD, perte de confiance des grands comptes | Cloisonnement par client dans la base, accès chiffrés, comptes au strict minimum de droits | Étendre l'authentification forte aux accès d'administration |
| Erreur ou malveillance interne | Suppression ou corruption de données | Aucun compte applicatif tout puissant, un compte par usage, journalisation des accès | Revue trimestrielle des droits |

## Ce que nous garantissons aujourd'hui

- Continuité. Perte de données limitée à moins d'une minute, redémarrage automatique en moins d'une minute. Les objectifs fixés étaient 15 minutes et 1 heure, ils sont largement tenus.
- Récupération prouvée. Nous avons restauré la base à blanc et vérifié que la totalité des données était récupérée.
- Étanchéité. Un terminal d'entrepôt peut seulement saisir des mouvements. Il ne peut ni lire le fichier clients, ni modifier la structure de la base.

## Décisions demandées au comité, par priorité

1. Prioritaire. Copie de sauvegarde immuable et externalisée. C'est la seule protection réellement efficace contre un rançongiciel. Budget à valider.
2. Important. Authentification forte sur tous les accès d'administration et distants, aujourd'hui limitée à l'équipe informatique.
3. Important. Corriger un défaut de configuration système détecté sur les serveurs, un mot de passe administrateur manquant. Action interne sans coût.
4. Recommandé. Doubler le point d'entrée réseau, le répartiteur de charge, pour supprimer le dernier point de défaillance unique.
5. Recommandé. Sensibiliser les super-utilisateurs aux risques cyber, hameçonnage et mots de passe.

## Message clé

L'essentiel du risque technique est maîtrisé. Les décisions ci-dessus relèvent désormais d'arbitrages budgétaires et organisationnels que seule la direction peut trancher. Le risque rançongiciel reste le plus coûteux, c'est la priorité numéro un.
