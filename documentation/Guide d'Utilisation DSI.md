
# 🛠️ NTL-SysToolbox : Guide d'Utilisation DSI

Ce dépôt contient la suite d'outils d'administration pour la maintenance, le diagnostic et l'audit de l'infrastructure de **NordTransit Logistics**.

---

## 🚀 Présentation des Modules

### 1. Diagnostic Infrastructure (`diagnostique_infra.py`)

Ce module effectue un bilan de santé instantané des serveurs critiques.

* **Fonctionnalités** : Vérification de la disponibilité des ports (SSH, HTTPS, LDAP, RDP, MySQL) et test de connexion applicative avancé au serveur de base de données.
* **Résultats** : Un résumé visuel en console et un rapport détaillé généré dans `/rapports_ntl/` au format JSON.

### 2. Sauvegarde Base de Données (`backup_mysql.py`)

Assure la protection des données du serveur **WMS-DB** (`192.168.1.14`).

* **Fonctionnalités** : Export complet (`--all-databases`) incluant routines, triggers et événements.
* **Sécurité** : Utilise le mode `--single-transaction` pour ne pas bloquer la production.
* **Destination** : Sauvegardes stockées dans le dossier `/backups_mysql/`.

### 3. Audit d'Obsolescence & EOL (`audit.py`)

Outil de gestion du cycle de vie du parc informatique.

* **Analyse** : Détection active sur le réseau et croisement avec l'inventaire connu.
* **Indicateurs de Risque** :
* 🔴 **CRITIQUE** : Système obsolète (EOL).
* 🟠 **ÉLEVÉ** : Fin de support < 6 mois.


* **Export** : Génération automatique d'un rapport **CSV** pour exploitation sur Excel.

---

## 💻 Tableau de Bord de l'Infrastructure

| Hôte | IP | OS | Rôle |
| --- | --- | --- | --- |
| **AD-01 / 02** | `192.168.1.10/11` | Windows Server 2019 | Contrôleurs de Domaine |
| **WMS-DB** | `192.168.1.14` | Ubuntu 20.04 LTS | Base de données MySQL |
| **WMS-APP** | `192.168.1.15` | Ubuntu 20.04 LTS | Serveur Web applicatif |
| **GRAFANA** | `192.168.1.13` | Ubuntu 22.04 LTS | Supervision |
| **PFSENSE** | `192.168.1.1` | pfSense 2.7 | Firewall LAN |

---

## 📖 Guide de lancement des scripts

Suivez ces étapes pour exécuter les outils en toute sécurité sur l'environnement de production.

### 1. Vérification des prérequis

Assurez-vous que Python et son gestionnaire de paquets sont correctement installés :

```bash
python3 --version
pip3 --version

```

### 2. Accès Root et Répertoire

Connectez-vous avec les privilèges d'administrateur et placez-vous dans le répertoire racine :

```bash
# Mot de passe : mspr25@
su - 
cd /root

```

### 3. Activation de l'environnement et lancement

Pour garantir que toutes les dépendances (comme `questionary` ou `pymysql`) sont disponibles, activez l'environnement virtuel avant de lancer le sélecteur :

```bash
# Activation de l'environnement virtuel
source .venv/bin/activate 

# Lancement de l'interface unifiée
python3 selecteur.py

```

---

## ⚠️ Notes de Sécurité

* **Externalisation** : Le script de sauvegarde crée des fichiers locaux. Il est impératif de les déplacer vers un stockage externe (NAS/Cloud).
* **Privilèges** : L'audit réseau nécessite l'accès root pour l'exécution des commandes réseau avancées.

---

*Dernière mise à jour : 8 Janvier  2026 - DSI NordTransit Logistics*
