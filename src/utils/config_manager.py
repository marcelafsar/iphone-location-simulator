"""
Configuration Manager - Marcel Location Simulator
Handles loading, saving, and managing configuration parameters from config.yaml.
Created by Marcel Afsar
"""

import yaml
from pathlib import Path
from typing import Any
from loguru import logger


class ConfigManager:
    """Manages application configuration profiles using YAML format"""
    
    _instance = None
    
    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Args:
            config_path: Path to the YAML configuration file
        """
        if not hasattr(self, '_initialized'):
            self.config_path = Path(config_path)
            self.config = self._load_config()
            self._initialized = True
    
    def _load_config(self) -> dict:
        """
        Load config options from disk
        
        Returns:
            dict: Configuration keys and values
        """
        if not self.config_path.exists():
            logger.warning(f"Configuration file not found: {self.config_path}")
            return self._get_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded config profile from: {self.config_path}")
                return config
        except Exception as e:
            logger.error(f"Error loading configuration file: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> dict:
        """
        Get absolute default fallback configurations
        
        Returns:
            dict: Default fallback settings
        """
        return {
            'app': {
                'name': 'Marcel Location Simulator',
                'version': '1.0.0',
                'author': 'Marcel Afsar',
                'language': 'en',
                'theme': 'dark'
            },
            'location': {
                'default_speed': 5.0,
                'update_interval': 1.0,
                'min_speed': 1.0,
                'max_speed': 100.0
            },
            'map': {
                'default_zoom': 15,
                'default_center': {
                    'latitude': 40.7128,
                    'longitude': -74.0060  # New York City
                },
                'tile_layer': 'CartoDB'
            },
            'database': {
                'path': 'data/favorites.db',
                'backup_enabled': True,
                'backup_interval': 7
            },
            'logging': {
                'level': 'INFO',
                'file_path': 'data/logs/app.log',
                'max_size': 10485760,
                'backup_count': 5
            },
            'ui': {
                'window_width': 1200,
                'window_height': 850,
                'remember_position': True,
                'show_tooltips': True
            },
            'features': {
                'auto_reconnect': True,
                'save_last_location': True,
                'show_notifications': True
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration parameter using dot notation
        
        Args:
            key: Config parameter (e.g. 'app.name', 'location.default_speed')
            default: Fallback value if key is not found
            
        Returns:
            Any: Value of the parameter
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set or modify a configuration parameter in memory
        
        Args:
            key: Config parameter key (e.g. 'app.language')
            value: New value
            
        Returns:
            bool: True if set successfully
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
        logger.info(f"Config updated: {key} = {value}")
        return True
    
    def save(self) -> bool:
        """
        Save configuration state to disk
        
        Returns:
            bool: True if written successfully
        """
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(
                    self.config, 
                    f, 
                    default_flow_style=False,
                    allow_unicode=True
                )
            logger.info(f"Config profile saved to: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config profile: {e}")
            return False
    
    def reload(self):
        """Reload configuration profile from disk"""
        self.config = self._load_config()
        logger.info("Config profile reloaded")