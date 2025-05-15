"""
UI menu module.
Handles user interface elements like menus and server selection.
"""

from typing import Dict, List, Any, Optional, Callable, Tuple

from src.ui.colors import Colors
from src.utils.logger import logger


def display_menu(menu_items: Dict[str, Tuple[str, Callable]]) -> None:
    """
    Display a menu of options to the user.
    
    Args:
        menu_items (Dict[str, Tuple[str, Callable]]): Dictionary of menu items.
            Key is the menu selection key, value is a tuple of (name, function).
    """
    logger.info_highlight("Choose an action:")
    for k, (name, _) in menu_items.items():
        logger.info(f"{Colors.BOLD}{k}{Colors.RESET}) {Colors.BOLD}{name}{Colors.RESET}")


def get_user_input(prompt: str) -> str:
    """
    Get input from the user with a prompt.
    
    Args:
        prompt (str): The prompt to display to the user.
        
    Returns:
        str: The user's input.
    """
    logger.info(prompt)
    return input("> ").strip()


def get_user_menu_choice(menu_items: Dict[str, Tuple[str, Callable]]) -> Optional[Tuple[str, Callable]]:
    """
    Get the user's menu choice.
    
    Args:
        menu_items (Dict[str, Tuple[str, Callable]]): Dictionary of menu items.
        
    Returns:
        Optional[Tuple[str, Callable]]: The selected menu item, or None if invalid choice.
    """
    choice = input("> ").strip()
    
    if choice not in menu_items:
        logger.warning("Invalid choice, exiting.")
        return None
    
    return menu_items[choice]


def select_servers(servers: List[Dict[str, Any]], server_type: Optional[str] = None, all_servers: bool = False) -> List[Dict[str, Any]]:
    """
    Prompt the user to select servers either by comma-separated IDs
    (if input starts with a digit) or by type (if input starts with a letter).
    
    Args:
        servers (List[Dict[str, Any]]): List of server configurations.
        server_type (Optional[str]): Server type to filter by automatically.
        all_servers (bool): Whether to select all servers.
        
    Returns:
        List[Dict[str, Any]]: List of selected server configurations.
    """
    # If requested all servers or a specific type
    if all_servers:
        return servers
    
    # If a type was passed in, just use it
    if server_type is not None:
        sel = [s for s in servers if s.get("type") == server_type]
        if not sel:
            logger.warning(f"No servers of type '{server_type}' found.")
        return sel

    # Otherwise, display available servers and let the user select
    logger.info_highlight("Available servers:")
    for s in servers:
        # Determine the color based on server type
        if s['type'] == 'router':
            type_color = Colors.GREEN
        elif s['type'] == 'compute':
            type_color = Colors.RED
        elif s['type'] == 'build':
            type_color = Colors.BLUE
        elif s['type'] == 'dev':
            type_color = Colors.MAGENTA
        else:
            type_color = Colors.RESET
        logger.info(f"{Colors.BOLD}{s['id']}{Colors.RESET}) {Colors.BOLD}{s['name']}{Colors.RESET} ({type_color}{s['type']}{Colors.RESET})")

    prompt = f"Select servers by ID (e.g. {Colors.YELLOW}1{Colors.RESET},{Colors.YELLOW}2{Colors.RESET},{Colors.YELLOW}3{Colors.RESET}) or by type (e.g. {Colors.RED}compute{Colors.RESET}, {Colors.BLUE}build{Colors.RESET}, {Colors.GREEN}router{Colors.RESET}, {Colors.MAGENTA}dev{Colors.RESET}):"
    logger.info(prompt)
    inp = input("> ").strip()
    
    if not inp:
        logger.warning("No input provided.")
        return []

    first = inp[0]
    if first.isdigit():
        # Treat input as comma-separated IDs
        ids = [i.strip() for i in inp.split(",") if i.strip()]
        sel = [s for s in servers if s.get("id") in ids]
    elif first.isalpha():
        if (inp == "all"):
            return servers
        # Treat input as a server type
        sel = [s for s in servers if s.get("type") == inp]
    else:
        logger.warning("Invalid selection format.")
        return []

    if not sel:
        logger.warning("No servers matched your selection.")
    
    return sel 