#!/usr/bin/env python3
"""
Script 1 - Diagnostic Auto Infrastructure NTL COMPLET
Lance automatiquement tous les tests sans interaction
Inclut la collecte des métriques système via agents
"""

import subprocess
import socket
import json
import sys
from datetime import datetime
from pathlib import Path
from config_loader import load_config
from agent_client import query_agent, AgentClient

def check_tcp_port(host, port, timeout=2):
    """Test connexion TCP simple"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def test_server(name, ip, ports):
    """Test générique d'un serveur"""
    print(f"[*] Test {name} ({ip})...")
    result = {'ip': ip, 'name': name}
    
    for port_name, port_num in ports.items():
        result[port_name] = check_tcp_port(ip, port_num)
    
    return result

def test_mysql_connection(ip, mysql_config):
    """Test connexion MySQL avancé"""
    result = {
        'port_3306': check_tcp_port(ip, 3306),
        'connection_test': False,
        'version': None
    }
    
    try:
        import pymysql
        conn = pymysql.connect(
            host=ip,
            user=mysql_config['user'],
            password=mysql_config['password'],
            connect_timeout=3
        )
        result['connection_test'] = True
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        result['version'] = version[0] if version else 'Unknown'
        conn.close()
    except Exception as e:
        result['connection_test'] = False
        result['error'] = str(e)
    
    return result

