"""
Tests for configuration loader
"""

import os
import pytest
import tempfile
from pathlib import Path
from config_loader import Config, load_config


class TestConfigLoader:
    """Test configuration loading and environment variable overrides"""
    
    @pytest.fixture
    def config_file(self):
        """Create a temporary config file for testing"""
        config_content = """
mysql:
  host: "192.168.1.14"
  user: "root"
  password: "test_password"
  port: 3306
  backup_dir: "backups_mysql"

agent:
  port: 6000
  auth_token: "test_token"
  timeout: 5

diagnostic:
  output_dir: "rapports_ntl"
  servers:
    - name: "Test Server"
      ip: "192.168.1.10"
      ports:
        ssh_22: 22
      agent_enabled: true
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name
        
        yield temp_path
        
        os.unlink(temp_path)
    
    def test_load_config_success(self, config_file):
        """Test successful config loading"""
        config = Config(config_file)
        
        assert config.get('mysql.host') == '192.168.1.14'
        assert config.get('mysql.user') == 'root'
        assert config.get('mysql.password') == 'test_password'
    
    def test_load_config_missing_file(self):
        """Test handling of missing config file"""
        with pytest.raises(FileNotFoundError):
            Config('nonexistent_config.yaml')
    
    def test_get_with_default(self, config_file):
        """Test getting value with default"""
        config = Config(config_file)
        
        assert config.get('nonexistent.key', 'default_value') == 'default_value'
    
    def test_env_override(self, config_file):
        """Test environment variable override"""
        os.environ['NTL_MYSQL_PASSWORD'] = 'env_password'
        
        try:
            config = Config(config_file)
            assert config.get('mysql.password') == 'env_password'
        finally:
            del os.environ['NTL_MYSQL_PASSWORD']
    
    def test_get_mysql_config(self, config_file):
        """Test getting MySQL configuration"""
        config = Config(config_file)
        mysql_config = config.get_mysql_config()
        
        assert mysql_config['host'] == '192.168.1.14'
        assert mysql_config['user'] == 'root'
        assert mysql_config['password'] == 'test_password'
        assert mysql_config['port'] == 3306
    
    def test_get_agent_config(self, config_file):
        """Test getting agent configuration"""
        config = Config(config_file)
        agent_config = config.get_agent_config()
        
        assert agent_config['port'] == 6000
        assert agent_config['auth_token'] == 'test_token'
        assert agent_config['timeout'] == 5
    
    def test_get_diagnostic_config(self, config_file):
        """Test getting diagnostic configuration"""
        config = Config(config_file)
        diag_config = config.get_diagnostic_config()
        
        assert diag_config['output_dir'] == 'rapports_ntl'
        assert isinstance(diag_config['servers'], list)
        assert len(diag_config['servers']) > 0
    
    def test_nested_config_navigation(self, config_file):
        """Test navigation through nested configuration"""
        config = Config(config_file)
        
        assert config.get('agent.port') == 6000
        assert config.get('diagnostic.servers') is not None
