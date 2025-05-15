"""
Command-line arguments module.
Handles parsing and validating command-line arguments.
"""

import argparse
import sys
from typing import Dict, Any, Optional, List

from src.config.settings import settings


def parse_arguments(args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Parse command-line arguments.
    
    Args:
        args: Command-line arguments (sys.argv[1:] if None)
        
    Returns:
        Dict: Parsed arguments as a dictionary
    """
    if args is None:
        args = sys.argv[1:]
    
    parser = argparse.ArgumentParser(
        description="HB Deploy - Deployment tool for HB servers",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Add global arguments
    parser.add_argument(
        "--config", 
        help="Path to a configuration file"
    )
    parser.add_argument(
        "--log-level", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level"
    )
    parser.add_argument(
        "--log-file", 
        help="Path to the log file"
    )
    parser.add_argument(
        "--key",
        help="SSH key to use"
    )
    
    # Create subparsers for different operations
    subparsers = parser.add_subparsers(
        dest="operation",
        help="Operation to perform"
    )
    
    # Add common arguments that can be used with any subcommand
    common_args = argparse.ArgumentParser(add_help=False)
    common_args.add_argument(
        "--parallel",
        action="store_true",
        help="Execute commands in parallel"
    )
    common_args.add_argument(
        "--max-workers",
        type=int,
        help="Maximum number of parallel workers"
    )
    common_args.add_argument(
        "--timeout",
        type=int,
        help="Timeout for operations in seconds"
    )
    common_args.add_argument(
        "--retries",
        type=int,
        help="Number of retries for operations"
    )
    
    # download_release operation
    download_parser = subparsers.add_parser(
        "download",
        parents=[common_args],
        help="Download a release from a build server"
    )
    download_parser.add_argument(
        "--servers",
        help="Comma-separated list of server IDs to download to"
    )
    download_parser.add_argument(
        "--type",
        help="Server type to download to (e.g., router, compute)"
    )
    
    # build_release operation
    build_parser = subparsers.add_parser(
        "build",
        parents=[common_args],
        help="Build a release on a build server"
    )
    build_parser.add_argument(
        "--servers",
        help="Comma-separated list of build server IDs"
    )
    
    # start_release operation
    start_parser = subparsers.add_parser(
        "start",
        parents=[common_args],
        help="Start a release on router and compute servers"
    )
    start_parser.add_argument(
        "--servers",
        help="Comma-separated list of server IDs to start"
    )
    start_parser.add_argument(
        "--type",
        help="Server type to start (e.g., router, compute)"
    )
    
    # shutdown_release operation
    shutdown_parser = subparsers.add_parser(
        "shutdown",
        parents=[common_args],
        help="Terminate QEMU processes on servers"
    )
    shutdown_parser.add_argument(
        "--servers",
        help="Comma-separated list of server IDs to shut down"
    )
    shutdown_parser.add_argument(
        "--type",
        help="Server type to shut down (e.g., router, compute)"
    )
    
    # update_config operation
    update_parser = subparsers.add_parser(
        "update-config",
        parents=[common_args],
        help="Update configuration on servers"
    )
    update_parser.add_argument(
        "--servers",
        help="Comma-separated list of server IDs to update"
    )
    update_parser.add_argument(
        "--type",
        help="Server type to update (e.g., router, compute)"
    )
    
    # run command operation
    run_parser = subparsers.add_parser(
        "run",
        parents=[common_args],
        help="Run a command on servers"
    )
    run_parser.add_argument(
        "command",
        nargs="?",  # Make it optional for interactive mode
        help="Command to run"
    )
    run_parser.add_argument(
        "--servers",
        help="Comma-separated list of server IDs to run on"
    )
    run_parser.add_argument(
        "--type",
        help="Server type to run on (e.g., router, compute, build)"
    )
    
    # shell operation for interactive shell
    shell_parser = subparsers.add_parser(
        "shell",
        parents=[common_args],
        help="Start an interactive shell"
    )
    
    # Parse the arguments
    parsed_args = parser.parse_args(args)
    
    # Convert to dictionary
    args_dict = vars(parsed_args)
    
    # Process comma-separated server IDs (only if --servers flag used)
    if args_dict.get("servers"):
        # Check if the server argument is possibly a type
        # This handles the case where someone does --servers compute instead of --type compute
        server_types = ["build", "router", "compute", "dev"]
        if args_dict["servers"] in server_types and not args_dict.get("type"):
            # This is likely a server type provided to --servers by mistake
            args_dict["type"] = args_dict["servers"]
            args_dict["servers"] = None
        else:
            # Process as normal server IDs
            args_dict["servers"] = [
                s.strip() for s in args_dict["servers"].split(",") if s.strip()
            ]
    
    return args_dict


def update_settings_from_args(args: Dict[str, Any]) -> None:
    """
    Update settings from command-line arguments.
    
    Args:
        args: Parsed command-line arguments
    """
    # Update settings with command-line arguments
    if args.get("config"):
        # Load a specific config file
        # This would typically be handled before this function is called
        pass
    
    # Update logging settings
    if args.get("log_level"):
        settings.set("logging", "level", args["log_level"])
    
    if args.get("log_file"):
        settings.set("logging", "file", args["log_file"])
    
    # Update execution settings
    if args.get("parallel") is not None:
        settings.set("execution", "parallel", args["parallel"])
    
    if args.get("max_workers") is not None:
        settings.set("execution", "max_workers", args["max_workers"])
    
    if args.get("timeout") is not None:
        settings.set("execution", "timeout", args["timeout"])
    
    if args.get("retries") is not None:
        settings.set("execution", "retry_count", args["retries"])
    
    # Update SSH settings
    if args.get("key"):
        settings.set("ssh", "identity_file", args["key"]) 