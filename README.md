# NTL-SysToolbox

Suite d'outils d'administration et de supervision pour l'infrastructure **NordTransit Logistics**.

## 🚀 Aperçu

NTL-SysToolbox fournit une solution complète pour :

- ✅ **Diagnostic Infrastructure** : Supervision des serveurs et collecte de métriques système
- ✅ **Backup MySQL** : Sauvegarde automatisée des bases de données
- ✅ **Audit d'Obsolescence** : Analyse EOL et gestion du cycle de vie
- ✅ **Agent Système** : Daemon de collecte de métriques multi-plateforme

## 📋 Fonctionnalités

### Diagnostic Infrastructure
- Vérification de la disponibilité des ports critiques (SSH, HTTP/S, LDAP, MySQL, etc.)
- Collecte automatique des métriques système via agents (CPU, RAM, Disque, Uptime, OS)
- Génération de rapports JSON horodatés
- Codes de retour exploitables pour automatisation

### Sauvegarde MySQL
- Backup complet avec routines, triggers et événements
- Configuration centralisée (pas de secrets hardcodés)
- Mode non-bloquant (`--single-transaction`)
- Rapports JSON de sauvegarde

### Audit d'Obsolescence
- Scan réseau automatisé
- Base de données EOL complète (Windows, Linux, VMware, pfSense)
- Analyse de risque (CRITIQUE, ÉLEVÉ, MOYEN, FAIBLE, OK)
- Export CSV pour analyse Excel

### Agent Système
- Collecte de métriques système en temps réel
- Protocole TCP sécurisé avec authentification par token
- Support Windows et Linux
- Configuration par port (défaut: 6000)

## 🔧 Quick Start

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/chtipilou/MSPR-NTL.git
cd MSPR-NTL

# Installer les dépendances
pip3 install -r requirements.txt

# Configurer
cp config.example.yaml config.yaml
# Éditer config.yaml avec vos paramètres
```

### Configuration Minimale

```yaml
mysql:
  host: "192.168.1.14"
  user: "root"
  password: "VOTRE_PASSWORD"

agent:
  port: 6000
  auth_token: "VOTRE_TOKEN_SECURISE"
```

### Déployer l'agent sur un serveur

```bash
# Sur chaque serveur à monitorer
export NTL_AGENT_TOKEN="votre_token"
python3 ntl_agent.py --port 6000
```

### Lancer les outils

```bash
# Menu interactif
python3 selecteur.py

# Ou directement
python3 diagnostique_infra.py
python3 backup_mysql.py
python3 audit.py
```

## 📊 Infrastructure Supportée

| Serveur | IP | Rôle |
|---------|-------------|------|
| AD-01/02 | 192.168.1.10/11 | Contrôleurs de domaine |
| WMS-DB | 192.168.1.14 | Base de données MySQL |
| WMS-APP | 192.168.1.15 | Serveur Web |
| GRAFANA | 192.168.1.13 | Supervision |
| PFSENSE | 192.168.1.1 | Firewall |

## 📚 Documentation

- [Guide d'Utilisation DSI](documentation/Guide%20d'Utilisation%20DSI.md) - Présentation des modules et usage quotidien
- [Guide d'Installation](documentation/Guide-Installation.md) - Installation complète, déploiement et configuration
- [Documentation Technique PDF](Documentation_MSPR_NTL-SysToolbox_final.pdf) - Dossier technique complet

## 🔒 Sécurité

- ⚠️ **Configuration** : `config.yaml` contient des secrets et n'est **pas** versionné (`.gitignore`)
- ⚠️ **Agent** : Utilisation obligatoire d'un token d'authentification en production
- ⚠️ **Réseau** : Ne pas exposer l'agent (port 6000) directement sur Internet
- ⚠️ **Backups** : Déplacer les sauvegardes vers un stockage externe sécurisé

## 🧪 Tests

```bash
# Exécuter les tests
pytest tests/ -v

# Avec couverture
pytest tests/ --cov=. --cov-report=html
```

## 📦 Artefacts Générés

- **Rapports de diagnostic** : `rapports_ntl/diagnostic_YYYYMMDD_HHMMSS.json`
- **Backups MySQL** : `backups_mysql/backup_complet_YYYYMMDD_HHMMSS.sql`
- **Audits EOL** : `audit_eol_ntl_YYYYMMDD_HHMMSS.csv`

## 🔄 Codes de Retour

| Code | Signification |
|------|---------------|
| 0 | Succès complet |
| 1 | Avertissements / Problèmes mineurs |
| 2 | Erreur critique / Serveurs down |

## 🛠️ Prérequis

- Python 3.8+
- Dépendances : `pyyaml`, `psutil`, `pymysql`, `questionary`, `pytest`
- Optionnel : `mysql-client` (pour backups)

## 📝 Licence

Projet interne - NordTransit Logistics

---

**DSI NordTransit Logistics** - Janvier 2026
