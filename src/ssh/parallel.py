"""
Parallel SSH execution module.
Provides parallel execution of SSH commands across multiple servers.
"""

import time
import concurrent.futures
from typing import Dict, List, Any, Callable, Optional, Tuple, Union

from src.config.settings import settings
from src.utils.logger import logger
from src.utils.exceptions import SSHCommandError, MaxRetriesExceededError
from src.ssh.executor import run_command_on_server


def retry(
    func: Callable, 
    *args, 
    retry_count: Optional[int] = None,
    retry_delay: Optional[int] = None,
    exceptions_to_retry: Tuple[Exception] = (Exception,),
    operation_name: str = "operation",
    **kwargs
) -> Any:
    """
    Retry a function multiple times with exponential backoff.
    
    Args:
        func: The function to retry
        *args: Positional arguments to pass to the function
        retry_count: Number of retries (from settings if None)
        retry_delay: Initial delay between retries in seconds (from settings if None)
        exceptions_to_retry: Tuple of exceptions that should trigger a retry
        operation_name: Name of the operation for logging
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call
        
    Raises:
        MaxRetriesExceededError: If the maximum number of retries is exceeded
    """
    # Get retry configuration from settings if not specified
    if retry_count is None:
        retry_count = settings.get("execution", "retry_count", 3)
    
    if retry_delay is None:
        retry_delay = settings.get("execution", "retry_delay", 5)
    
    attempt = 0
    last_exception = None
    
    while attempt <= retry_count:
        try:
            return func(*args, **kwargs)
        except exceptions_to_retry as e:
            attempt += 1
            last_exception = e
            
            if attempt > retry_count:
                logger.error(f"Maximum retries ({retry_count}) exceeded for {operation_name}")
                break
            
            # Calculate exponential backoff delay
            delay = retry_delay * (2 ** (attempt - 1))
            logger.warning(
                f"Attempt {attempt}/{retry_count} failed for {operation_name}: {str(e)}. "
                f"Retrying in {delay} seconds..."
            )
            time.sleep(delay)
    
    # If we get here, all retries failed
    raise MaxRetriesExceededError(
        operation=operation_name,
        max_retries=retry_count
    ) from last_exception


def run_command_with_retry(
    server: Dict[str, Any],
    command: str,
    ssh_base: List[str],
    print_output: bool = True,
    retry_count: Optional[int] = None,
    retry_delay: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Run a command on a server with retry.
    
    Args:
        server: Server configuration
        command: Command to run
        ssh_base: Base SSH command
        print_output: Whether to print command output
        retry_count: Number of retries
        retry_delay: Delay between retries in seconds
        
    Returns:
        Tuple of success status and command output
    """
    operation_name = f"SSH command on {server['name']}"
    
    return retry(
        run_command_on_server,
        server, command, ssh_base, print_output,
        retry_count=retry_count,
        retry_delay=retry_delay,
        exceptions_to_retry=(SSHCommandError, ConnectionError, TimeoutError),
        operation_name=operation_name
    )


def run_parallel_command(
    servers: List[Dict[str, Any]],
    command: str,
    ssh_base: List[str],
    stop_on_failure: bool = False
) -> Dict[str, Union[str, Exception]]:
    """
    Run a command on multiple servers in parallel.
    A simpler interface to run_parallel_commands.
    
    Args:
        servers: List of server configurations
        command: Command to run
        ssh_base: Base SSH command
        stop_on_failure: Whether to stop if a command fails
        
    Returns:
        Dictionary mapping server IDs to command outputs or exceptions
    """
    logger.info_highlight(f"Running command in parallel on {len(servers)} servers")
    logger.info(f"Command: {command}")
    
    results = run_parallel_commands(
        servers,
        command,
        ssh_base,
        print_output=True,
        stop_on_failure=stop_on_failure
    )
    
    # Count successes and failures
    failures = sum(1 for s in servers if isinstance(results.get(s['id']), Exception))
    
    if failures == 0:
        logger.info_success(f"Command executed successfully on all {len(servers)} servers")
    else:
        success_count = len(servers) - failures
        logger.warning_highlight(f"Command completed with {success_count} successes and {failures} failures")
    
    return results


def run_parallel_commands(
    servers: List[Dict[str, Any]],
    command: str,
    ssh_base: List[str],
    max_workers: Optional[int] = None,
    timeout: Optional[int] = None,
    print_output: bool = True,
    stop_on_failure: bool = False,
    retry_count: Optional[int] = None,
    retry_delay: Optional[int] = None
) -> Dict[str, Union[str, Exception]]:
    """
    Run a command on multiple servers in parallel.
    
    Args:
        servers: List of server configurations
        command: Command to run
        ssh_base: Base SSH command
        max_workers: Maximum number of worker threads
        timeout: Timeout for each command in seconds
        print_output: Whether to print command output
        stop_on_failure: Whether to stop if a command fails
        retry_count: Number of retries for each command
        retry_delay: Initial delay between retries in seconds
        
    Returns:
        Dictionary mapping server IDs to command outputs or exceptions
    """
    # Get configuration from settings if not specified
    if max_workers is None:
        max_workers = settings.get("execution", "max_workers", 5)
    
    if timeout is None:
        timeout = settings.get("execution", "timeout", 300)
    
    results = {}
    futures = {}
    
    logger.info(f"Running command in parallel on {len(servers)} servers: {command}")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        for server in servers:
            future = executor.submit(
                run_command_with_retry,
                server,
                command,
                ssh_base,
                print_output,
                retry_count,
                retry_delay
            )
            futures[future] = server
        
        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            server = futures[future]
            try:
                success, output = future.result(timeout=timeout)
                results[server['id']] = output
                
                if not success and stop_on_failure:
                    # Cancel remaining futures
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    logger.error(f"Command failed on {server['name']}, stopping remaining tasks")
                    break
                    
            except Exception as e:
                logger.error(f"Error running command on {server['name']}: {str(e)}")
                results[server['id']] = e
                
                if stop_on_failure:
                    # Cancel remaining futures
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    logger.error(f"Command failed on {server['name']}, stopping remaining tasks")
                    break
    
    return results 