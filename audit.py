#!/usr/bin/env python3
"""
NTL-SysToolbox - Module d'Audit d'Obsolescence
Scan réseau optimisé et analyse EOL - Export CSV uniquement
"""

import subprocess
import csv
import sys
import socket
from datetime import datetime
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Base de données EOL complète
EOL_DATABASE = {
    "Windows Server 2008": {"mainstream": "2015-01-13", "extended": "2020-01-14", "status": "EOL"},
    "Windows Server 2008 R2": {"mainstream": "2015-01-13", "extended": "2020-01-14", "status": "EOL"},
    "Windows Server 2012": {"mainstream": "2018-10-09", "extended": "2023-10-10", "status": "EOL"},
    "Windows Server 2012 R2": {"mainstream": "2018-10-09", "extended": "2023-10-10", "status": "EOL"},
    "Windows Server 2016": {"mainstream": "2022-01-11", "extended": "2027-01-12", "status": "Extended Support"},
    "Windows Server 2019": {"mainstream": "2024-01-09", "extended": "2029-01-09", "status": "Extended Support"},
    "Windows Server 2022": {"mainstream": "2026-10-13", "extended": "2031-10-14", "status": "Mainstream Support"},
    "Windows 7": {"mainstream": "2015-01-13", "extended": "2020-01-14", "status": "EOL"},
    "Windows 10": {"mainstream": "2020-10-13", "extended": "2025-10-14", "status": "Extended Support"},
    "Windows 11": {"mainstream": "2024-10-10", "extended": "2026-10-08", "status": "Mainstream Support"},
    "Ubuntu 16.04 LTS": {"mainstream": "2021-04-02", "extended": "2026-04-02", "status": "Extended Security"},
    "Ubuntu 18.04 LTS": {"mainstream": "2023-05-31", "extended": "2028-04-30", "status": "Extended Security"},
    "Ubuntu 20.04 LTS": {"mainstream": "2025-04-02", "extended": "2030-04-02", "status": "Mainstream Support"},
    "Ubuntu 22.04 LTS": {"mainstream": "2027-04-01", "extended": "2032-04-01", "status": "Mainstream Support"},
    "Ubuntu 24.04 LTS": {"mainstream": "2029-04-01", "extended": "2034-04-01", "status": "Mainstream Support"},
    "CentOS 6": {"mainstream": "2017-05-10", "extended": "2020-11-30", "status": "EOL"},
    "CentOS 7": {"mainstream": "2020-08-06", "extended": "2024-06-30", "status": "EOL"},
    "CentOS 8": {"mainstream": "2021-12-31", "extended": "2021-12-31", "status": "EOL"},
    "Debian 8": {"mainstream": "2018-06-17", "extended": "2020-06-30", "status": "EOL"},
    "Debian 9": {"mainstream": "2020-07-06", "extended": "2022-06-30", "status": "EOL"},
    "Debian 10": {"mainstream": "2022-09-10", "extended": "2024-06-30", "status": "EOL"},
    "Debian 11": {"mainstream": "2024-08-14", "extended": "2026-06-30", "status": "Extended Support"},
    "Debian 12": {"mainstream": "2026-06-10", "extended": "2028-06-10", "status": "Mainstream Support"},
    "pfSense 2.7": {"mainstream": "2025-12-31", "extended": "2026-12-31", "status": "Mainstream Support"},
    "pfSense 2.6": {"mainstream": "2024-06-30", "extended": "2025-06-30", "status": "Extended Support"},
    "VMware ESXi 5.5": {"mainstream": "2018-09-19", "extended": "2020-09-19", "status": "EOL"},
    "VMware ESXi 6.0": {"mainstream": "2020-03-12", "extended": "2022-03-12", "status": "EOL"},
    "VMware ESXi 6.5": {"mainstream": "2020-11-15", "extended": "2022-10-15", "status": "EOL"},
    "VMware ESXi 6.7": {"mainstream": "2021-10-15", "extended": "2023-10-15", "status": "EOL"},
    "VMware ESXi 7.0": {"mainstream": "2025-04-02", "extended": "2027-04-02", "status": "Mainstream Support"},
    "VMware ESXi 8.0": {"mainstream": "2027-10-11", "extended": "2029-10-11", "status": "Mainstream Support"},
}

