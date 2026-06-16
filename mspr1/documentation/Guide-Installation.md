# Guide d'Installation et de Déploiement - NTL-SysToolbox

## Table des Matières

1. [Introduction](#introduction)
2. [Prérequis](#prérequis)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Déploiement de l'Agent](#déploiement-de-lagent)
6. [Utilisation](#utilisation)
7. [Sécurité](#sécurité)
8. [Maintenance](#maintenance)
9. [Dépannage](#dépannage)

---

## Introduction

NTL-SysToolbox est une suite d'outils pour la supervision, le diagnostic et la maintenance de l'infrastructure NordTransit Logistics. Elle comprend :

- **Diagnostic Infrastructure** : Test de connectivité et collecte de métriques système
- **Backup MySQL** : Sauvegarde automatisée des bases de données
- **Audit d'Obsolescence** : Analyse EOL du parc informatique
- **Agent Système** : Daemon de collecte de métriques

---

## Prérequis

### Système

- **OS** : Linux (Ubuntu 20.04+, Debian 11+, CentOS 8+) ou Windows Server 2016+
- **Python** : 3.8 ou supérieur
- **Réseau** : Connectivité TCP sur port 6000 (configurable) pour les agents

### Dépendances Python

Toutes les dépendances sont listées dans `requirements.txt` :

```
pyyaml>=6.0
psutil>=5.9.0
pymysql>=1.0.0
questionary>=2.0.0
pytest>=7.0.0
pytest-cov>=4.0.0
```

### Outils Système (optionnels)

- `mysqldump` : Pour les backups MySQL (paquet `mysql-client`)
- `nmap` : Pour les scans réseau avancés (optionnel)

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/chtipilou/MSPR-NTL.git
cd MSPR-NTL
```

### 2. Installer les dépendances

#### Sur Linux

```bash
# Installer Python 3 et pip si nécessaire
sudo apt update
sudo apt install python3 python3-pip

# Installer les dépendances Python
pip3 install -r requirements.txt

# Installer mysql-client pour les backups
sudo apt install mysql-client
```

#### Sur Windows

```powershell
# S'assurer que Python 3.8+ est installé
python --version

# Installer les dépendances
pip install -r requirements.txt
```

### 3. Vérifier l'installation

```bash
python3 --version
pip3 list | grep -E "pyyaml|psutil|pymysql"
```

---

## Configuration

### 1. Créer le fichier de configuration

```bash
cp config.example.yaml config.yaml
```

### 2. Éditer config.yaml

Ouvrez `config.yaml` et configurez vos paramètres :

```yaml
# Configuration MySQL
mysql:
  host: "192.168.1.14"
  user: "root"
  password: "VOTRE_MOT_DE_PASSE_MYSQL"
  port: 3306
  backup_dir: "backups_mysql"

# Configuration Agent
agent:
  port: 6000
  auth_token: "GENERER_UN_TOKEN_SECURISE_ICI"
  timeout: 5

# Configuration Diagnostic
diagnostic:
  output_dir: "rapports_ntl"
  servers:
    - name: "Serveur exemple"
      ip: "192.168.1.10"
      ports:
        ssh_22: 22
      agent_enabled: true
```

**Important** : 
- Générez un token sécurisé pour `auth_token` (minimum 32 caractères aléatoires)
- Ne commitez JAMAIS `config.yaml` dans Git

### 3. Générer un token sécurisé

```bash
# Sur Linux/macOS
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Sur Windows
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Variables d'environnement (alternative)

Vous pouvez utiliser des variables d'environnement pour surcharger la configuration :

```bash
export NTL_MYSQL_PASSWORD="votre_mot_de_passe"
export NTL_MYSQL_HOST="192.168.1.14"
export NTL_AGENT_TOKEN="votre_token_securise"
export NTL_AGENT_PORT="6000"
```

---

## Déploiement de l'Agent

L'agent doit être installé sur chaque serveur que vous souhaitez monitorer.

### Installation sur Linux

#### 1. Copier les fichiers

```bash
# Sur le serveur cible
mkdir -p /opt/ntl-agent
cd /opt/ntl-agent

# Copier ntl_agent.py et config_loader.py (si nécessaire)
# Ou cloner le dépôt complet
```

#### 2. Créer un service systemd

Créez le fichier `/etc/systemd/system/ntl-agent.service` :

```ini
[Unit]
Description=NTL System Metrics Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ntl-agent
Environment="NTL_AGENT_TOKEN=VOTRE_TOKEN_ICI"
ExecStart=/usr/bin/python3 /opt/ntl-agent/ntl_agent.py --port 6000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 3. Activer et démarrer le service

```bash
sudo systemctl daemon-reload
sudo systemctl enable ntl-agent
sudo systemctl start ntl-agent
sudo systemctl status ntl-agent
```

### Installation sur Windows

#### 1. Créer un script de démarrage

Créez `start_agent.bat` :

```batch
@echo off
set NTL_AGENT_TOKEN=VOTRE_TOKEN_ICI
python ntl_agent.py --port 6000
```

#### 2. Configurer comme service Windows (optionnel)

Utilisez NSSM (Non-Sucking Service Manager) :

```powershell
# Télécharger NSSM depuis https://nssm.cc/
nssm install NTLAgent "C:\Python39\python.exe" "C:\path\to\ntl_agent.py --port 6000"
nssm set NTLAgent AppEnvironmentExtra NTL_AGENT_TOKEN=VOTRE_TOKEN_ICI
nssm start NTLAgent
```

### Vérification du déploiement

Testez la connexion à l'agent :

```bash
# Depuis le serveur de diagnostic
python3 -c "from agent_client import query_agent; print(query_agent('192.168.1.10', 6000, 'VOTRE_TOKEN'))"
```

### Configuration du pare-feu

#### Linux (UFW)

```bash
sudo ufw allow 6000/tcp
```

#### Linux (iptables)

```bash
sudo iptables -A INPUT -p tcp --dport 6000 -j ACCEPT
```

#### Windows Firewall

```powershell
New-NetFirewallRule -DisplayName "NTL Agent" -Direction Inbound -Protocol TCP -LocalPort 6000 -Action Allow
```

---

## Utilisation

### Lancer le menu principal

```bash
python3 selecteur.py
```

### Diagnostic Infrastructure

```bash
python3 diagnostique_infra.py
```

**Sorties** :
- Rapport JSON dans `rapports_ntl/diagnostic_YYYYMMDD_HHMMSS.json`
- Résumé console avec statut de chaque serveur
- Métriques système collectées depuis les agents

**Codes de retour** :
- `0` : Tous les serveurs OK
- `1` : Problèmes détectés sur certains serveurs
- `2` : Serveurs critiques down

### Backup MySQL

```bash
python3 backup_mysql.py
```

**Sorties** :
- Fichier SQL dans `backups_mysql/backup_complet_YYYYMMDD_HHMMSS.sql`
- Rapport JSON dans `backups_mysql/rapport_YYYYMMDD_HHMMSS.json`

**Codes de retour** :
- `0` : Backup réussi
- `1` : Backup échoué

### Audit d'Obsolescence

```bash
python3 audit.py
```

Suivez le menu interactif pour :
1. Scanner le réseau et générer un rapport EOL
2. Analyser uniquement les machines inventoriées
3. Lister toutes les versions OS avec dates EOL

**Sorties** :
- Rapport CSV : `audit_eol_ntl_YYYYMMDD_HHMMSS.csv`
- Résumé console avec niveaux de risque

---

## Sécurité

### Bonnes Pratiques

1. **Token d'authentification**
   - Utiliser un token fort (32+ caractères)
   - Ne jamais partager le token
   - Rotation régulière du token (tous les 3-6 mois)

2. **Fichiers de configuration**
   - `config.yaml` est dans `.gitignore`
   - Permissions restrictives : `chmod 600 config.yaml`
   - Backup sécurisé de la configuration

3. **Réseau**
   - L'agent ne doit pas être exposé sur Internet
   - Utiliser un réseau privé ou VPN
   - Filtrage par IP si possible (pare-feu)

4. **Sauvegardes**
   - Déplacer les backups vers un stockage externe
   - Chiffrement des backups recommandé
   - Tests réguliers de restauration

5. **Logs**
   - Surveiller les logs des agents
   - Alertes sur tentatives d'authentification échouées
   - Rotation des logs

### Rotation du Token

```bash
# 1. Générer un nouveau token
NEW_TOKEN=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")

# 2. Mettre à jour config.yaml
sed -i "s/auth_token: .*/auth_token: \"$NEW_TOKEN\"/" config.yaml

# 3. Redémarrer tous les agents avec le nouveau token
# Sur chaque serveur :
export NTL_AGENT_TOKEN="$NEW_TOKEN"
systemctl restart ntl-agent
```

---

## Maintenance

### Logs

```bash
# Logs de l'agent (systemd)
journalctl -u ntl-agent -f

# Logs de l'agent (fichier si configuré)
tail -f /var/log/ntl-agent.log
```

### Mise à jour

```bash
cd /path/to/MSPR-NTL
git pull
pip3 install -r requirements.txt --upgrade

# Redémarrer les agents
sudo systemctl restart ntl-agent
```

### Tests

Exécuter les tests unitaires :

```bash
pytest tests/ -v
pytest tests/ --cov=. --cov-report=html
```

### Monitoring

- Vérifier que les agents répondent
- Surveiller l'espace disque pour les backups
- Vérifier les rapports de diagnostic quotidiens

---

## Dépannage

### L'agent ne démarre pas

```bash
# Vérifier les logs
journalctl -u ntl-agent -n 50

# Vérifier que le port est disponible
netstat -tlnp | grep 6000

# Tester manuellement
python3 ntl_agent.py --port 6000 --token "test"
```

### Erreur "Authentication failed"

- Vérifier que le token est identique dans `config.yaml` et sur l'agent
- Vérifier les variables d'environnement
- Essayer de se connecter sans token pour tester

### Erreur de connexion à l'agent

```bash
# Tester la connectivité réseau
ping 192.168.1.10
telnet 192.168.1.10 6000

# Vérifier le pare-feu
sudo iptables -L -n | grep 6000
```

### Backup MySQL échoue

```bash
# Vérifier que mysqldump est installé
which mysqldump

# Tester la connexion MySQL
mysql -h 192.168.1.14 -u root -p

# Vérifier les permissions du dossier de backup
ls -la backups_mysql/
```

### "Configuration file not found"

```bash
# Vérifier que config.yaml existe
ls -la config.yaml

# Si absent, créer depuis l'exemple
cp config.example.yaml config.yaml
# Puis éditer config.yaml
```

---

## Support

Pour toute question ou problème :

1. Consulter la documentation dans `documentation/`
2. Vérifier les logs
3. Contacter l'équipe DSI NordTransit Logistics

---

*Guide d'Installation - NTL-SysToolbox v1.0 - Janvier 2026*
