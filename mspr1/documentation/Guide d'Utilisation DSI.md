
# 🛠️ NTL-SysToolbox : Guide d'Utilisation DSI

Ce dépôt contient la suite d'outils d'administration pour la maintenance, le diagnostic et l'audit de l'infrastructure de **NordTransit Logistics**.

---

## 🚀 Présentation des Modules

### 1. Diagnostic Infrastructure (`diagnostique_infra.py`)

Ce module effectue un bilan de santé instantané des serveurs critiques.

* **Fonctionnalités** : 
  * Vérification de la disponibilité des ports (SSH, HTTPS, LDAP, RDP, MySQL)
  * Test de connexion applicative avancé au serveur de base de données
  * Collecte des métriques système via agents (CPU, RAM, Disque, Uptime, OS)
* **Résultats** : Un résumé visuel en console et un rapport détaillé généré dans `/rapports_ntl/` au format JSON.

### 2. Sauvegarde Base de Données (`backup_mysql.py`)

Assure la protection des données du serveur WMS-DB.

* **Fonctionnalités** : Export complet (`--all-databases`) incluant routines, triggers et événements.
* **Sécurité** : Utilise le mode `--single-transaction` pour ne pas bloquer la production.
* **Configuration** : Utilise les identifiants définis dans `config.yaml`.
* **Destination** : Sauvegardes stockées dans le dossier configuré (par défaut `/backups_mysql/`).

### 3. Audit d'Obsolescence & EOL (`audit.py`)

Outil de gestion du cycle de vie du parc informatique.

* **Analyse** : Détection active sur le réseau et croisement avec l'inventaire connu.
* **Indicateurs de Risque** :
* 🔴 **CRITIQUE** : Système obsolète (EOL).
* 🟠 **ÉLEVÉ** : Fin de support < 6 mois.


* **Export** : Génération automatique d'un rapport **CSV** pour exploitation sur Excel.

### 4. Agent Système (`ntl_agent.py`)

Agent daemon qui expose les métriques système via TCP.

* **Fonctionnalités** : 
  * Collecte CPU, RAM, Disque, Uptime, Version OS
  * Protocole TCP sécurisé avec authentification par token
  * Support multi-plateforme (Windows & Linux)
* **Port** : Configurable (par défaut 6000)
* **Sécurité** : Authentification obligatoire en production

---

## 💻 Tableau de Bord de l'Infrastructure

| Hôte | IP | OS | Rôle |
| --- | --- | --- | --- |
| **AD-01 / 02** | `192.168.1.10/11` | Windows Server 2019 | Contrôleurs de Domaine |
| **WMS-DB** | `192.168.1.14` | Ubuntu 20.04 LTS | Base de données MySQL |
| **WMS-APP** | `192.168.1.15` | Ubuntu 20.04 LTS | Serveur Web applicatif |
| **GRAFANA** | `192.168.1.13` | Windows Server 2025 | Supervision |
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

### 2. Installation des dépendances

Installez les dépendances requises :

```bash
pip3 install -r requirements.txt

```

### 3. Configuration

Copiez le fichier de configuration exemple et configurez vos paramètres :

```bash
cp config.example.yaml config.yaml
# Éditez config.yaml avec vos paramètres réels

```

**Important** : Ne commitez jamais `config.yaml` dans Git. Ce fichier contient des informations sensibles.

Vous pouvez également utiliser des variables d'environnement pour surcharger la configuration :

```bash
export NTL_MYSQL_PASSWORD="votre_mot_de_passe"
export NTL_AGENT_TOKEN="votre_token_securise"

```

### 4. Déploiement de l'agent

Sur chaque serveur à monitorer, installez et démarrez l'agent :

```bash
# Installation
pip3 install -r requirements.txt

# Démarrage de l'agent (avec token de sécurité)
python3 ntl_agent.py --port 6000 --token "VOTRE_TOKEN_ICI"

# Ou via variable d'environnement
export NTL_AGENT_TOKEN="VOTRE_TOKEN_ICI"
python3 ntl_agent.py

```

Pour exécuter l'agent en tant que service système, consultez le guide d'installation complet.

### 5. Lancement de l'interface unifiée

```bash
# Lancement du sélecteur de scripts
python3 selecteur.py

```

Ou exécutez directement les scripts :

```bash
# Diagnostic complet
python3 diagnostique_infra.py

# Backup MySQL
python3 backup_mysql.py

# Audit d'obsolescence
python3 audit.py

```

---

## ⚠️ Notes de Sécurité

* **Configuration** : Ne stockez jamais de mots de passe en clair dans le code. Utilisez `config.yaml` (non versionné) ou des variables d'environnement.
* **Agent** : Toujours utiliser un token d'authentification en production. Ne jamais exposer l'agent directement sur Internet.
* **Externalisation** : Les sauvegardes locales doivent être déplacées vers un stockage externe (NAS/Cloud).
* **Privilèges** : L'audit réseau nécessite l'accès root pour l'exécution des commandes réseau avancées.
* **Fichiers sensibles** : Le fichier `config.yaml` est dans `.gitignore` pour éviter de committer des secrets.

---

## 📊 Codes de Retour

Les scripts retournent des codes de sortie standardisés :

* **0** : Succès - Tous les tests ont réussi
* **1** : Avertissement - Certains problèmes détectés
* **2** : Erreur critique - Serveurs down ou échec complet

---

*Dernière mise à jour : Janvier 2026 - DSI NordTransit Logistics*

