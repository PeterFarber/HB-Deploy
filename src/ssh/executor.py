"""
SSH executor module.
Handles execution of commands on remote servers via SSH.
"""

import subprocess
from typing import Dict, List, Any, Optional, Tuple

from src.utils.logger import logger
from src.utils.exceptions import SSHCommandError


def run_command_on_server(
    server: Dict[str, Any], 
    command: str, 
    ssh_base: List[str],
    print_output: bool = True
) -> Tuple[bool, str]:
    """
    Run a command on a specific server via SSH.
    
    Args:
        server (Dict[str, Any]): Server configuration dictionary.
        command (str): Command to run on the server.
        ssh_base (List[str]): Base SSH command with options.
        print_output (bool): Whether to print command output to console.
        
    Returns:
        Tuple[bool, str]: Tuple containing success status and command output.
    """
    host = f"hb@{server['ip']}"
    
    if print_output:
        logger.info_highlight(f"{server['name']} - {server['ip']}:\n{command}")
    
    logger.debug(f"Executing on {server['name']}: {command}")
    
    try:
        proc = subprocess.run(
            ssh_base + [host, command],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        output = proc.stdout
        success = proc.returncode == 0
        
        if success:
            logger.debug(f"Command succeeded on {server['name']}")
        else:
            logger.error(f"Command failed on {server['name']} with code {proc.returncode}: {command}")
        
        if print_output:
            logger.info(output)
            if success:
                logger.info_success("Command Finished")
            else:
                logger.error_highlight(f"Command Failed with code {proc.returncode}")
        
        return success, output
    except Exception as e:
        error_msg = f"Error executing SSH command on {server['name']}: {e}"
        logger.error(error_msg, exc_info=True)
        if print_output:
            logger.error_highlight(error_msg)
        return False, str(e)


def run_command_on_servers(
    servers: List[Dict[str, Any]], 
    command: str, 
    ssh_base: List[str],
    stop_on_failure: bool = False
) -> Tuple[bool, Dict[str, str]]:
    """
    Run a command on multiple servers.
    
    Args:
        servers (List[Dict[str, Any]]): List of server configurations.
        command (str): Command to run on each server.
        ssh_base (List[str]): Base SSH command with options.
        stop_on_failure (bool): Whether to stop if a command fails on a server.
        
    Returns:
        Tuple[bool, Dict[str, str]]: Tuple containing overall success status and 
                                    dictionary of server IDs to command outputs.
    """
    logger.info(f"Running command: {command}")
    logger.info(f"Running command on {len(servers)} servers: {command}")
    
    results = {}
    all_success = True
    
    for server in servers:
        logger.debug(f"Running command on {server['name']}")
        success, output = run_command_on_server(server, command, ssh_base)
        results[server['id']] = output
        
        if not success:
            all_success = False
            error_msg = f"Command failed on {server['name']}"
            logger.error(error_msg)
            
            if stop_on_failure:
                logger.warning(f"Stopping further execution due to failure on {server['name']}")
                break
    
    if all_success:
        logger.info_success("Command executed successfully on all servers")
    else:
        logger.warning_highlight("Command failed on one or more servers")
    
    return all_success, results 