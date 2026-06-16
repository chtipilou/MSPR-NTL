#!/usr/bin/env python3
"""
Script 2 - Backup MySQL Complet Auto
Sauvegarde TOUTES les bases avec configuration centralisée
"""

import subprocess
import json
import sys
from datetime import datetime
from pathlib import Path
from config_loader import load_config

def backup_all_mysql():
    """Backup complet de TOUTES les bases MySQL"""
    
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"[✗] ERREUR: {e}")
        return False
    except Exception as e:
        print(f"[✗] ERREUR de configuration: {e}")
        return False
    
    mysql_config = config.get_mysql_config()
    
    if not mysql_config.get('password'):
        print("[✗] ERREUR: Mot de passe MySQL non configuré")
        print("Veuillez définir le mot de passe dans config.yaml ou via NTL_MYSQL_PASSWORD")
        return False

    print("="*60)
    print("BACKUP MYSQL COMPLET AUTO")
    print(f"Serveur: {mysql_config['host']}")
    print("="*60)
    print()

    # Créer dossier de backup
    backup_dir = Path(mysql_config['backup_dir'])
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_complet_{timestamp}.sql"

    # Commande mysqldump
    cmd = [
        "mysqldump",
        f"--host={mysql_config['host']}",
        f"--user={mysql_config['user']}",
        f"--password={mysql_config['password']}",
        "--all-databases",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--events"
    ]

    print(f"[*] Lancement backup complet...")
    print(f"[*] Fichier: {backup_file}")
    print()

    try:
        # Exécuter mysqldump
        with open(backup_file, 'w') as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )

        if result.returncode == 0:
            size_mb = backup_file.stat().st_size / (1024 * 1024)

            print("="*60)
            print("✓ BACKUP RÉUSSI")
            print("="*60)
            print(f"Fichier: {backup_file}")
            print(f"Taille: {size_mb:.2f} MB")

            # Sauvegarde rapport JSON
            rapport = {
                'timestamp': datetime.now().isoformat(),
                'host': mysql_config['host'],
                'backup_file': str(backup_file),
                'size_mb': round(size_mb, 2),
                'status': 'SUCCESS'
            }

            rapport_file = backup_dir / f"rapport_{timestamp}.json"
            with open(rapport_file, 'w', encoding='utf-8') as f:
                json.dump(rapport, f, indent=2, ensure_ascii=False)

            print(f"Rapport: {rapport_file}")
            print("="*60)

            return True

        else:
            print("✗ ERREUR BACKUP")
            print(result.stderr)
            return False

    except FileNotFoundError:
        print("\n✗ ERREUR: mysqldump non trouvé")
        print("Installer: apt install mysql-client")
        return False

    except subprocess.TimeoutExpired:
        print("\n✗ ERREUR: Timeout (>5min)")
        return False

    except Exception as e:
        print(f"\n✗ ERREUR: {e}")
        return False

def main():
    success = backup_all_mysql()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
