# Plan de reprise d'activité (PRA)

Base de données WMS NordTransit Logistics. Ce plan décrit comment reprendre le service de base de données après un incident, du plus courant au sinistre majeur, en tenant les objectifs fixés par la direction.

## 1. Objectifs

| Objectif | Cible cahier des charges | Résultat mesuré |
|----------|--------------------------|-----------------|
| RTO, durée maximale d'interruption | 1 heure | 10 à 30 secondes sur bascule automatique |
| RPO, perte de données maximale | 15 minutes | Inférieur à 1 minute grâce à l'archivage WAL continu |

Le RTO et le RPO sont tenus avec une marge importante. La bascule entre noeuds est automatique et ne nécessite pas d'intervention humaine. La restauration complète, plus rare, reste dans l'objectif d'une heure.

## 2. Ce qui protège la base

Trois mécanismes complémentaires.

- Réplication en streaming entre pgsql-01 et pgsql-02. Une panne d'un noeud est absorbée par bascule automatique, sans perte.
- Archivage continu des journaux WAL vers le dépôt pgBackRest. Chaque transaction validée est archivée en moins d'une minute. C'est ce qui fixe le RPO.
- Sauvegardes complètes, différentielles et incrémentales sur un dépôt séparé. Elles permettent de reconstruire la base même en cas de perte des deux noeuds.

## 3. Scénarios de sinistre et réponse

### Scénario 1 : panne du noeud primaire

Cause possible : arrêt matériel, plantage du moteur, perte réseau du primaire.

Réponse, automatique. Patroni détecte la perte du verrou de leader dans etcd, promeut le réplica le plus à jour, et HAProxy route immédiatement les écritures vers le nouveau primaire. Aucune perte de données, le réplica était synchrone du flux WAL.

Action humaine. Vérifier l'état avec `patronictl list`, puis réintégrer l'ancien noeud quand il revient avec `systemctl start patroni`. Patroni le resynchronise automatiquement, au besoin par `pg_rewind`.

Durée typique : 10 à 30 secondes pour le retour du service, transparent pour les applications connectées via HAProxy.

### Scénario 2 : panne du noeud réplica

Cause possible : arrêt du second noeud.

Réponse. Le primaire continue de servir seul. Le slot de réplication conserve les journaux WAL nécessaires. Au retour du réplica, la resynchronisation est automatique.

Vigilance. Pendant l'absence du réplica, le cluster n'a plus de candidat à la bascule. Il faut traiter le retour du réplica en priorité, et surveiller l'espace WAL retenu par le slot.

### Scénario 3 : corruption logique ou suppression de données

Cause possible : erreur applicative, mauvaise manipulation, suppression de masse.

Réponse. La réplication ne protège pas de ce cas, car l'erreur se réplique. On utilise la restauration à un instant précis (PITR) de pgBackRest, en visant un horodatage juste avant l'incident.

```
sudo -u postgres pgbackrest --stanza=wms \
     --type=time --target="2026-06-16 09:59:00" --delta restore
```

### Scénario 4 : perte des deux noeuds de base

Cause possible : sinistre sur l'hyperviseur, perte simultanée des deux machines.

Réponse. Reconstruction complète à partir du dépôt pgBackRest sur un noeud sain, procédure du point 4. Le dépôt étant porté par la troisième machine, il survit à la perte des deux noeuds de base.

### Scénario 5 : perte ou indisponibilité du dépôt de sauvegarde

Cause possible : perte de la machine pgsql-lb.

Réponse. Le cluster de base continue de fonctionner, la réplication n'en dépend pas. Il faut reconstruire le dépôt et relancer une sauvegarde complète au plus vite, car pendant ce temps la couverture PRA est dégradée. C'est l'argument pour la copie immuable externalisée, présentée en perspective.

## 4. Procédure de restauration complète

À utiliser pour les scénarios 3, 4 et tout besoin de repartir d'une sauvegarde.

```bash
# 1. Sur le noeud cible, arreter Patroni et vider le repertoire de donnees
systemctl stop patroni

# 2. Restaurer la derniere sauvegarde (option --delta pour ne transferer que le delta)
sudo -u postgres pgbackrest --stanza=wms --delta restore
#    ou restauration a un instant precis :
#    sudo -u postgres pgbackrest --stanza=wms --type=time \
#         --target="AAAA-MM-JJ HH:MM:SS" --delta restore

# 3. Redemarrer Patroni, qui reprend la main sur l'instance restauree
systemctl start patroni

# 4. Controler l'etat du cluster
patronictl -c /etc/patroni/patroni.yml list
```

## 5. Plan périodique de tests de restauration

Une sauvegarde non testée n'est pas une sauvegarde. Le test de restauration est intégré au plan d'exploitation.

| Test | Fréquence | Méthode | Critère de succès |
|------|-----------|---------|-------------------|
| Vérification des sauvegardes | après chaque sauvegarde | `pgbackrest verify`, contrôle des sommes de contrôle | aucune erreur signalée |
| Restauration isolée | mensuelle | restauration vers un répertoire temporaire, démarrage sur un port dédié, comptage des lignes, puis suppression | comptes identiques à la production |
| Bascule de noeud | trimestrielle | switchover contrôlé en fenêtre de maintenance | reprise sous 30 secondes, réplica resynchronisé |

Test de restauration déjà réalisé. La dernière sauvegarde a été restaurée dans une instance isolée. Les comptes ont été retrouvés à l'identique, 1 800 articles et 131 801 mouvements, ce qui confirme l'intégrité. L'instance de test a ensuite été supprimée. La procédure détaillée figure dans le RunBook.

## 6. Rôles et déclenchement

| Phase | Responsable | Action |
|-------|-------------|--------|
| Détection | supervision, N1 | Alerte sur indicateur, vérification de l'état du cluster |
| Qualification | N2, administrateur base | Identifier le scénario, décider bascule ou restauration |
| Exécution | N2 | Appliquer la procédure correspondante |
| Escalade | N3, expert ou éditeur | Corruption non résolue, incident majeur |
| Retour à la normale | N2 | Vérifier réplication, lag, sauvegardes, clôturer l'incident |

La matrice d'escalade complète avec délais cibles figure dans le RunBook.

## 7. Limites connues et perspectives

- etcd sur un seul noeud. Pour un PRA de production, passer à trois noeuds etcd pour le quorum.
- Dépôt de sauvegarde local au siège. Pour se protéger d'un sinistre du site et d'un rançongiciel, ajouter une copie immuable et externalisée. C'est la priorité numéro un de la note de direction.
- Répartiteur de charge unique. Ajouter un second HAProxy avec adresse IP virtuelle pour supprimer ce point de défaillance.
