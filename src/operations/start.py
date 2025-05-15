"""
Start release operation module.
Handles starting releases on router and compute servers.
"""

import time
from typing import Dict, List, Any

from src.ssh.executor import run_command_on_server
from src.utils.helpers import wait_for_router
from src.utils.logger import logger
from src.utils.exceptions import RouterError, TimeoutError


def start_release_operation(servers: List[Dict[str, Any]], ssh_base: List[str]) -> None:
    """
    Start a release on router and compute servers.
    
    Args:
        servers (List[Dict[str, Any]]): List of all server configurations.
        ssh_base (List[str]): Base SSH command with options.
    """
    # Group servers by type
    builds = [s for s in servers if s['type'] == 'build']
    routers = [s for s in servers if s['type'] == 'router']
    computes = [s for s in servers if s['type'] == 'compute']
    
    if not routers:
        logger.error_highlight("No router servers found. Cannot start release.")
        return
    
    logger.info_highlight(f"Starting release operation with {len(routers)} routers and {len(computes)} compute nodes")
    
    # Start HTTP server on build servers if there are any
    for build_server in builds:
        logger.info(f"Starting HTTP server on build server {build_server['name']}")
        run_command_on_server(
            build_server, 
            "cd hb-os && nohup python3 -m http.server 8000 > /dev/null 2>&1 &", 
            ssh_base
        )
        time.sleep(1)
    
    try:
        # Process routers first
        for router in routers:
            logger.info(f"Stopping any existing instances on router {router['name']}")
            # Stop any existing instances
            run_command_on_server(router, "sudo pkill -9 qemu-syst || true", ssh_base)
            time.sleep(5)
            
            # Start new release
            logger.info(f"Starting release on router {router['name']}")
            start_cmd = f"cd hb-os && ./run start_release --data-disk ../cache.img --self {router['ip']}:80 --peer {router['ip']}:80"
            success, output = run_command_on_server(router, start_cmd, ssh_base)
            
            if not success:
                raise RouterError(router, "Failed to start release")
            
            # Wait for router to be ready
            logger.info(f"Waiting for router {router['name']} to become available")
            if not wait_for_router(router['ip']):
                raise TimeoutError(f"Router {router['name']} availability check", 30)
            logger.info_success(f"Router {router['name']} is now available")
        
        # Process compute nodes only if there's at least one router up
        if routers and computes:
            for compute in computes:
                logger.info(f"Stopping any existing instances on compute node {compute['name']}")
                # Stop any existing instances
                run_command_on_server(compute, "sudo pkill -9 qemu-syst || true", ssh_base)
                time.sleep(5)
                
                # Start new release
                logger.info(f"Starting release on compute node {compute['name']}")
                start_cmd = f"cd hb-os && ./run start_release --data-disk ../cache.img --self {compute['ip']}:80 --peer {routers[0]['ip']}:80"
                success, output = run_command_on_server(compute, start_cmd, ssh_base)
                
                if not success:
                    logger.error_highlight(f"Failed to start release on compute node {compute['name']}")
                else:
                    logger.info_success(f"Successfully started release on compute node {compute['name']}")
    
    except Exception as e:
        logger.error(f"Error during start operation: {e}", exc_info=True)
        raise 