# INFRASTRUCTURE NORDTRANSIT LOGISTICS
KNOWN_HOSTS = {
    # Active Directory
    "192.168.1.10": {"hostname": "AD-01", "os": "Windows Server 2019", "role": "Contrôleur de domaine principal"},
    "192.168.1.11": {"hostname": "AD-02", "os": "Windows Server 2019", "role": "Contrôleur de domaine secondaire"},
    
    # Services applicatifs
    "192.168.1.13": {"hostname": "GRAFANA", "os": "Ubuntu 22.04 LTS", "role": "Supervision Grafana"},
    "192.168.1.14": {"hostname": "MYSQL-DB", "os": "Ubuntu 20.04 LTS", "role": "Base de données MySQL"},
    "192.168.1.15": {"hostname": "WEB-APP", "os": "Ubuntu 20.04 LTS", "role": "Serveur Web applicatif"},
    
    # Infrastructure réseau
    "192.168.1.1": {"hostname": "PFSENSE-FW", "os": "pfSense 2.7", "role": "Firewall principal (LAN)"},
    "10.10.10.67": {"hostname": "PFSENSE-FW", "os": "pfSense 2.7", "role": "Firewall principal (WAN)"},
}

class NetworkScanner:
    """Scanner réseau ultra-rapide"""
    
    def __init__(self, network_range: str):
        self.network_range = network_range
        self.hosts = []
    
    def ping_host(self, ip: str) -> bool:
        """Ping ultra-rapide"""
        try:
            is_windows = sys.platform.lower().startswith('win')
            cmd = ['ping', '-n' if is_windows else '-c', '1', 
                   '-w' if is_windows else '-W', '1', ip]
            
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL, timeout=1.5)
            return result.returncode == 0
        except:
            return False
    
    def get_hostname(self, ip: str) -> Optional[str]:
        """Résolution DNS rapide"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return None
    
    def check_ports_batch(self, ip: str) -> Dict[int, bool]:
        """Scan rapide de plusieurs ports"""
        ports = {
            445: "SMB/Windows",
            22: "SSH/Linux",
            3306: "MySQL",
            902: "VMware",
            3389: "RDP",
            80: "HTTP",
            443: "HTTPS",
            389: "LDAP",
            3000: "Grafana"
        }
        
        results = {}
        for port in ports.keys():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.2)
                result = sock.connect_ex((ip, port))
                sock.close()
                results[port] = (result == 0)
            except:
                results[port] = False
        
        return results
    
    def detect_os_advanced(self, ip: str, ports: Dict[int, bool]) -> str:
        """Détection OS avancée"""
        if ports[902]:
            return "VMware ESXi 8.0"
        elif ports[443] and ports[80] and not ports[22] and not ports[445]:
            return "pfSense 2.7"
        elif ports[445] and ports[389]:
            return "Windows Server 2019"
        elif ports[445]:
            return "Windows Server"
        elif ports[3000] and ports[22]:
            return "Ubuntu 22.04 LTS"
        elif ports[3306] and ports[22]:
            return "Ubuntu 20.04 LTS"
        elif ports[80] and ports[22]:
            return "Ubuntu 20.04 LTS"
        elif ports[22]:
            return "Ubuntu 22.04 LTS"
        else:
            return "Système inconnu"
    
    def scan_single_host(self, ip: str) -> Optional[Dict]:
        """Scan complet d'un hôte"""
        if not self.ping_host(ip):
            return None
        
        # Vérifier si c'est une machine connue
        if ip in KNOWN_HOSTS:
            known = KNOWN_HOSTS[ip]
            return {
                "ip": ip,
                "hostname": known["hostname"],
                "os": known["os"],
                "role": known["role"],
                "source": "inventory"
            }
        
        # Sinon, détecter
        hostname = self.get_hostname(ip)
        ports = self.check_ports_batch(ip)
        os_detected = self.detect_os_advanced(ip, ports)
        
        return {
            "ip": ip,
            "hostname": hostname or "N/A",
            "os": os_detected,
            "role": "Non documenté",
            "source": "detected"
        }
    
    def parse_network_range(self) -> List[str]:
        """Parse la plage réseau"""
        if '/' in self.network_range:
            base = '.'.join(self.network_range.split('/')[0].split('.')[:3])
        else:
            base = '.'.join(self.network_range.split('.')[:3])
        return [f"{base}.{i}" for i in range(1, 255)]
    
    def scan_network(self, max_workers: int = 100) -> List[Dict]:
        """Scan parallèle ultra-rapide"""
        print(f"\n[*] Scan du réseau {self.network_range}")
        print(f"[*] Utilisation de {max_workers} threads parallèles\n")
        
        ips_to_scan = self.parse_network_range()
        total_ips = len(ips_to_scan)
        scanned = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ip = {executor.submit(self.scan_single_host, ip): ip 
                           for ip in ips_to_scan}
            
            for future in as_completed(future_to_ip):
                scanned += 1
                if scanned % 20 == 0:
                    print(f"  Progression: {scanned}/{total_ips} IPs scannées...")
                
                host_info = future.result()
                if host_info:
                    self.hosts.append(host_info)
                    source_icon = "📋" if host_info.get('source') == 'inventory' else "🔍"
                    print(f"  {source_icon} [{host_info['ip']}] {host_info['hostname']} - {host_info['os']}")
        
        print(f"\n[✓] Scan terminé: {len(self.hosts)} hôte(s) actif(s)\n")
        return self.hosts

