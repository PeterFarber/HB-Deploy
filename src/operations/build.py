"""
Build release operation module.
Handles building releases on build servers.
"""

from typing import Dict, List, Any

from src.ssh.executor import run_command_on_server
from src.ui.menu import select_servers
from src.utils.helpers import generate_random_string
from src.utils.logger import logger
from src.utils.exceptions import BuildError


def build_release_operation(servers: List[Dict[str, Any]], ssh_base: List[str]) -> None:
    """
    Build a release on build servers.
    
    Args:
        servers (List[Dict[str, Any]]): List of all server configurations.
        ssh_base (List[str]): Base SSH command with options.
    """
    # Select build servers
    sel = select_servers(servers, server_type="build")
    if not sel:
        logger.warning("No build servers selected, exiting operation")
        return
    
    for server in sel:
        logger.info(f"Starting build process on server {server['name']}")
        try:
            # Backup content.Dockerfile
            logger.debug(f"Backing up content.Dockerfile on {server['name']}")
            success, _ = run_command_on_server(
                server, 
                "cp hb-os/resources/content.Dockerfile hb-os/resources/content.Dockerfile.bak", 
                ssh_base
            )
            
            if not success:
                raise BuildError(server, "Failed to backup content.Dockerfile")
            
            # Inject random 64-character string into content.Dockerfile
            random_str = generate_random_string(64)
            logger.debug(f"Injecting build identifier into content.Dockerfile on {server['name']}")
            inject_cmd = f"sed -i '/RUN mkdir -p \\/build \\/release/a RUN echo \\\"{random_str}\\\"' /home/hb/hb-os/resources/content.Dockerfile"
            success, _ = run_command_on_server(server, inject_cmd, ssh_base)
            
            if not success:
                raise BuildError(server, "Failed to modify content.Dockerfile")
            
            # Run the build commands
            logger.info(f"Building guest on {server['name']}")
            success, _ = run_command_on_server(server, "cd hb-os && ./run build_guest", ssh_base)
            
            if not success:
                raise BuildError(server, "Failed to build guest")
            
            logger.info(f"Packaging release on {server['name']}")
            success, _ = run_command_on_server(
                server, 
                "cd hb-os && sudo rm -rf inputs.json release release.tar.gz && sudo ./run package_release", 
                ssh_base
            )
            
            if not success:
                raise BuildError(server, "Failed to package release")
            
            logger.info(f"Build completed successfully on {server['name']}")
            
        except Exception as e:
            logger.error(f"Build failed on {server['name']}: {e}", exc_info=True)
        finally:
            # Always restore content.Dockerfile
            logger.debug(f"Restoring content.Dockerfile on {server['name']}")
            run_command_on_server(
                server, 
                "mv hb-os/resources/content.Dockerfile.bak hb-os/resources/content.Dockerfile", 
                ssh_base
            ) 