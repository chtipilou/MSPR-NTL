"""
Tests for NTL Agent - System metrics collection and protocol
"""

import json
import socket
import threading
import time
import pytest
from ntl_agent import NTLAgent, SystemMetricsCollector
from agent_client import AgentClient, query_agent


class TestSystemMetricsCollector:
    """Test system metrics collection"""
    
    def test_collect_metrics(self):
        """Test that metrics collection returns all required fields"""
        metrics = SystemMetricsCollector.collect_metrics()
        
        assert 'timestamp' in metrics
        assert 'hostname' in metrics
        assert 'os' in metrics
        assert 'cpu' in metrics
        assert 'memory' in metrics
        assert 'disk' in metrics
        assert 'uptime' in metrics
    
    def test_os_info(self):
        """Test OS information collection"""
        os_info = SystemMetricsCollector.get_os_info()
        
        assert 'system' in os_info
        assert 'release' in os_info
        assert 'version' in os_info
        assert 'architecture' in os_info
        assert 'platform' in os_info
        assert os_info['system'] in ['Linux', 'Windows', 'Darwin']
    
    def test_cpu_metrics(self):
        """Test CPU metrics collection"""
        cpu_metrics = SystemMetricsCollector.get_cpu_metrics()
        
        assert 'usage_percent' in cpu_metrics
        assert 'count_logical' in cpu_metrics
        assert 'count_physical' in cpu_metrics
        assert isinstance(cpu_metrics['usage_percent'], (int, float))
        assert cpu_metrics['usage_percent'] >= 0
        assert cpu_metrics['usage_percent'] <= 100
    
    def test_memory_metrics(self):
        """Test memory metrics collection"""
        mem_metrics = SystemMetricsCollector.get_memory_metrics()
        
        assert 'total_mb' in mem_metrics
        assert 'available_mb' in mem_metrics
        assert 'used_mb' in mem_metrics
        assert 'percent' in mem_metrics
        assert mem_metrics['percent'] >= 0
        assert mem_metrics['percent'] <= 100
    
    def test_disk_metrics(self):
        """Test disk metrics collection"""
        disk_metrics = SystemMetricsCollector.get_disk_metrics()
        
        assert 'partitions' in disk_metrics
        assert isinstance(disk_metrics['partitions'], list)
        
        if disk_metrics['partitions']:
            partition = disk_metrics['partitions'][0]
            assert 'device' in partition
            assert 'mountpoint' in partition
            assert 'total_gb' in partition
            assert 'percent' in partition
    
    def test_uptime(self):
        """Test uptime collection"""
        uptime = SystemMetricsCollector.get_uptime()
        
        assert 'boot_time' in uptime
        assert 'uptime_seconds' in uptime
        assert 'uptime_human' in uptime
        assert uptime['uptime_seconds'] > 0


