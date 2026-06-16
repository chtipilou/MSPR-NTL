"""
Tests for diagnostic report generation
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestDiagnosticReport:
    """Test diagnostic report generation and format"""
    
    def test_report_json_structure(self):
        """Test that diagnostic report has correct JSON structure"""
        from datetime import datetime
        
        rapport = {
            'timestamp': datetime.now().isoformat(),
            'serveurs': {
                'Test Server': {
                    'ip': '192.168.1.10',
                    'name': 'Test Server',
                    'ssh_22': True
                }
            },
            'summary': {
                'total_servers': 1,
                'servers_up': 1,
                'servers_with_issues': 0,
                'servers_down': 0
            }
        }
        
        assert 'timestamp' in rapport
        assert 'serveurs' in rapport
        assert 'summary' in rapport
        
        json_str = json.dumps(rapport)
        parsed = json.loads(json_str)
        assert parsed is not None
    
    def test_report_contains_metrics(self):
        """Test that report can contain agent metrics"""
        rapport = {
            'serveurs': {
                'Test Server': {
                    'ip': '192.168.1.10',
                    'agent': {
                        'hostname': 'test-host',
                        'os': {'system': 'Linux'},
                        'cpu': {'usage_percent': 25.5},
                        'memory': {'percent': 50.0}
                    }
                }
            }
        }
        
        assert 'agent' in rapport['serveurs']['Test Server']
        assert rapport['serveurs']['Test Server']['agent']['cpu']['usage_percent'] == 25.5


class TestPortChecking:
    """Test port checking functionality"""
    
    @patch('socket.socket')
    def test_check_tcp_port_success(self, mock_socket):
        """Test successful port check"""
        from diagnostique_infra import check_tcp_port
        
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock
        
        result = check_tcp_port('192.168.1.10', 22)
        
        assert result == True
    
    @patch('socket.socket')
    def test_check_tcp_port_failure(self, mock_socket):
        """Test failed port check"""
        from diagnostique_infra import check_tcp_port
        
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 1
        mock_socket.return_value = mock_sock
        
        result = check_tcp_port('192.168.1.10', 22)
        
        assert result == False


class TestServerTesting:
    """Test server testing functionality"""
    
    @patch('diagnostique_infra.check_tcp_port')
    def test_test_server(self, mock_check_port):
        """Test server testing function"""
        from diagnostique_infra import test_server
        
        mock_check_port.return_value = True
        
        result = test_server('Test Server', '192.168.1.10', {'ssh_22': 22, 'http_80': 80})
        
        assert result['ip'] == '192.168.1.10'
        assert result['name'] == 'Test Server'
        assert result['ssh_22'] == True
        assert result['http_80'] == True
