"""
Interactive shell module.
Provides an interactive shell interface with command history and completion.
"""

import os
import sys
import shlex
import readline
import atexit
from typing import Dict, List, Any, Callable, Optional, Tuple

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, WordCompleter

from src.config.settings import settings
from src.config.servers import load_servers
from src.ssh.key_manager import select_ssh_key, get_ssh_command_base
from src.utils.logger import logger
from src.operations.build import build_release_operation
from src.operations.download import download_release_operation
from src.operations.start import start_release_operation
from src.operations.shutdown import shutdown_release_operation
from src.operations.update_config import update_config_operation
from src.operations.run_command import run_command_operation


class HBCompleter(Completer):
    """Custom completer for HB shell."""
    
    def __init__(self, servers: List[Dict[str, Any]]):
        """
        Initialize the completer.
        
        Args:
            servers: List of server configurations
        """
        self.servers = servers
        self.commands = [
            "download", "build", "start", "shutdown", "update-config", "run", 
            "help", "exit", "quit", "servers", "parallel"
        ]
        self.server_ids = [s["id"] for s in servers]
        self.server_types = list(set(s["type"] for s in servers))
        
        # Create a mapping of command to subcommands/arguments
        self.command_args = {
            "download": ["--servers", "--type"],
            "build": ["--servers"],
            "start": ["--servers", "--type"],
            "shutdown": ["--servers", "--type"],
            "update-config": ["--servers", "--type"],
            "run": ["--servers", "--type"],
            "parallel": ["on", "off"],
            "help": self.commands,
        }
    
    def get_completions(self, document, complete_event):
        """
        Get completions for the current document.
        
        Args:
            document: The current input document
            complete_event: The completion event
            
        Yields:
            Completion: Potential completions
        """
        text = document.text
        
        # Split the input into words
        words = shlex.split(text) if text else []
        word_index = len(words)
        
        # Find the word being completed
        if not text or text[-1].isspace():
            # No word is being completed, add a new empty word
            words.append("")
            word_index = len(words) - 1
        
        # Define the current word and the words before it
        current_word = words[word_index] if word_index < len(words) else ""
        prev_word = words[word_index - 1] if word_index > 0 else ""
        
        # Check if we're completing the first word (command)
        if word_index == 0:
            for command in self.commands:
                if command.startswith(current_word):
                    yield Completion(command, start_position=-len(current_word))
            return
        
        # Command-specific completions
        command = words[0]
        
        # If the previous word is a flag that expects a server ID
        if prev_word == "--servers":
            for server_id in self.server_ids:
                if server_id.startswith(current_word):
                    yield Completion(server_id, start_position=-len(current_word))
            return
        
        # If the previous word is a flag that expects a server type
        if prev_word == "--type":
            for server_type in self.server_types:
                if server_type.startswith(current_word):
                    yield Completion(server_type, start_position=-len(current_word))
            return
        
        # If we're completing the second word or later, offer appropriate arguments
        if command in self.command_args:
            for arg in self.command_args[command]:
                if arg.startswith(current_word):
                    yield Completion(arg, start_position=-len(current_word))


def print_help(commands: Dict[str, Tuple[str, Callable]]) -> None:
    """
    Print help information.
    
    Args:
        commands: Dictionary of commands
    """
    logger.info_highlight("Available commands:")
    logger.info("  download [--servers ID1,ID2,...] [--type TYPE]")
    logger.info("      Download a release from a build server")
    logger.info("  build [--servers ID1,ID2,...]")
    logger.info("      Build a release on build servers")
    logger.info("  start [--servers ID1,ID2,...] [--type TYPE]")
    logger.info("      Start a release on router and compute servers")
    logger.info("  shutdown [--servers ID1,ID2,...] [--type TYPE]")
    logger.info("      Terminate QEMU processes on servers")
    logger.info("  update-config [--servers ID1,ID2,...] [--type TYPE]")
    logger.info("      Update configuration on servers")
    logger.info("  run [--servers ID1,ID2,...] [--type TYPE] COMMAND")
    logger.info("      Run a command on servers")
    logger.info("  servers")
    logger.info("      List available servers")
    logger.info("  parallel [on|off]")
    logger.info("      Enable or disable parallel execution")
    logger.info("  help")
    logger.info("      Show this help message")
    logger.info("  exit, quit")
    logger.info("      Exit the shell")


def list_servers(servers: List[Dict[str, Any]]) -> None:
    """
    List available servers.
    
    Args:
        servers: List of server configurations
    """
    logger.info_highlight("Available servers:")
    for server in servers:
        logger.info(f"  {server['id']}: {server['name']} ({server['type']}) - {server['ip']}")