def main():
    print("="*70)
    print("DIAGNOSTIC AUTO INFRASTRUCTURE NTL - COMPLET")
    print("="*70)
    print()
    
    try:
        config = load_config()
    except FileNotFoundError as e:
        print(f"[✗] ERREUR: {e}")
        return 1
    except Exception as e:
        print(f"[✗] ERREUR de configuration: {e}")
        return 1
    
    mysql_config = config.get_mysql_config()
    agent_config = config.get_agent_config()
    diag_config = config.get_diagnostic_config()
    
    rapport = {
        'timestamp': datetime.now().isoformat(),
        'serveurs': {},
        'summary': {
            'total_servers': 0,
            'servers_up': 0,
            'servers_with_issues': 0,
            'servers_down': 0
        }
    }
    
    serveurs = diag_config.get('servers', [])
    
    if not serveurs:
        print("[!] ATTENTION: Aucun serveur configuré dans config.yaml")
        return 1
    
    # Test tous les serveurs
    for srv in serveurs:
        name = srv.get('name')
        ip = srv.get('ip')
        ports = srv.get('ports', {})
        agent_enabled = srv.get('agent_enabled', False)
        
        print(f"[*] Test {name} ({ip})...")
        result = test_server(name, ip, ports)
        
        # Test MySQL spécifique
        if 'mysql_3306' in ports and result.get('mysql_3306'):
            mysql_info = test_mysql_connection(ip, mysql_config)
            result.update(mysql_info)
        
        # Interroger l'agent si activé
        if agent_enabled:
            port = agent_config['port']
            token = agent_config.get('auth_token')
            timeout = agent_config.get('timeout', 5)

            # Debug: vérifier que l'agent tourne et expose bien le port
            print(f"    [*] Verification agent sur port {port}...")
            client = AgentClient(ip, port, token, timeout)
            debug_info = client.debug()

            if debug_info:
                print(f"    [✓] Agent DEBUG: v{debug_info.get('agent_version')} | "
                      f"port={debug_info.get('port')} | "
                      f"socket={debug_info.get('socket_listening')} | "
                      f"metriques={debug_info.get('metrics_collection_ok')}")
                result['agent_debug'] = debug_info
            else:
                print(f"    [!] Agent DEBUG: commande debug indisponible (ancienne version?)")

            # Collecter les métriques
            print(f"    [*] Interrogation agent sur port {port}...")
            agent_response = query_agent(ip, port, token, timeout)

            if agent_response['status'] == 'success':
                metrics = agent_response['metrics']
                result['agent'] = metrics

                # Validation des données récupérées
                validation_errors = []
                if not metrics.get('hostname'):
                    validation_errors.append("hostname manquant")
                if not metrics.get('os', {}).get('system'):
                    validation_errors.append("info OS manquante")
                cpu_pct = metrics.get('cpu', {}).get('usage_percent')
                if cpu_pct is None or not (0 <= cpu_pct <= 100):
                    validation_errors.append(f"CPU invalide: {cpu_pct}")
                ram_pct = metrics.get('memory', {}).get('percent')
                if ram_pct is None or not (0 <= ram_pct <= 100):
                    validation_errors.append(f"RAM invalide: {ram_pct}")
                if not metrics.get('disk', {}).get('partitions'):
                    validation_errors.append("aucune partition disque")
                if not metrics.get('uptime', {}).get('uptime_seconds'):
                    validation_errors.append("uptime manquant")

                if validation_errors:
                    print(f"    [!] Agent: Métriques collectées AVEC anomalies: {', '.join(validation_errors)}")
                    result['agent_validation'] = {'ok': False, 'errors': validation_errors}
                else:
                    print(f"    [✓] Agent: Métriques système collectées et validées")
                    result['agent_validation'] = {'ok': True, 'errors': []}
            else:
                result['agent'] = {
                    'status': 'unavailable',
                    'error': agent_response.get('error', 'Unknown error')
                }
                result['agent_validation'] = {'ok': False, 'errors': ['agent indisponible']}
                print(f"    [!] Agent: {agent_response.get('error', 'Indisponible')}")
        
        rapport['serveurs'][name] = result
    
    # Calculer le résumé
    rapport['summary']['total_servers'] = len(serveurs)
    
    for name, data in rapport['serveurs'].items():
        ports_ok = sum(1 for k, v in data.items() if k.endswith(('_22', '_80', '_443', '_389', '_636', '_53', '_88', '_3389', '_3000', '_3306')) and v == True)
        total_ports = sum(1 for k in data.keys() if k.endswith(('_22', '_80', '_443', '_389', '_636', '_53', '_88', '_3389', '_3000', '_3306')))
        
        if total_ports > 0:
            if ports_ok == total_ports:
                rapport['summary']['servers_up'] += 1
            elif ports_ok > 0:
                rapport['summary']['servers_with_issues'] += 1
            else:
                rapport['summary']['servers_down'] += 1
    
    # Sauvegarde JSON
    output_dir = Path(diag_config.get('output_dir', 'rapports_ntl'))
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"diagnostic_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    
    # Affichage résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DIAGNOSTIC")
    print("="*70)
    print(f"Serveurs testés: {rapport['summary']['total_servers']}")
    print(f"✓ OK: {rapport['summary']['servers_up']} | ⚠ Alertes: {rapport['summary']['servers_with_issues']} | ✗ Down: {rapport['summary']['servers_down']}")
    print("="*70)
    
    for name, data in rapport['serveurs'].items():
        # Compter ports ouverts
        ports_ok = sum(1 for k, v in data.items() if k.endswith(('_22', '_80', '_443', '_389', '_636', '_53', '_88', '_3389', '_3000', '_3306')) and v == True)
        total_ports = sum(1 for k in data.keys() if k.endswith(('_22', '_80', '_443', '_389', '_636', '_53', '_88', '_3389', '_3000', '_3306')))
        
        if ports_ok == total_ports and total_ports > 0:
            status = "✓"
        elif ports_ok > 0:
            status = "⚠"
        else:
            status = "✗"
        
        info = f"{status} {name:20} ({data['ip']:15}) - {ports_ok}/{total_ports} ports OK"
        
        # Détail des ports fermés
        ports_fermes = [k.replace('_', ' ').upper() for k, v in data.items() 
                       if k.endswith(('_22', '_80', '_443', '_389', '_636', '_53', '_88', '_3389', '_3000', '_3306')) and v == False]
        if ports_fermes:
            info += f" | Fermés: {', '.join(ports_fermes)}"
        
        # Info MySQL
        if 'connection_test' in data and data['connection_test']:
            info += f" | MySQL: {data.get('version', 'N/A')}"
        
        # Info Agent
        if 'agent' in data:
            if data['agent'].get('status') == 'unavailable':
                info += f" | Agent: Indisponible"
            else:
                cpu_usage = data['agent'].get('cpu', {}).get('usage_percent', 'N/A')
                mem_percent = data['agent'].get('memory', {}).get('percent', 'N/A')
                validation = data.get('agent_validation', {})
                valid_tag = "OK" if validation.get('ok') else "WARN"
                info += f" | Agent: {valid_tag} (CPU:{cpu_usage}% RAM:{mem_percent}%)"
                if not validation.get('ok') and validation.get('errors'):
                    info += f" [{', '.join(validation['errors'])}]"
        
        print(info)
    
    print("\n" + "="*70)
    print(f"[✓] Rapport complet sauvegardé: {output_file}")
    print("="*70)
    
    # Code de retour basé sur le statut des serveurs
    if rapport['summary']['servers_down'] > 0:
        return 2
    elif rapport['summary']['servers_with_issues'] > 0:
        return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main())
