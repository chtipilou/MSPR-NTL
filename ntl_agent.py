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
        except:
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
    
    def start(self):
        """Start the agent server"""
        self.running = True
        
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
    
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