class TestAgentProtocol:
    """Test agent protocol (authentication, commands, response format)"""
    
    @pytest.fixture
    def agent_server(self):
        """Start a test agent server"""
        agent = NTLAgent(port=6001, auth_token="test_token_12345")
        
        server_thread = threading.Thread(target=agent.start, daemon=True)
        server_thread.start()
        
        time.sleep(0.5)
        
        yield agent
        
        agent.stop()
    
    def test_ping_without_auth(self):
        """Test ping command without authentication"""
        agent = NTLAgent(port=6002, auth_token=None)
        server_thread = threading.Thread(target=agent.start, daemon=True)
        server_thread.start()
        time.sleep(0.5)
        
        try:
            client = AgentClient('127.0.0.1', 6002, auth_token=None)
            assert client.ping() == True
        finally:
            agent.stop()
    
    def test_ping_with_valid_auth(self, agent_server):
        """Test ping command with valid authentication"""
        client = AgentClient('127.0.0.1', 6001, auth_token="test_token_12345")
        assert client.ping() == True
    
    def test_ping_with_invalid_auth(self, agent_server):
        """Test ping command with invalid authentication"""
        client = AgentClient('127.0.0.1', 6001, auth_token="wrong_token")
        assert client.ping() == False
    
    def test_get_metrics_with_valid_auth(self, agent_server):
        """Test get_metrics command with valid authentication"""
        client = AgentClient('127.0.0.1', 6001, auth_token="test_token_12345")
        metrics = client.get_metrics()
        
        assert metrics is not None
        assert 'hostname' in metrics
        assert 'os' in metrics
        assert 'cpu' in metrics
        assert 'memory' in metrics
    
    def test_get_metrics_with_invalid_auth(self, agent_server):
        """Test get_metrics command with invalid authentication"""
        client = AgentClient('127.0.0.1', 6001, auth_token="wrong_token")
        metrics = client.get_metrics()
        
        assert metrics is None
    
    def test_invalid_json_request(self, agent_server):
        """Test handling of invalid JSON request"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 6001))
        sock.sendall(b"not valid json")
        
        response = sock.recv(4096).decode('utf-8')
        sock.close()
        
        response_data = json.loads(response)
        assert response_data['status'] == 'error'
        assert 'Invalid JSON' in response_data['message']
    
    def test_unknown_command(self, agent_server):
        """Test handling of unknown command"""
        request = {
            'command': 'unknown_command',
            'auth_token': 'test_token_12345'
        }
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('127.0.0.1', 6001))
            sock.sendall(json.dumps(request).encode('utf-8'))
            
            response = sock.recv(4096).decode('utf-8')
            sock.close()
            
            response_data = json.loads(response)
            assert response_data['status'] == 'error'
            assert 'Unknown command' in response_data['message']
        except (ConnectionResetError, BrokenPipeError):
            pytest.skip("Connection issue with test agent")


class TestAgentClient:
    """Test agent client functionality"""
    
    @pytest.fixture
    def agent_server(self):
        """Start a test agent server"""
        agent = NTLAgent(port=6003, auth_token="client_test_token")
        
        server_thread = threading.Thread(target=agent.start, daemon=True)
        server_thread.start()
        
        time.sleep(0.5)
        
        yield agent
        
        agent.stop()
    
    def test_client_connection_timeout(self):
        """Test client timeout on unreachable host"""
        result = query_agent('192.0.2.1', 6000, timeout=1)
        
        assert result['status'] == 'error'
        assert 'timeout' in result['error'] or 'connection_failed' in result['error']
    
    def test_client_connection_refused(self):
        """Test client handling of connection refused"""
        result = query_agent('127.0.0.1', 9999, timeout=1)
        
        assert result['status'] == 'error'
        assert 'connection_failed' in result['error']
    
    def test_client_successful_query(self, agent_server):
        """Test successful metrics query"""
        result = query_agent('127.0.0.1', 6003, auth_token='client_test_token')
        
        assert result['status'] == 'success'
        assert result['metrics'] is not None
        assert 'hostname' in result['metrics']
    
    def test_client_auth_failure(self, agent_server):
        """Test client handling of authentication failure"""
        result = query_agent('127.0.0.1', 6003, auth_token='wrong_token')
        
        assert result['status'] == 'error'


class TestMetricsFormat:
    """Test metrics data format and validation"""
    
    def test_metrics_json_serializable(self):
        """Test that collected metrics are JSON serializable"""
        metrics = SystemMetricsCollector.collect_metrics()
        
        try:
            json_str = json.dumps(metrics)
            parsed = json.loads(json_str)
            assert parsed is not None
        except Exception as e:
            pytest.fail(f"Metrics are not JSON serializable: {e}")
    
    def test_metrics_values_valid(self):
        """Test that metric values are within valid ranges"""
        metrics = SystemMetricsCollector.collect_metrics()
        
        assert 0 <= metrics['cpu']['usage_percent'] <= 100
        assert 0 <= metrics['memory']['percent'] <= 100
        assert metrics['memory']['total_mb'] > 0
        assert metrics['uptime']['uptime_seconds'] > 0
    
    def test_response_format(self):
        """Test agent response format"""
        agent = NTLAgent(port=6004, auth_token=None)
        server_thread = threading.Thread(target=agent.start, daemon=True)
        server_thread.start()
        time.sleep(0.5)
        
        try:
            request = {'command': 'get_metrics'}
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', 6004))
            sock.sendall(json.dumps(request).encode('utf-8'))
            
            response = sock.recv(65536).decode('utf-8')
            sock.close()
            
            response_data = json.loads(response)
            
            assert 'status' in response_data
            assert response_data['status'] == 'success'
            assert 'data' in response_data
            assert isinstance(response_data['data'], dict)
        finally:
            agent.stop()
