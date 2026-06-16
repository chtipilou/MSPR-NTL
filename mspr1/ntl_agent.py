#!/usr/bin/env python3
"""
NTL System Agent - Daemon that exposes system metrics over TCP
Collects: CPU, RAM, Disk, Uptime, OS version
Cross-platform support for Windows and Linux
"""

import socket
import json
import psutil
import platform
import time
import threading
import sys
import os
import signal
from datetime import datetime, timedelta
from typing import Dict, Any


class SystemMetricsCollector:
    """Collect system metrics (CPU, RAM, Disk, Uptime, OS)"""
    
    @staticmethod
    def collect_metrics() -> Dict[str, Any]:
        """
        Collect all system metrics
        
        Returns:
            Dictionary with system metrics
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'hostname': platform.node(),
            'os': SystemMetricsCollector.get_os_info(),
            'cpu': SystemMetricsCollector.get_cpu_metrics(),
            'memory': SystemMetricsCollector.get_memory_metrics(),
            'disk': SystemMetricsCollector.get_disk_metrics(),
            'uptime': SystemMetricsCollector.get_uptime()
        }
        return metrics
    
    @staticmethod
    def get_os_info() -> Dict[str, str]:
        """Get OS information"""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'architecture': platform.machine(),
            'platform': platform.platform()
        }
    
    @staticmethod
    def get_cpu_metrics() -> Dict[str, Any]:
        """Get CPU metrics"""
        cpu_percent = psutil.cpu_percent(interval=1, percpu=False)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        
        try:
            cpu_freq = psutil.cpu_freq()
            freq_info = {
                'current': cpu_freq.current if cpu_freq else None,
                'min': cpu_freq.min if cpu_freq else None,
                'max': cpu_freq.max if cpu_freq else None
            }
        except (OSError, AttributeError, NotImplementedError):
            freq_info = {'current': None, 'min': None, 'max': None}
        
        return {
            'usage_percent': cpu_percent,
            'count_logical': cpu_count,
            'count_physical': cpu_count_physical,
            'frequency_mhz': freq_info
        }
    
    @staticmethod
    def get_memory_metrics() -> Dict[str, Any]:
        """Get memory metrics"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            'total_mb': round(mem.total / (1024 * 1024), 2),
            'available_mb': round(mem.available / (1024 * 1024), 2),
            'used_mb': round(mem.used / (1024 * 1024), 2),
            'percent': mem.percent,
            'swap_total_mb': round(swap.total / (1024 * 1024), 2),
            'swap_used_mb': round(swap.used / (1024 * 1024), 2),
            'swap_percent': swap.percent
        }
    
    @staticmethod
    def get_disk_metrics() -> Dict[str, Any]:
        """Get disk metrics for main partitions"""
        partitions = []
        
        for partition in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partitions.append({
                    'device': partition.device,
                    'mountpoint': partition.mountpoint,
                    'fstype': partition.fstype,
                    'total_gb': round(usage.total / (1024 ** 3), 2),
                    'used_gb': round(usage.used / (1024 ** 3), 2),
                    'free_gb': round(usage.free / (1024 ** 3), 2),
                    'percent': usage.percent
                })
            except (PermissionError, OSError):
                continue
        
        return {'partitions': partitions}
    
    @staticmethod
    def get_uptime() -> Dict[str, Any]:
        """Get system uptime"""
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime_delta = datetime.now() - boot_time
        
        return {
            'boot_time': boot_time.isoformat(),
            'uptime_seconds': int(uptime_delta.total_seconds()),
            'uptime_human': str(uptime_delta).split('.')[0]
        }


