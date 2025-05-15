"""
Configuration settings module.
Handles loading and accessing application configuration from different sources.
"""

import os
import sys
import yaml
import toml
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Remove the direct import of logger
# from src.utils.logger import logger, setup_logging

# Default configuration values
DEFAULT_CONFIG = {
    # Server settings
    "server": {
        "config_file": "./config/servers.json",
        "user": "hb",
    },
    
    # SSH settings
    "ssh": {
        "batch_mode": True,
        "identity_file": None,
        "agent_sock_path": "~/.ssh/agent_info",
    },
    
    # HTTP settings
    "http": {
        "server_port": 8000,
        "timeout": 2,
    },
    
    # Release settings
    "release": {
        "data_disk": "../cache.img",
        "router_endpoint": "/~meta@1.0/info/address",
        "router_port": 80,
        "router_retries": 30,
        "router_retry_delay": 1,
    },
    
    # Paths
    "paths": {
        "ssh_dir": "~/.ssh",
        "hb_os_dir": "hb-os",
        "config_types_dir": "./config/types",
        "server_config": "config/server.jsonc",
        "content_dockerfile": "resources/content.Dockerfile",
    },
    
    # Execution settings
    "execution": {
        "parallel": True,
        "max_workers": 5,
        "timeout": 300,
        "retry_count": 3,
        "retry_delay": 5,
    },
    
    # Logging settings
    "logging": {
        "level": "INFO",
        "file": None,
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "backup_count": 5,
    },
}


class ConfigurationError(Exception):
    """Exception raised for configuration errors."""
    pass


class Settings:
    """
    Settings class for managing application configuration.
    Loads configuration from multiple sources with priority:
    1. Command line arguments
    2. Environment variables
    3. Configuration files (YAML, TOML, JSON)
    4. Default values
    """
    
    def __init__(self):
        """Initialize the settings with default values."""
        self._config = DEFAULT_CONFIG.copy()
        self._load_config_files()
        self._load_env_vars()
    
    def _load_config_files(self):
        """Load configuration from files if they exist."""
        # Order matters: later files override earlier ones
        config_files = [
            ("config.json", self._load_json),
            ("config.yaml", self._load_yaml),
            ("config.yml", self._load_yaml),
            ("config.toml", self._load_toml),
        ]
        
        for filename, loader in config_files:
            if os.path.exists(filename):
                try:
                    config_data = loader(filename)
                    self._merge_configs(self._config, config_data)
                except Exception as e:
                    # Always use print during initialization to avoid circular imports
                    print(f"Warning: Failed to load {filename}: {e}", file=sys.stderr)
    
    def _load_json(self, filename: str) -> Dict[str, Any]:
        """Load JSON configuration file."""
        with open(filename, "r") as f:
            return json.load(f)
    
    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file."""
        with open(filename, "r") as f:
            return yaml.safe_load(f)
    
    def _load_toml(self, filename: str) -> Dict[str, Any]:
        """Load TOML configuration file."""
        with open(filename, "r") as f:
            return toml.load(f)
    
    def _load_env_vars(self):
        """Load configuration from environment variables."""
        # Load from .env file if it exists
        load_dotenv()
        
        # Process environment variables that start with HB_
        for key, value in os.environ.items():
            if key.startswith("HB_"):
                # Convert HB_SERVER_CONFIG_FILE to ['server']['config_file']
                parts = key[3:].lower().split("_")
                
                # Navigate to the right place in the config dict
                current = self._config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set the value, converting to the appropriate type if possible
                try:
                    # Try to determine the type from the existing value if it exists
                    last_part = parts[-1]
                    if last_part in current:
                        existing_value = current[last_part]
                        if isinstance(existing_value, bool):
                            current[last_part] = value.lower() in ("true", "yes", "1", "on")
                        elif isinstance(existing_value, int):
                            current[last_part] = int(value)
                        elif isinstance(existing_value, float):
                            current[last_part] = float(value)
                        else:
                            current[last_part] = value
                    else:
                        # If there's no existing value, just use the string
                        current[last_part] = value
                except (ValueError, TypeError):
                    # If conversion fails, use the string value
                    current[parts[-1]] = value
    
    def _merge_configs(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        Recursively merge source config into target config.
        
        Args:
            target: The target configuration dictionary
            source: The source configuration dictionary
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                # If both are dicts, merge them recursively
                self._merge_configs(target[key], value)
            else:
                # Otherwise, replace the value
                target[key] = value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            section: The configuration section
            key: The configuration key
            default: The default value if the key doesn't exist
            
        Returns:
            The configuration value
        """
        try:
            return self._config[section][key]
        except KeyError:
            return default
    
    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            section: The configuration section
            key: The configuration key
            value: The value to set
        """
        if section not in self._config:
            self._config[section] = {}
        self._config[section][key] = value
    
    def update_from_args(self, args: Dict[str, Any]) -> None:
        """
        Update configuration from command line arguments.
        
        Args:
            args: The parsed command line arguments
        """
        for key, value in args.items():
            if value is not None:  # Only update if the argument was provided
                # Convert argument names to config sections and keys
                # e.g., server_config_file -> server.config_file
                if "_" in key:
                    section, rest = key.split("_", 1)
                    if section in self._config:
                        # If there are still underscores, process further
                        if "_" in rest:
                            subkey, value_key = rest.split("_", 1)
                            if subkey in self._config[section]:
                                self._config[section][subkey][value_key] = value
                        else:
                            self._config[section][rest] = value
                else:
                    # Handle top-level keys
                    self._config[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration.
        
        Returns:
            The complete configuration dictionary
        """
        return self._config


# Create a singleton instance
settings = Settings() 