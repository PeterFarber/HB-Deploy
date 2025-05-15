"""
Update config operation module.
Handles updating configuration on servers.
"""

import os
from typing import Dict, List, Any

from src.ssh.executor import run_command_on_server, run_command_on_servers
from src.ui.menu import select_servers
from src.utils.logger import logger
from src.utils.exceptions import ConfigurationError


def update_config_operation(servers: List[Dict[str, Any]], ssh_base: List[str]) -> None:
    """
    Update configuration on selected servers.
    
    Args:
        servers (List[Dict[str, Any]]): List of all server configurations.
        ssh_base (List[str]): Base SSH command with options.
    """
    # Select all servers by default
    sel = select_servers(servers, all_servers=True)
    if not sel:
        logger.warning("No servers selected for config update, exiting operation")
        return
    
    logger.info_highlight(f"Updating configuration on selected servers")
    
    try:
        updated_count = 0
        skipped_count = 0
        
        for server in sel:
            # Skip build servers
            if server['type'] == 'build':
                logger.debug(f"Skipping build server {server['name']}")
                skipped_count += 1
                continue
                
            logger.info(f"Updating config on {server['name']} ({server['type']})")
            
            # Check if the config file exists for this server type
            config_file_path = f"./config/types/{server['type']}.jsonc"
            if not os.path.exists(config_file_path):
                logger.warning_highlight(f"Config file not found: {config_file_path}")
                logger.warning(f"Skipping config update for {server['name']}")
                skipped_count += 1
                continue
            
            try:
                # Create backups directory on the server if it doesn't exist
                logger.debug(f"Creating backups directory on {server['name']}")
                backup_dir_cmd = "mkdir -p /home/hb/hb-os/config/backups"
                success, _ = run_command_on_server(server, backup_dir_cmd, ssh_base)
                
                if not success:
                    logger.warning(f"Could not create backups directory on {server['name']}, proceeding anyway")
                
                # Backup existing config with timestamp
                logger.debug(f"Backing up existing configuration on {server['name']}")
                timestamp_cmd = "date +%s"  # Get Unix timestamp
                success, timestamp_output = run_command_on_server(server, timestamp_cmd, ssh_base, print_output=False)
                timestamp = timestamp_output.strip() if success else "unknown"
                
                backup_file = f"/home/hb/hb-os/config/backups/server-{timestamp}.jsonc"
                backup_cmd = f"cp /home/hb/hb-os/config/server.jsonc {backup_file} 2>/dev/null || true"
                success, _ = run_command_on_server(server, backup_cmd, ssh_base)
                
                if success:
                    logger.info(f"Created backup: {backup_file}")
                else:
                    logger.warning(f"Could not backup config on {server['name']}, proceeding anyway")
                
                # Read the configuration file
                with open(config_file_path, "r") as f:
                    content = f.read()
                
                # Escape single quotes in the content to prevent shell interpretation issues
                escaped_content = content.replace("'", "'\\''")
                
                # Write the content to the server
                update_cmd = f"echo '{escaped_content}' > /home/hb/hb-os/config/server.jsonc"
                success, output = run_command_on_server(server, update_cmd, ssh_base)
                
                if not success:
                    error_msg = f"Failed to update configuration on {server['name']}"
                    logger.error_highlight(error_msg)
                    raise ConfigurationError(f"Failed to update config on {server['name']}")
                
                logger.info_success(f"Successfully updated configuration on {server['name']}")
                updated_count += 1
                
            except Exception as e:
                logger.error_highlight(f"Error updating config on {server['name']}: {e}")
                logger.error(f"Error details:", exc_info=True)
                skipped_count += 1
    
    except Exception as e:
        logger.error_highlight(f"Error during configuration update: {e}")
        logger.error(f"Error details:", exc_info=True)
    
    logger.info_highlight(f"Configuration update completed: {updated_count} updated, {skipped_count} skipped") 