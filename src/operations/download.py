"""
Download release operation module.
Handles downloading releases from build servers to other servers.
"""

import time
from typing import Dict, List, Any

from src.ssh.executor import run_command_on_server
from src.utils.logger import logger
from src.utils.exceptions import MaxRetriesExceededError


def download_release_operation(servers: List[Dict[str, Any]], ssh_base: List[str]) -> None:
    """
    Download a release from build servers to other servers.
    
    Args:
        servers (List[Dict[str, Any]]): List of all server configurations.
        ssh_base (List[str]): Base SSH command with options.
    """
    # Use all servers, but separate builds from the rest
    builds = [s for s in servers if s['type'] == 'build']
    others = [s for s in servers if s['type'] != 'build']
    
    if not builds:
        logger.error_highlight("No build servers found. Cannot download release.")
        return
    
    if not others:
        logger.error_highlight("No target servers found. Nothing to download to.")
        return
    
    # Start HTTP server on build servers
    for build_server in builds:
        logger.info(f"Starting HTTP server on build server {build_server['name']}")
        run_command_on_server(
            build_server, 
            "cd hb-os && nohup python3 -m http.server 8000 > /dev/null 2>&1 &", 
            ssh_base
        )
        time.sleep(1)
    
    try:
        # Download to each target server
        for target_server in others:
            logger.info(f"Downloading release to {target_server['name']}")
            download_cmd = f"cd hb-os && sudo ./run download_release --url http://{builds[0]['ip']}:8000/release.tar.gz"
            success, _ = run_command_on_server(target_server, download_cmd, ssh_base)
            
            if not success:
                error_msg = f"Failed to download release on server {target_server['name']}. Skipping."
                logger.error_highlight(error_msg)
    except Exception as e:
        logger.error(f"Error during download operation: {e}", exc_info=True)
        raise
    finally:
        # Always stop HTTP servers
        logger.info("Stopping HTTP servers on build servers")
        for build_server in builds:
            run_command_on_server(
                build_server, 
                "pkill -f 'python3 -m http.server 8000'", 
                ssh_base
            ) 