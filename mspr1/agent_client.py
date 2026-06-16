#!/usr/bin/env python3
"""
NTL Agent Client - Client to query NTL system agents
"""

import socket
import json
from typing import Dict, Any, Optional


class AgentClient:
    """Client to communicate with NTL system agents"""
    
    def __init__(self, host: str, port: int = 6000, auth_token: str = None, timeout: int = 5):
        """
        Initialize agent client
        
        Args:
            host: Agent host address
            port: Agent port (default: 6000)
            auth_token: Authentication token
            timeout: Connection timeout in seconds (default: 5)
        """
        self.host = host
        self.port = port
        self.auth_token = auth_token
        self.timeout = timeout
    
    def _send_request(self, command: str, additional_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Send request to agent
        
        Args:
            command: Command to execute
            additional_data: Additional data to include in request
            
        Returns:
            Response dictionary
            
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If request times out
            ValueError: If response is invalid
        """
        request = {
            'command': command
        }
        
        if self.auth_token:
            request['auth_token'] = self.auth_token
        
        if additional_data:
            request.update(additional_data)
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            
            request_json = json.dumps(request)
            sock.sendall(request_json.encode('utf-8'))
            
            response_data = sock.recv(65536).decode('utf-8')
            sock.close()
            
            if not response_data:
                raise ValueError("Empty response from agent")
            
            response = json.loads(response_data)
            return response
            
        except socket.timeout:
            raise TimeoutError(f"Connection to agent {self.host}:{self.port} timed out")
        except socket.error as e:
            raise ConnectionError(f"Failed to connect to agent {self.host}:{self.port}: {e}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from agent: {e}")
    
    def get_metrics(self) -> Optional[Dict[str, Any]]:
        """
        Get system metrics from agent
        
        Returns:
            Metrics dictionary or None if failed
        """
        try:
            response = self._send_request('get_metrics')
            
            if response.get('status') == 'success':
                return response.get('data')
            else:
                error_msg = response.get('message', 'Unknown error')
                raise ValueError(f"Agent returned error: {error_msg}")
                
        except Exception:
            return None
    
    def ping(self) -> bool:
        """
        Ping agent to check if it's alive
        
        Returns:
            True if agent responds, False otherwise
        """
        try:
            response = self._send_request('ping')
            return response.get('status') == 'success'
        except Exception:
            return False
    
    def debug(self) -> Optional[Dict[str, Any]]:
        """
        Get debug/status info from agent

        Returns:
            Debug info dictionary or None if failed
        """
        try:
            response = self._send_request('debug')
            if response.get('status') == 'success':
                return response.get('debug')
            return None
        except Exception:
            return None

    def get_metrics_safe(self) -> Dict[str, Any]:
        """
        Get system metrics from agent with error handling
        
        Returns:
            Metrics dictionary or error dictionary
        """
        try:
            metrics = self.get_metrics()
            if metrics:
                return {
                    'status': 'success',
                    'metrics': metrics
                }
            else:
                return {
                    'status': 'error',
                    'error': 'Failed to retrieve metrics',
                    'metrics': None
                }
        except TimeoutError as e:
            return {
                'status': 'error',
                'error': f'timeout: {str(e)}',
                'metrics': None
            }
        except ConnectionError as e:
            return {
                'status': 'error',
                'error': f'connection_failed: {str(e)}',
                'metrics': None
            }
        except (ValueError, OSError) as e:
            return {
                'status': 'error',
                'error': f'connection_failed: {str(e)}',
                'metrics': None
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'connection_failed: {str(e)}',
                'metrics': None
            }


def query_agent(host: str, port: int = 6000, auth_token: str = None, timeout: int = 5) -> Dict[str, Any]:
    """
    Convenience function to query an agent
    
    Args:
        host: Agent host address
        port: Agent port (default: 6000)
        auth_token: Authentication token
        timeout: Connection timeout in seconds
        
    Returns:
        Dictionary with status and metrics/error
    """
    client = AgentClient(host, port, auth_token, timeout)
    return client.get_metrics_safe()
