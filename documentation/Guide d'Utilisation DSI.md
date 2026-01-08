# 🛠️ NTL-SysToolbox : Guide d'Utilisation DSI

Ce dépôt contient la suite d'outils d'administration pour la maintenance, le diagnostic et l'audit de l'infrastructure de **NordTransit Logistics**.

---

## 🚀 Lancement Rapide

Pour accéder à l'interface unifiée et éviter de lancer les scripts manuellement, utilisez le sélecteur interactif :

```bash
python selecteur.py

```

* **Navigation** : Utilisez les flèches du clavier pour choisir un module.
* **Validation** : Appuyez sur `Entrée` pour exécuter le script sélectionné.

---

## 📋 Présentation des Modules

### 1. Diagnostic Infrastructure (`diagnostique_infra.py`)

Ce module effectue un bilan de santé instantané des serveurs critiques.

* **Fonctionnalités** :
* Vérification de la disponibilité des ports (SSH, HTTPS, LDAP, RDP, MySQL).
* Test de connexion applicative avancé au serveur de base de données.
* Identification précise des services hors-ligne.


* **Résultats** :
* **Console** : Résumé visuel avec icônes de statut (✓ OK, ⚠ Partiel, ✗ Hors-ligne).
* **Fichier** : Rapport détaillé généré dans `/rapports_ntl/` au format JSON.



### 2. Sauvegarde Base de Données (`backup_mysql.py`)

Assure la protection des données du serveur **WMS-DB** (`192.168.1.14`).

* **Fonctionnalités** :
* Export complet (`--all-databases`) incluant routines, triggers et événements.
* Mode `--single-transaction` pour garantir la cohérence sans bloquer la production.


* **Maintenance** :
* **Destination** : Sauvegardes stockées dans le dossier `/backups_mysql/`.
* **Prérequis** : Nécessite l'installation de `mysql-client` (`mysqldump`).
* **Sécurité** : Identifiants pré-configurés pour l'utilisateur `root`.



### 3. Audit d'Obsolescence & EOL (`audit.py`)

Outil de gestion du cycle de vie du parc informatique.

* **Options de l'Audit** :
* **Scan Réseau** : Détection active sur `192.168.1.0/24` via scan de ports et inventaire connu.
* **Analyse Inventaire** : Focus uniquement sur les machines critiques documentées.
* **Base EOL** : Consultation des dates de fin de support pour Windows, Linux (Ubuntu, Debian, CentOS) et ESXi.


* **Gestion des Risques** :
* 🔴 **CRITIQUE** : Système obsolète — Migration urgente requise.
* 🟠 **ÉLEVÉ** : Fin de support à moins de 6 mois.
* ✅ **OK** : Support actif.


* **Export** : Génération automatique d'un rapport **CSV** (`audit_eol_ntl_YYYYMMDD.csv`) pour exploitation sur Excel.

---

## 💻 Tableau de Bord de l'Infrastructure

| Hôte | IP | OS | Rôle |
| --- | --- | --- | --- |
| **AD-01 / 02** | `192.168.1.10/11` | Windows Server 2019 | Contrôleurs de Domaine |
| **WMS-DB** | `192.168.1.14` | Ubuntu 20.04 LTS | Base de données MySQL |
| **WMS-APP** | `192.168.1.15` | Ubuntu 20.04 LTS | Serveur Web applicatif |
| **GRAFANA** | `192.168.1.13` | Ubuntu 22.04 LTS | Supervision |
| **PFSENSE** | `192.168.1.1` | pfSense 2.7 | Firewall LAN |
| **ESXi Host** | `10.10.10.71` | VMware ESXi | Hyperviseur |

---

## ⚠️ Notes de Sécurité et Maintenance

* **Privilèges** : L'audit réseau (`audit.py`) peut nécessiter des privilèges administrateur pour l'envoi de paquets ICMP/Raw.
* **Externalisation** : Le script de backup gère uniquement la création locale. Il est impératif de configurer un transfert (SCP/RSYNC) vers un stockage externe (NAS/Cloud).
* **Dépendances** : Assurez-vous d'avoir installé les bibliothèques `questionary` et `pymysql` via pip avant le premier lancement.

---

*Dernière mise à jour : Janvier 2026 - DSI NordTransit Logistics*

**Souhaitez-vous que je génère le fichier `requirements.txt` correspondant à ces scripts ?**
