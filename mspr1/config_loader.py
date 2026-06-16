#!/usr/bin/env python3
"""
Configuration loader for NTL-SysToolbox
Supports YAML configuration files with environment variable overrides
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict


class Config:
    """Configuration manager with environment variable override support"""
    
    def __init__(self, config_file: str = "config.yaml"):
        """
        Load configuration from YAML file with environment variable overrides
        
        Args:
            config_file: Path to configuration file (default: config.yaml)
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_file}\n"
                f"Please copy config.example.yaml to config.yaml and update with your values."
            )
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if config is None:
            raise ValueError(f"Configuration file {self.config_file} is empty or invalid")
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with environment variable override support
        
        Environment variables are checked in format: NTL_SECTION_KEY
        Example: NTL_MYSQL_PASSWORD for mysql.password
        
        Args:
            key: Configuration key in dot notation (e.g., 'mysql.password')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Check environment variable first
        env_key = f"NTL_{key.upper().replace('.', '_')}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value
        
        # Navigate through nested dictionary
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def get_mysql_config(self) -> Dict[str, Any]:
        """Get MySQL configuration"""
        try:
            port = int(self.get('mysql.port', 3306))
        except (ValueError, TypeError):
            port = 3306
        
        return {
            'host': self.get('mysql.host', '192.168.1.14'),
            'user': self.get('mysql.user', 'root'),
            'password': self.get('mysql.password'),
            'port': port,
            'backup_dir': self.get('mysql.backup_dir', 'backups_mysql')
        }
    
    def get_agent_config(self) -> Dict[str, Any]:
        """Get agent configuration"""
        try:
            port = int(self.get('agent.port', 6000))
        except (ValueError, TypeError):
            port = 6000
        
        try:
            timeout = int(self.get('agent.timeout', 5))
        except (ValueError, TypeError):
            timeout = 5
        
        return {
            'port': port,
            'auth_token': self.get('agent.auth_token'),
            'timeout': timeout
        }
    
    def get_diagnostic_config(self) -> Dict[str, Any]:
        """Get diagnostic configuration"""
        return {
            'output_dir': self.get('diagnostic.output_dir', 'rapports_ntl'),
            'servers': self.get('diagnostic.servers', [])
        }


def load_config(config_file: str = "config.yaml") -> Config:
    """
    Convenience function to load configuration
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        Config object
    """
    return Config(config_file)