class NTLAgent:
    """NTL System Agent - TCP server exposing system metrics"""

    def __init__(self, port: int = 6000, auth_token: str = None, bind_address: str = '0.0.0.0'):
        """
        Initialize NTL Agent

        Args:
            port: TCP port to listen on (default: 6000)
            auth_token: Authentication token (optional but recommended)
            bind_address: Address to bind to (default: 0.0.0.0)
        """
        self.port = port
        self.auth_token = auth_token
        self.bind_address = bind_address
        self.running = False
        self.server_socket = None
        self.start_time = None
        self.connections_count = 0
        
    def verify_auth(self, request_data: Dict[str, Any]) -> bool:
        """
        Verify authentication token
        
        Args:
            request_data: Request data containing auth token
            
        Returns:
            True if authenticated, False otherwise
        """
        if not self.auth_token:
            return True
        
        token = request_data.get('auth_token', '')
        return token == self.auth_token
    
    def handle_client(self, client_socket: socket.socket, client_address: tuple):
        """
        Handle client connection

        Args:
            client_socket: Client socket
            client_address: Client address tuple
        """
        self.connections_count += 1
        try:
            data = client_socket.recv(4096).decode('utf-8')
            
            if not data:
                return
            
            try:
                request = json.loads(data)
            except json.JSONDecodeError:
                error_response = {
                    'status': 'error',
                    'message': 'Invalid JSON request'
                }
                client_socket.sendall(json.dumps(error_response).encode('utf-8'))
                return
            
            if not self.verify_auth(request):
                error_response = {
                    'status': 'error',
                    'message': 'Authentication failed'
                }
                client_socket.sendall(json.dumps(error_response).encode('utf-8'))
                return
            
            command = request.get('command', 'get_metrics')
            
            if command == 'get_metrics':
                metrics = SystemMetricsCollector.collect_metrics()
                response = {
                    'status': 'success',
                    'data': metrics
                }
            elif command == 'ping':
                response = {
                    'status': 'success',
                    'message': 'pong',
                    'timestamp': datetime.now().isoformat()
                }
            elif command == 'debug':
                response = self._build_debug_response()
            else:
                response = {
                    'status': 'error',
                    'message': f'Unknown command: {command}'
                }
            
            client_socket.sendall(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            error_response = {
                'status': 'error',
                'message': f'Server error: {str(e)}'
            }
            try:
                client_socket.sendall(json.dumps(error_response).encode('utf-8'))
            except:
                pass
        finally:
            client_socket.close()
    
    def _build_debug_response(self) -> Dict[str, Any]:
        """Build a debug/status response with full agent diagnostics"""
        now = datetime.now()
        agent_uptime = (now - self.start_time).total_seconds() if self.start_time else 0

        # Self-test: verify metrics collection works
        metrics_ok = False
        metrics_error = None
        metrics_sample = {}
        try:
            test_metrics = SystemMetricsCollector.collect_metrics()
            # Validate essential fields
            required = ['hostname', 'os', 'cpu', 'memory', 'disk', 'uptime']
            missing = [f for f in required if f not in test_metrics]
            if missing:
                metrics_error = f"Missing fields: {', '.join(missing)}"
            else:
                metrics_ok = True
                metrics_sample = {
                    'hostname': test_metrics['hostname'],
                    'cpu_percent': test_metrics['cpu'].get('usage_percent'),
                    'ram_percent': test_metrics['memory'].get('percent'),
                    'partitions_count': len(test_metrics['disk'].get('partitions', []))
                }
        except Exception as e:
            metrics_error = str(e)

        # Check socket is actually bound and listening
        socket_ok = False
        actual_bind = None
        try:
            if self.server_socket:
                actual_bind = self.server_socket.getsockname()
                socket_ok = True
        except Exception:
            pass

        return {
            'status': 'success',
            'debug': {
                'agent_version': '1.1.0',
                'bind_address': self.bind_address,
                'port': self.port,
                'actual_bind': f"{actual_bind[0]}:{actual_bind[1]}" if actual_bind else None,
                'socket_listening': socket_ok,
                'auth_enabled': self.auth_token is not None,
                'agent_uptime_seconds': round(agent_uptime, 1),
                'agent_start_time': self.start_time.isoformat() if self.start_time else None,
                'connections_handled': self.connections_count,
                'metrics_collection_ok': metrics_ok,
                'metrics_collection_error': metrics_error,
                'metrics_sample': metrics_sample,
                'timestamp': now.isoformat()
            }
        }

    def start(self):
        """Start the agent server"""
        self.running = True
        self.start_time = datetime.now()
        
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.bind_address, self.port))
            self.server_socket.listen(5)
            
            print(f"[*] NTL Agent started on {self.bind_address}:{self.port}")
            if self.auth_token:
                print(f"[*] Authentication enabled")
            else:
                print(f"[!] WARNING: Authentication disabled - not recommended for production")
            print(f"[*] Press Ctrl+C to stop")
            
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)
                    client_socket, client_address = self.server_socket.accept()
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"[!] Error accepting connection: {e}")
        
        except Exception as e:
            print(f"[!] Failed to start agent: {e}")
    
    def stop(self):
        """Stop the agent server"""
        print("\n[*] Stopping NTL Agent...")
        self.running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("[*] NTL Agent stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n[*] Shutdown signal received")
    sys.exit(0)