def parse_shell_command(command_line: str) -> Tuple[str, Dict[str, Any]]:
    """
    Parse a shell command into a command and arguments.
    
    Args:
        command_line: The command line to parse
        
    Returns:
        Tuple of command and arguments dictionary
    """
    args_dict = {
        "operation": None,
        "servers": None,
        "type": None,
        "command": None
    }
    
    if not command_line:
        return "", args_dict
    
    try:
        # Split the command line into words
        words = shlex.split(command_line)
        
        if not words:
            return "", args_dict
        
        # The first word is the command
        cmd = words[0]
        args_dict["operation"] = cmd
        
        # Process the remaining words as arguments
        i = 1
        while i < len(words):
            arg = words[i]
            
            if arg == "--servers":
                if i + 1 < len(words) and not words[i + 1].startswith("--"):
                    args_dict["servers"] = [
                        s.strip() for s in words[i + 1].split(",") if s.strip()
                    ]
                    i += 2
                else:
                    i += 1
            elif arg == "--type":
                if i + 1 < len(words) and not words[i + 1].startswith("--"):
                    args_dict["type"] = words[i + 1]
                    i += 2
                else:
                    i += 1
            else:
                # If it's not a recognized flag, assume it's the command for "run"
                if cmd == "run":
                    args_dict["command"] = " ".join(words[i:])
                i = len(words)  # Exit the loop
        
        return cmd, args_dict
    
    except Exception as e:
        logger.error(f"Error parsing command: {e}")
        return "", args_dict


def run_shell_command(
    command: str, 
    args: Dict[str, Any], 
    servers: List[Dict[str, Any]], 
    ssh_base: List[str]
) -> bool:
    """
    Run a shell command.
    
    Args:
        command: The command to run
        args: The command arguments
        servers: List of server configurations
        ssh_base: Base SSH command
        
    Returns:
        bool: True if the command should continue, False to exit
    """
    if command in ("exit", "quit"):
        return False
    
    elif command == "help":
        print_help({})
    
    elif command == "servers":
        list_servers(servers)
    
    elif command == "parallel":
        value = args.get("servers", ["on"])[0] if args.get("servers") else "on"
        if value.lower() in ("on", "true", "yes", "1"):
            settings.set("execution", "parallel", True)
            logger.info_success("Parallel execution enabled")
        elif value.lower() in ("off", "false", "no", "0"):
            settings.set("execution", "parallel", False)
            logger.info("Parallel execution disabled")
        else:
            logger.warning(f"Invalid value for parallel: {value}")
            logger.info("Usage: parallel [on|off]")
    
    elif command == "download":
        selected_servers = servers
        if args.get("servers"):
            selected_servers = [s for s in servers if s["id"] in args["servers"]]
        elif args.get("type"):
            selected_servers = [s for s in servers if s["type"] == args["type"]]
        
        download_release_operation(selected_servers, ssh_base)
    
    elif command == "build":
        selected_servers = servers
        if args.get("servers"):
            selected_servers = [s for s in servers if s["id"] in args["servers"]]
        else:
            selected_servers = [s for s in servers if s["type"] == "build"]
        
        build_release_operation(selected_servers, ssh_base)
    
    elif command == "start":
        selected_servers = servers
        if args.get("servers"):
            selected_servers = [s for s in servers if s["id"] in args["servers"]]
        elif args.get("type"):
            selected_servers = [s for s in servers if s["type"] == args["type"]]
        
        start_release_operation(selected_servers, ssh_base)
    
    elif command == "shutdown":
        selected_servers = servers
        if args.get("servers"):
            selected_servers = [s for s in servers if s["id"] in args["servers"]]
        elif args.get("type"):
            selected_servers = [s for s in servers if s["type"] == args["type"]]
        
        # Determine if we should run in parallel
        parallel_mode = settings.get("execution", "parallel", False)
        
        shutdown_release_operation(selected_servers, ssh_base, parallel=parallel_mode)
    
    elif command == "update-config":
        selected_servers = servers
        if args.get("servers"):
            selected_servers = [s for s in servers if s["id"] in args["servers"]]
        elif args.get("type"):
            selected_servers = [s for s in servers if s["type"] == args["type"]]
        
        update_config_operation(selected_servers, ssh_base)
    
    elif command == "run":
        if not args.get("command"):
            logger.error("Missing command")
            logger.info("Usage: run [--servers ID1,ID2,...] [--type TYPE] COMMAND")
            return True
        
        selected_servers = servers
        if args.get("servers"):
            selected_servers = [s for s in servers if s["id"] in args["servers"]]
        elif args.get("type"):
            selected_servers = [s for s in servers if s["type"] == args["type"]]
        
        # Run the command directly without the interactive prompt
        command_to_run = args.get("command")
        run_command_operation(selected_servers, ssh_base, command_to_run)
    
    else:
        if command:
            logger.warning(f"Unknown command: {command}")
            logger.info("Type 'help' for a list of commands")
    
    return True


def run_interactive_shell() -> None:
    """
    Run an interactive shell.
    """
    # Load server configurations
    servers = load_servers()
    
    # Select SSH key and get base command
    keyfile = select_ssh_key()
    ssh_base = get_ssh_command_base(keyfile)
    
    # Create a prompt session with history
    history_file = os.path.expanduser("~/.hb_deploy_history")
    session = PromptSession(
        history=FileHistory(history_file),
        auto_suggest=AutoSuggestFromHistory(),
        completer=HBCompleter(servers)
    )
    
    logger.info_highlight("HB Deploy Interactive Shell")
    logger.info("Type 'help' for a list of commands, 'exit' to quit")
    
    try:
        while True:
            try:
                # Get a command from the user
                command_line = session.prompt("hb> ")
                
                # Parse the command line
                command, args = parse_shell_command(command_line)
                
                # Run the command
                if not run_shell_command(command, args, servers, ssh_base):
                    break
                
            except KeyboardInterrupt:
                logger.info("^C")
            except EOFError:
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Shell error: {e}")
    
    logger.info("Goodbye!")


if __name__ == "__main__":
    run_interactive_shell() 