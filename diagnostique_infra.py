#!/usr/bin/env python3
"""
Script 1 - Diagnostic Auto Infrastructure NTL COMPLET
Lance automatiquement tous les tests sans interaction
"""

import subprocess
import socket
import json
from datetime import datetime
from pathlib import Path

def check_tcp_port(host, port, timeout=2):
    """Test connexion TCP simple"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def test_server(name, ip, ports):
    """Test générique d'un serveur"""
    print(f"[*] Test {name} ({ip})...")
    result = {'ip': ip, 'name': name}
    
    for port_name, port_num in ports.items():
        result[port_name] = check_tcp_port(ip, port_num)
    
    return result

def test_mysql_connection(ip):
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
            user='root',
            password='root',
            connect_timeout=3
        )
        result['connection_test'] = True
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        result['version'] = version[0] if version else 'Unknown'
        conn.close()
    except:
        result['connection_test'] = False
    
    return result

def main():
    print("="*70)
    print("DIAGNOSTIC AUTO INFRASTRUCTURE NTL - COMPLET")
    print("="*70)
    print()
    
    rapport = {
        'timestamp': datetime.now().isoformat(),
        'serveurs': {}
    }
    
    # Liste COMPLÈTE des serveurs
    serveurs = [
        {
            'name': 'ESXi Host',
            'ip': '10.10.10.71',
            'ports': {'https_443': 443, 'ssh_22': 22}
        },
        {
            'name': 'Grafana',
            'ip': '192.168.1.13',
            'ports': {'grafana_3000': 3000, 'ssh_22': 22}
        },
        {
            'name': 'WMS-DB',
            'ip': '192.168.1.14',
            'ports': {'mysql_3306': 3306, 'ssh_22': 22}
        },
        {
            'name': 'Serveur AD 1',
            'ip': '192.168.1.10',
            'ports': {'ldap_389': 389, 'ldaps_636': 636, 'dns_53': 53, 'kerberos_88': 88, 'rdp_3389': 3389}
        },
        {
            'name': 'Serveur AD MSPR',
            'ip': '192.168.1.11',
            'ports': {'ldap_389': 389, 'ldaps_636': 636, 'dns_53': 53, 'kerberos_88': 88, 'rdp_3389': 3389}
        },
        {
            'name': 'WMS-APP',
            'ip': '192.168.1.15',
            'ports': {'http_80': 80, 'https_443': 443, 'ssh_22': 22}
        }
    ]
    
    # Test tous les serveurs
    for srv in serveurs:
        result = test_server(srv['name'], srv['ip'], srv['ports'])
        
        # Test MySQL spécifique
        if 'mysql_3306' in srv['ports'] and result.get('mysql_3306'):
            mysql_info = test_mysql_connection(srv['ip'])
            result.update(mysql_info)
        
        rapport['serveurs'][srv['name']] = result
    
    # Sauvegarde JSON
    output_dir = Path("rapports_ntl")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"diagnostic_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(rapport, f, indent=2, ensure_ascii=False)
    
    # Affichage résumé
    print("\n" + "="*70)
    print("RÉSUMÉ DIAGNOSTIC")
    print("="*70)
    
    for name, data in rapport['serveurs'].items():
        # Compter ports ouverts
        ports_ok = sum(1 for k, v in data.items() if k not in ['ip', 'name', 'connection_test', 'version'] and v == True)
        total_ports = sum(1 for k in data.keys() if k not in ['ip', 'name', 'connection_test', 'version'])
        
        if ports_ok == total_ports and total_ports > 0:
            status = "✓"
        elif ports_ok > 0:
            status = "⚠"
        else:
            status = "✗"
        
        info = f"{status} {name:20} ({data['ip']:15}) - {ports_ok}/{total_ports} ports OK"
        
        # Détail des ports fermés
        ports_fermes = [k.replace('_', ' ').upper() for k, v in data.items() 
                       if k not in ['ip', 'name', 'connection_test', 'version'] and v == False]
        if ports_fermes:
            info += f" | Fermés: {', '.join(ports_fermes)}"
        
        # Info MySQL
        if 'connection_test' in data and data['connection_test']:
            info += f" | MySQL: {data.get('version', 'N/A')}"
        
        print(info)
    
    print("\n" + "="*70)
    print(f"[✓] Rapport complet sauvegardé: {output_file}")
    print("="*70)

if __name__ == "__main__":
    main()
