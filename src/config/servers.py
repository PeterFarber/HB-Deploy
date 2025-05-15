"""
Server configuration module.
Handles loading and accessing server configurations.
"""

import json
import sys
from typing import Dict, List, Optional, Any

from src.utils.logger import logger

# Default configuration file path
CONFIG_FILE = "./config/servers.json"


def load_servers(config_file: str = CONFIG_FILE) -> List[Dict[str, Any]]:
    """
    Load server configurations from the specified JSON file.
    
    Args:
        config_file (str): Path to the server configuration file.
        
    Returns:
        List[Dict]: List of server configuration dictionaries.
    
    Raises:
        SystemExit: If the configuration file cannot be loaded.
    """
    try:
        with open(config_file) as f:
            servers = json.load(f)
            logger.debug(f"Loaded {len(servers)} servers from {config_file}")
            return servers
    except Exception as e:
        logger.error_highlight(f"Failed to load server configuration from {config_file}: {e}")
        sys.exit(1)


def get_servers_by_type(servers: List[Dict[str, Any]], server_type: str) -> List[Dict[str, Any]]:
    """
    Filter servers by their type.
    
    Args:
        servers (List[Dict]): List of server configurations.
        server_type (str): The server type to filter by.
        
    Returns:
        List[Dict]: Filtered list of server configurations.
    """
    filtered = [s for s in servers if s.get("type") == server_type]
    logger.debug(f"Filtered {len(filtered)} servers of type '{server_type}'")
    return filtered


def get_servers_by_ids(servers: List[Dict[str, Any]], ids: List[str]) -> List[Dict[str, Any]]:
    """
    Filter servers by their IDs.
    
    Args:
        servers (List[Dict]): List of server configurations.
        ids (List[str]): List of server IDs to filter by.
        
    Returns:
        List[Dict]: Filtered list of server configurations.
    """
    filtered = [s for s in servers if s.get("id") in ids]
    logger.debug(f"Filtered {len(filtered)} servers by IDs: {', '.join(ids)}")
    return filtered


def get_server_by_id(servers: List[Dict[str, Any]], server_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a server by its ID.
    
    Args:
        servers (List[Dict]): List of server configurations.
        server_id (str): The server ID to search for.
        
    Returns:
        Optional[Dict]: The server configuration, or None if not found.
    """
    for server in servers:
        if server.get("id") == server_id:
            logger.debug(f"Found server with ID '{server_id}'")
            return server
    
    logger.debug(f"No server found with ID '{server_id}'")
    return None 