def run_self_diagnostic(agent: NTLAgent):
    """
    Run a full self-diagnostic: start the agent, connect to it,
    verify all commands work, then print results and stop.
    """
    print("=" * 60)
    print("  NTL AGENT - SELF DIAGNOSTIC / DEBUG")
    print("=" * 60)
    print()

    # 1. Test metrics collection without network
    print("[1/4] Test collecte des metriques systeme...")
    try:
        metrics = SystemMetricsCollector.collect_metrics()
        required = ['hostname', 'os', 'cpu', 'memory', 'disk', 'uptime']
        missing = [f for f in required if f not in metrics]
        if missing:
            print(f"  [FAIL] Champs manquants: {', '.join(missing)}")
        else:
            print(f"  [OK] Toutes les metriques collectees")
            print(f"       Hostname: {metrics['hostname']}")
            print(f"       OS: {metrics['os']['system']} {metrics['os']['release']}")
            print(f"       CPU: {metrics['cpu']['usage_percent']}% ({metrics['cpu']['count_logical']} cores)")
            print(f"       RAM: {metrics['memory']['percent']}% ({metrics['memory']['used_mb']:.0f}/{metrics['memory']['total_mb']:.0f} MB)")
            print(f"       Disques: {len(metrics['disk']['partitions'])} partition(s)")
            print(f"       Uptime: {metrics['uptime']['uptime_human']}")
    except Exception as e:
        print(f"  [FAIL] Erreur collecte: {e}")

    # 2. Start server in background thread
    print(f"\n[2/4] Demarrage agent sur {agent.bind_address}:{agent.port}...")
    server_thread = threading.Thread(target=agent.start, daemon=True)
    server_thread.start()
    time.sleep(1)

    if not agent.running or not agent.server_socket:
        print(f"  [FAIL] L'agent n'a pas reussi a demarrer")
        return

    try:
        sock_addr = agent.server_socket.getsockname()
        print(f"  [OK] Agent en ecoute sur {sock_addr[0]}:{sock_addr[1]}")
    except Exception:
        print(f"  [FAIL] Impossible de verifier le socket")

    # 3. Test TCP connection + commands
    print(f"\n[3/4] Test connexion TCP vers 127.0.0.1:{agent.port}...")
    errors = []

    # Test ping
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', agent.port))
        request = {'command': 'ping'}
        if agent.auth_token:
            request['auth_token'] = agent.auth_token
        sock.sendall(json.dumps(request).encode('utf-8'))
        resp = json.loads(sock.recv(4096).decode('utf-8'))
        sock.close()
        if resp.get('status') == 'success' and resp.get('message') == 'pong':
            print(f"  [OK] Commande 'ping' -> pong")
        else:
            errors.append(f"ping: reponse inattendue: {resp}")
            print(f"  [FAIL] Commande 'ping' -> {resp}")
    except Exception as e:
        errors.append(f"ping: {e}")
        print(f"  [FAIL] Commande 'ping' -> {e}")

    # Test get_metrics
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', agent.port))
        request = {'command': 'get_metrics'}
        if agent.auth_token:
            request['auth_token'] = agent.auth_token
        sock.sendall(json.dumps(request).encode('utf-8'))
        resp = json.loads(sock.recv(65536).decode('utf-8'))
        sock.close()
        if resp.get('status') == 'success' and resp.get('data'):
            data = resp['data']
            fields_ok = all(k in data for k in ['hostname', 'os', 'cpu', 'memory', 'disk', 'uptime'])
            if fields_ok:
                print(f"  [OK] Commande 'get_metrics' -> {len(data)} champs retournes")
            else:
                errors.append("get_metrics: champs manquants dans la reponse")
                print(f"  [FAIL] Commande 'get_metrics' -> champs manquants")
        else:
            errors.append(f"get_metrics: {resp}")
            print(f"  [FAIL] Commande 'get_metrics' -> {resp}")
    except Exception as e:
        errors.append(f"get_metrics: {e}")
        print(f"  [FAIL] Commande 'get_metrics' -> {e}")

    # Test debug command
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', agent.port))
        request = {'command': 'debug'}
        if agent.auth_token:
            request['auth_token'] = agent.auth_token
        sock.sendall(json.dumps(request).encode('utf-8'))
        resp = json.loads(sock.recv(65536).decode('utf-8'))
        sock.close()
        if resp.get('status') == 'success' and resp.get('debug'):
            dbg = resp['debug']
            print(f"  [OK] Commande 'debug' -> agent v{dbg.get('agent_version')}")
            print(f"       Port: {dbg.get('port')} | Bind: {dbg.get('actual_bind')}")
            print(f"       Socket OK: {dbg.get('socket_listening')}")
            print(f"       Auth: {'Oui' if dbg.get('auth_enabled') else 'Non'}")
            print(f"       Metriques OK: {dbg.get('metrics_collection_ok')}")
            print(f"       Connexions: {dbg.get('connections_handled')}")
        else:
            errors.append(f"debug: {resp}")
            print(f"  [FAIL] Commande 'debug' -> {resp}")
    except Exception as e:
        errors.append(f"debug: {e}")
        print(f"  [FAIL] Commande 'debug' -> {e}")

    # Test auth rejection (if auth enabled)
    if agent.auth_token:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('127.0.0.1', agent.port))
            request = {'command': 'ping', 'auth_token': 'mauvais_token'}
            sock.sendall(json.dumps(request).encode('utf-8'))
            resp = json.loads(sock.recv(4096).decode('utf-8'))
            sock.close()
            if resp.get('status') == 'error' and 'Authentication' in resp.get('message', ''):
                print(f"  [OK] Rejet token invalide -> authentification fonctionne")
            else:
                errors.append(f"auth rejection: aurait du rejeter, got {resp}")
                print(f"  [FAIL] Le token invalide n'a pas ete rejete")
        except Exception as e:
            errors.append(f"auth test: {e}")
            print(f"  [FAIL] Test authentification -> {e}")

    # 4. Summary
    print(f"\n[4/4] Resume du diagnostic")
    print("=" * 60)
    if not errors:
        print(f"  [OK] AGENT OPERATIONNEL sur le port {agent.port}")
        print(f"  Toutes les verifications ont reussi.")
        print(f"  L'agent expose correctement les metriques systeme.")
    else:
        print(f"  [!!] {len(errors)} PROBLEME(S) DETECTE(S):")
        for err in errors:
            print(f"    - {err}")
    print("=" * 60)

    agent.stop()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='NTL System Agent - Expose system metrics over TCP'
    )
    parser.add_argument(
        '--port', 
        type=int, 
        default=6000,
        help='TCP port to listen on (default: 6000)'
    )
    parser.add_argument(
        '--token',
        type=str,
        default=None,
        help='Authentication token (recommended)'
    )
    parser.add_argument(
        '--bind',
        type=str,
        default='0.0.0.0',
        help='Address to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run self-diagnostic at startup to verify agent works correctly'
    )

    args = parser.parse_args()
    
    # Support environment variable for token
    auth_token = args.token or os.environ.get('NTL_AGENT_TOKEN')
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start agent
    agent = NTLAgent(
        port=args.port,
        auth_token=auth_token,
        bind_address=args.bind
    )

    if args.debug:
        run_self_diagnostic(agent)
        return

    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
