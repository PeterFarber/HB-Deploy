"""
Shutdown operation module.
Handles terminating QEMU processes on servers.
"""

from typing import Dict, List, Any, Optional, Union, Tuple

from src.ssh.executor import run_command_on_server, run_command_on_servers
from src.ssh.parallel import run_parallel_command
from src.ui.menu import select_servers, get_user_input
from src.utils.logger import logger
from src.utils.exceptions import SSHCommandError
from src.config.settings import settings


def shutdown_release_operation(
    servers: List[Dict[str, Any]], 
    ssh_base: List[str],
    skip_server_selection: bool = False,
    parallel: Optional[bool] = None
) -> Union[None, Tuple[bool, Dict[str, str]]]:
    """
    Terminate QEMU processes on selected servers.
    
    Args:
        servers (List[Dict[str, Any]]): List of server configurations.
        ssh_base (List[str]): Base SSH command with options.
        skip_server_selection (bool): Whether to skip server selection.
        parallel (Optional[bool]): Whether to run in parallel mode. If None, will use settings or prompt.
        
    Returns:
        None or Tuple[bool, Dict[str, str]]: None if interactive mode, or success and results if called programmatically
    """
    # Only select servers if we're not skipping selection
    sel = servers
    if not skip_server_selection:
        sel = select_servers(servers)
        if not sel:
            logger.warning("No servers selected, exiting operation")
            return None
    
    logger.info_highlight(f"Shutting down QEMU processes on {len(sel)} servers")
    
    try:
        # Determine if we should run in parallel
        run_parallel = parallel
        
        # If parallel mode wasn't specified, check settings
        if run_parallel is None:
            if settings.get("execution", "parallel", False):
                # Use the setting if available
                run_parallel = True
                logger.info("Using parallel execution from settings")
            else:
                # Otherwise ask the user
                run_parallel = get_user_input("Run in parallel? (y/n): ").lower() == "y"
        
        # Shutdown command - terminate any QEMU system processes
        command = "sudo pkill -9 qemu-syst || true"
        
        results = None
        success = False
        
        if run_parallel:
            logger.info_action("Shutting down in parallel mode")
            results = run_parallel_command(sel, command, ssh_base)
            # For simplicity, consider it successful if we got results
            success = bool(results)
        else:
            logger.info_action("Shutting down in sequential mode")
            success, results = run_command_on_servers(sel, command, ssh_base, stop_on_failure=False)
        
        # Verify that processes were terminated
        for server in sel:
            logger.info(f"Verifying shutdown on {server['name']}")
            check_cmd = "pgrep -l qemu-syst || echo 'No QEMU processes found'"
            success, output = run_command_on_server(server, check_cmd, ssh_base)
            
            if "No QEMU processes found" not in output and "qemu-syst" in output:
                logger.warning_highlight(f"QEMU processes may still be running on {server['name']}")
            else:
                logger.info_success(f"Successfully shut down QEMU on {server['name']}")
        
        logger.info_success("Shutdown operation completed")
        return success, results
    
    except Exception as e:
        logger.error(f"Error during shutdown operation: {e}", exc_info=True)
        raise 