class EOLAnalyzer:
    """Analyseur EOL"""
    
    def __init__(self):
        self.eol_db = EOL_DATABASE
    
    def calculate_days_remaining(self, eol_date_str: str) -> int:
        """Calcule les jours restants avant EOL"""
        try:
            eol_date = datetime.strptime(eol_date_str, "%Y-%m-%d")
            today = datetime.now()
            return (eol_date - today).days
        except:
            return -9999
    
    def get_risk_level(self, days_remaining: int, status: str) -> str:
        """Détermine le niveau de risque"""
        if status == "EOL" or days_remaining < 0:
            return "CRITIQUE"
        elif days_remaining < 180:
            return "ÉLEVÉ"
        elif days_remaining < 365:
            return "MOYEN"
        elif days_remaining < 730:
            return "FAIBLE"
        else:
            return "OK"
    
    def analyze_host(self, host: Dict) -> Dict:
        """Analyse EOL complète d'un hôte"""
        os_version = host.get('os', 'Inconnu')
        
        # Recherche dans la base EOL
        eol_info = None
        matched_version = None
        
        for known_version, dates in self.eol_db.items():
            if known_version.lower() in os_version.lower():
                eol_info = dates
                matched_version = known_version
                break
        
        if not eol_info:
            return {
                **host,
                "matched_version": "Version inconnue",
                "eol_status": "UNKNOWN",
                "mainstream_eol": "N/A",
                "extended_eol": "N/A",
                "days_remaining": "N/A",
                "risk_level": "UNKNOWN",
                "recommendation": "Vérifier manuellement"
            }
        
        # Calculs réels
        days_remaining = self.calculate_days_remaining(eol_info['extended'])
        risk_level = self.get_risk_level(days_remaining, eol_info['status'])
        
        # Recommandation
        if risk_level == "CRITIQUE":
            recommendation = "MIGRATION URGENTE REQUISE"
        elif risk_level == "ÉLEVÉ":
            recommendation = f"Planifier migration sous 3 mois"
        elif risk_level == "MOYEN":
            recommendation = f"Prévoir migration"
        elif risk_level == "FAIBLE":
            recommendation = f"Surveiller"
        else:
            recommendation = f"Support actif - OK"
        
        return {
            **host,
            "matched_version": matched_version,
            "eol_status": eol_info['status'],
            "mainstream_eol": eol_info['mainstream'],
            "extended_eol": eol_info['extended'],
            "days_remaining": days_remaining,
            "risk_level": risk_level,
            "recommendation": recommendation
        }
    
    def print_cli_summary(self, analyzed_hosts: List[Dict]):
        """Affiche le résumé dans le CLI"""
        # Statistiques
        risk_counts = {"CRITIQUE": 0, "ÉLEVÉ": 0, "MOYEN": 0, "FAIBLE": 0, "OK": 0, "UNKNOWN": 0}
        for host in analyzed_hosts:
            risk = host.get('risk_level', 'UNKNOWN')
            risk_counts[risk] += 1
        
        print("\n" + "="*100)
        print("RAPPORT D'AUDIT D'OBSOLESCENCE - NORDTRANSIT LOGISTICS")
        print("="*100)
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Infrastructure scannée: {len(analyzed_hosts)} hôte(s)")
        print("="*100 + "\n")
        
        # Synthèse
        print("📊 SYNTHÈSE PAR NIVEAU DE RISQUE")
        print("-"*100)
        print(f"🔴 CRITIQUE : {risk_counts['CRITIQUE']} hôte(s) - EOL dépassée - ACTION IMMÉDIATE")
        print(f"🟠 ÉLEVÉ    : {risk_counts['ÉLEVÉ']} hôte(s) - < 6 mois - PLANIFICATION URGENTE")
        print(f"🟡 MOYEN    : {risk_counts['MOYEN']} hôte(s) - < 1 an - PLANIFICATION")
        print(f"🟢 FAIBLE   : {risk_counts['FAIBLE']} hôte(s) - < 2 ans - SURVEILLER")
        print(f"✅ OK       : {risk_counts['OK']} hôte(s) - Support actif")
        print(f"⚪ INCONNU  : {risk_counts['UNKNOWN']} hôte(s) - Version non identifiée")
        print("\n" + "="*100 + "\n")
        
        # Détails des machines par niveau de risque
        risk_order = ["CRITIQUE", "ÉLEVÉ", "MOYEN", "FAIBLE", "OK", "UNKNOWN"]
        icons = {"CRITIQUE": "🔴", "ÉLEVÉ": "🟠", "MOYEN": "🟡", "FAIBLE": "🟢", "OK": "✅", "UNKNOWN": "⚪"}
        
        for risk in risk_order:
            hosts_at_risk = [h for h in analyzed_hosts if h.get('risk_level') == risk]
            if not hosts_at_risk:
                continue
            
            print(f"{icons[risk]} NIVEAU {risk} ({len(hosts_at_risk)} hôte(s))")
            print("-"*100)
            
            for host in hosts_at_risk:
                print(f"\n  📍 {host['hostname']} ({host['ip']})")
                print(f"     OS:             {host.get('os', 'N/A')}")
                print(f"     Rôle:           {host.get('role', 'N/A')}")
                print(f"     Version EOL:    {host.get('matched_version', 'N/A')}")
                print(f"     Extended EOL:   {host.get('extended_eol', 'N/A')}")
                
                days = host.get('days_remaining', 'N/A')
                if days != 'N/A':
                    print(f"     Jours restants: {days}")
                
                print(f"     Recommandation: {host.get('recommendation', 'N/A')}")
            
            print("\n")
        
        print("="*100 + "\n")
    
    def export_csv(self, analyzed_hosts: List[Dict], output_file: Optional[str] = None):
        """Export CSV uniquement"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if not output_file:
            output_file = f"audit_eol_ntl_{timestamp}.csv"
        
        # Export CSV
        if analyzed_hosts:
            fieldnames = [
                "ip", "hostname", "os", "role", "source",
                "matched_version", "eol_status", 
                "mainstream_eol", "extended_eol", 
                "days_remaining", "risk_level", "recommendation"
            ]
            
            with open(output_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(analyzed_hosts)
        
        print(f"[✓] Export CSV sauvegardé: {output_file}\n")
        
        return 0 if sum(1 for h in analyzed_hosts if h.get('risk_level') == 'CRITIQUE') == 0 else 1

def main():
    """Menu principal"""
    print("\n" + "="*100)
    print("MODULE D'AUDIT D'OBSOLESCENCE - NTL-SysToolbox")
    print("Infrastructure NordTransit Logistics")
    print("="*100 + "\n")
    
    print("Options disponibles:")
    print("1. Scanner le réseau 192.168.1.0/24 et générer rapport EOL")
    print("2. Analyser uniquement les machines inventoriées")
    print("3. Lister toutes les versions OS avec dates EOL")
    
    choice = input("\nVotre choix (1-3): ").strip()
    
    analyzer = EOLAnalyzer()
    
    if choice == "1":
        network = input("\nPlage réseau [192.168.1.0/24]: ").strip() or "192.168.1.0/24"
        scanner = NetworkScanner(network)
        hosts = scanner.scan_network(max_workers=100)
        
        if hosts:
            analyzed = [analyzer.analyze_host(h) for h in hosts]
            analyzer.print_cli_summary(analyzed)
            return analyzer.export_csv(analyzed)
        else:
            print("[!] Aucun hôte détecté")
            return 1
    
    elif choice == "2":
        print("\n[*] Analyse des machines inventoriées...\n")
        hosts = []
        for ip, info in KNOWN_HOSTS.items():
            hosts.append({
                "ip": ip,
                "hostname": info["hostname"],
                "os": info["os"],
                "role": info["role"],
                "source": "inventory"
            })
        
        analyzed = [analyzer.analyze_host(h) for h in hosts]
        analyzer.print_cli_summary(analyzed)
        return analyzer.export_csv(analyzed, "audit_eol_inventory.csv")
    
    elif choice == "3":
        print("\n" + "="*100)
        print("BASE DE DONNÉES EOL - TOUTES LES VERSIONS")
        print("="*100 + "\n")
        
        for version, info in sorted(analyzer.eol_db.items()):
            days = analyzer.calculate_days_remaining(info['extended'])
            status_icon = "🔴" if info['status'] == "EOL" else "🟢"
            
            print(f"{status_icon} {version}")
            print(f"   Mainstream EOL: {info['mainstream']}")
            print(f"   Extended EOL:   {info['extended']} ({days} jours)")
            print(f"   Statut:         {info['status']}\n")
        
        print("="*100 + "\n")
        return 0
    
    else:
        print("[!] Choix invalide")
        return 1

if __name__ == "__main__":
    sys.exit(main())
