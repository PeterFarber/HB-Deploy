"""
Main module.
Handles the main application workflow and menu.
"""

import sys
from typing import Dict, List, Any, Callable, Optional, Tuple

# Initialize logging first
from src.utils.logger import logger, setup_logging

# Then import other modules
from src.config.settings import settings
from src.config.servers import load_servers
from src.ssh.key_manager import select_ssh_key, get_ssh_command_base
from src.ui.menu import display_menu, get_user_menu_choice
from src.cli.arguments import parse_arguments, update_settings_from_args
from src.cli.shell import run_interactive_shell

# Import operations
from src.operations.build import build_release_operation
from src.operations.download import download_release_operation
from src.operations.start import start_release_operation
from src.operations.shutdown import shutdown_release_operation
from src.operations.update_config import update_config_operation
from src.operations.run_command import run_command_operation


def create_menu() -> Dict[str, Tuple[str, Callable]]:
    """
    Create the main application menu.
    
    Returns:
        Dict[str, Tuple[str, Callable]]: Menu items dictionary.
    """
    return {
        "1": ("download_release", download_release_operation),
        "2": ("build_release", build_release_operation),
        "3": ("start_release", start_release_operation),
        "4": ("shutdown_release", shutdown_release_operation),
        "5": ("update_config", update_config_operation),
        "6": ("run", run_command_operation),
    }


def run_cli_mode(args: Dict[str, Any]) -> int:
    """
    Run in CLI mode with arguments.
    
    Args:
        args: Command-line arguments
        
    Returns:
        int: Exit code
    """
    # Load server configurations
    server_config_file = settings.get("server", "config_file")
    servers = load_servers(server_config_file)
    
    # Select SSH key
    key_file = args.get("key") or settings.get("ssh", "identity_file")
    if not key_file:
        key_file = select_ssh_key()
    
    # Get base SSH command
    ssh_base = get_ssh_command_base(key_file)
    
    # Determine which operation to run
    operation = args.get("operation")
    if not operation:
        logger.error("No operation specified")
        return 1
    
    # Handle interactive shell
    if operation == "shell":
        run_interactive_shell(servers, ssh_base)
        return 0
    
    # Handle other operations
    try:
        # Filter servers by --servers or --type arguments
        selected_servers = servers
        if args.get("servers"):
            selected_servers = [s for s in servers if s["id"] in args["servers"]]
            if not selected_servers:
                logger.error(f"No servers found matching the provided IDs: {args['servers']}")
                return 1
        elif args.get("type"):
            server_type = args.get("type")
            selected_servers = [s for s in servers if s["type"] == server_type]
            if server_type == "all":
                selected_servers = servers
            if not selected_servers:
                logger.error(f"No servers found with type: {server_type}")
                return 1
        
        # Pre-selected servers flag (true when servers were selected via CLI args)
        pre_selected = bool(args.get("servers") or args.get("type"))
        
        if operation == "download":
            download_release_operation(selected_servers, ssh_base)
        elif operation == "build":
            build_release_operation(selected_servers, ssh_base)
        elif operation == "start":
            start_release_operation(selected_servers, ssh_base)
        elif operation == "shutdown":
            # Get parallel execution preference from settings or args
            parallel_mode = None
            if args.get("parallel") is not None:
                parallel_mode = args.get("parallel")
            elif settings.get("execution", "parallel") is not None:
                parallel_mode = settings.get("execution", "parallel")
                
            shutdown_release_operation(
                selected_servers, 
                ssh_base,
                skip_server_selection=pre_selected,
                parallel=parallel_mode
            )
        elif operation == "update-config":
            update_config_operation(selected_servers, ssh_base)
        elif operation == "run":
            cmd = args.get("command")
            if not cmd:
                logger.error("No command specified for 'run' operation")
                return 1
                
            # Get parallel execution preference from settings or args
            parallel_mode = None
            if args.get("parallel") is not None:
                parallel_mode = args.get("parallel")
            elif settings.get("execution", "parallel") is not None:
                parallel_mode = settings.get("execution", "parallel")
                
            # Skip server selection if servers were pre-selected from command line
            run_command_operation(
                selected_servers, 
                ssh_base, 
                cmd,
                skip_server_selection=pre_selected,
                parallel=parallel_mode
            )
        else:
            logger.error(f"Unknown operation: {operation}")
            return 1
        
        return 0
    
    except Exception as e:
        logger.error(f"Error executing {operation}: {e}", exc_info=True)
        return 1


def run_interactive_mode() -> int:
    """
    Run in interactive menu mode.
    
    Returns:
        int: Exit code
    """
    # Load server configurations
    server_config_file = settings.get("server", "config_file")
    servers = load_servers(server_config_file)
    
    # Select SSH key and get base command
    keyfile = select_ssh_key()
    ssh_base = get_ssh_command_base(keyfile)
    
    # Create and display menu
    menu = create_menu()
    display_menu(menu)
    
    # Get user's choice
    choice = get_user_menu_choice(menu)
    if not choice:
        return 0
    
    # Execute selected operation
    action_name, action_fn = choice
    logger.info("")  # Empty line for visual separation
    
    try:
        if action_name == "run":
            # run_command is special, it needs to get the command from user
            action_fn(servers, ssh_base)
        else:
            # All other operations just take the servers list
            action_fn(servers, ssh_base)
        return 0
    
    except Exception as e:
        logger.error(f"Error executing {action_name}: {e}", exc_info=True)
        return 1


def main() -> int:
    """
    Main application entry point.
    
    Returns:
        int: Exit code
    """
    # Parse command-line arguments
    args = parse_arguments()
    
    # Update settings from arguments
    update_settings_from_args(args)
    
    # Set up logging
    log_level = args.get("log_level")
    log_file = args.get("log_file")
    setup_logging("hb", log_level, log_file)
    
    # Determine the mode based on arguments
    if args.get("operation"):
        # CLI mode
        return run_cli_mode(args)
    else:
        # Interactive menu mode
        return run_interactive_mode()


if __name__ == "__main__":
    sys.exit(main()) 