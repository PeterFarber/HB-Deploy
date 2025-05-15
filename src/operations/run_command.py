"""
Run command operation module.
Handles running arbitrary commands on servers.
"""

from typing import Dict, List, Any, Optional, Union, Tuple

from src.ssh.executor import run_command_on_servers
from src.ssh.parallel import run_parallel_command
from src.ui.menu import select_servers, get_user_input
from src.utils.logger import logger
from src.utils.exceptions import SSHCommandError
from src.config.settings import settings


def get_command_input() -> Optional[str]:
    """
    Get command input from the user.
    
    Returns:
        Optional[str]: The command to run, or None if cancelled.
    """
    command = get_user_input(
        "Enter command to run on selected servers (leave empty to cancel): "
    )
    
    if not command:
        return None
    
    return command


def run_command_operation(
    servers: List[Dict[str, Any]], 
    ssh_base: List[str],
    command: Optional[str] = None,
    skip_server_selection: bool = False,
    parallel: Optional[bool] = None
) -> Union[None, Tuple[bool, Dict[str, str]]]:
    """
    Run a command on selected servers.
    
    Args:
        servers (List[Dict[str, Any]]): List of server configurations.
        ssh_base (List[str]): Base SSH command with options.
        command (Optional[str]): Command to run. If None, will prompt the user.
        skip_server_selection (bool): Whether to skip server selection.
        parallel (Optional[bool]): Whether to run in parallel mode. If None, will prompt the user.
        
    Returns:
        None or Tuple[bool, Dict[str, str]]: None if interactive mode, or success and results if called with command
    """
    # Only select servers if we're not skipping selection
    sel = servers
    if not skip_server_selection:
        sel = select_servers(servers)
        if not sel:
            logger.warning("No servers selected, exiting operation")
            return None
    
    # Get command if not provided
    if not command:
        command = get_command_input()
        if not command:
            logger.info("Command operation cancelled by user")
            return None
    
    logger.info_highlight(f"Running command '{command}' on {len(sel)} servers")
    
    try:
        # Determine if we should run in parallel
        run_parallel = parallel
        
        # If parallel mode wasn't specified, check settings or ask the user
        if run_parallel is None:
            if settings.get("execution", "parallel", False):
                # Use the setting if available
                run_parallel = True
                logger.info("Using parallel execution from settings")
            else:
                # Otherwise ask the user
                run_parallel = get_user_input("Run in parallel? (y/n): ").lower() == "y"
        
        results = None
        success = False
        
        if run_parallel:
            logger.info_action("Running command in parallel mode")
            results = run_parallel_command(sel, command, ssh_base)
            # For simplicity, consider it successful if we got results
            success = bool(results)
        else:
            logger.info_action("Running command in sequential mode")
            success, results = run_command_on_servers(sel, command, ssh_base, stop_on_failure=False)
            
            if not success:
                logger.warning_highlight("Command failed on one or more servers")
                raise SSHCommandError(command=command)
            
            logger.info_success("Command execution completed successfully")
            
        return success, results
    
    except Exception as e:
        logger.error(f"Error during command execution: {e}", exc_info=True)
        raise 