"""
SSH key management module.
Handles SSH key selection, authentication, and SSH agent interactions.
"""

import os
import glob
import subprocess
import re
from typing import List, Optional, Tuple, Dict

from src.ui.colors import Colors
from src.utils.logger import logger


def find_ssh_keys() -> List[str]:
    """
    Find SSH private key files in the ~/.ssh directory.
    
    Returns:
        List[str]: List of paths to SSH private key files.
    """
    ssh_dir = os.path.expanduser("~/.ssh")
    candidates = []
    # Common non-key files to exclude
    excluded_names = ["config", "known_hosts", "authorized_keys", "agent_info", "last_selected_key"]
    excluded_extensions = [".pub", ".config", ".old", ".bak"]
    
    for p in glob.glob(os.path.join(ssh_dir, "*")):
        name = os.path.basename(p)
        # Skip known non-key files
        if name in excluded_names:
            continue
        # Skip files with known non-key extensions
        if any(name.endswith(ext) for ext in excluded_extensions):
            continue
        # Skip directories
        if not os.path.isfile(p):
            continue
        # Skip very large files (keys are small)
        if os.path.getsize(p) > 10000:  # Most SSH keys are under 10KB
            continue
            
        candidates.append(p)
    return candidates


def load_agent_from_file() -> bool:
    """
    Load SSH agent information from the saved file.
    
    Returns:
        bool: True if agent info was loaded successfully, False otherwise.
    """
    agent_file = os.path.expanduser("~/.ssh/agent_info")
    if not os.path.exists(agent_file):
        return False
    
    try:
        with open(agent_file, 'r') as f:
            agent_output = f.read()
        
        # Extract environment variables from agent output
        for line in agent_output.splitlines():
            if line.startswith("SSH_AUTH_SOCK=") or line.startswith("SSH_AGENT_PID="):
                var, value = line.split(";", 1)[0].split("=", 1)
                os.environ[var] = value
        
        # Verify the agent is actually running
        pid_str = os.environ.get('SSH_AGENT_PID')
        sock_path = os.environ.get('SSH_AUTH_SOCK')
        
        if pid_str and sock_path:
            # Check if the process exists
            try:
                pid = int(pid_str)
                # On Unix, sending signal 0 checks if process exists
                os.kill(pid, 0)
                # Also verify socket exists
                if os.path.exists(sock_path):
                    return True
            except (OSError, ValueError):
                # Process doesn't exist or invalid PID
                pass
                
        return False
        
    except Exception as e:
        logger.debug(f"Failed to load agent info: {e}")
        return False


def start_ssh_agent() -> bool:
    """
    Start an SSH agent if one is not already running.
    First tries to use an existing agent, then loads saved agent info,
    and finally starts a new agent if needed.
    
    Returns:
        bool: True if an agent is running (either started or pre-existing),
              False if agent couldn't be started.
    """
    # First check if agent is already in environment
    agent_sock = os.environ.get('SSH_AUTH_SOCK')
    agent_pid = os.environ.get('SSH_AGENT_PID')
    
    # If both variables are set, check if agent is still running
    if agent_sock and agent_pid and os.path.exists(agent_sock):
        try:
            # Test if agent is working by listing keys
            result = subprocess.run(["ssh-add", "-l"], 
                                   capture_output=True, 
                                   text=True, 
                                   env=os.environ)
            if result.returncode in (0, 1):  # 0 = keys found, 1 = no keys but agent running
                logger.info_success("Using existing SSH agent.")
                return True
        except Exception:
            # If checking fails, continue to next method
            pass
    
    # Try to load agent from saved file
    if load_agent_from_file():
        logger.info_success("Loaded SSH agent from saved info.")
        return True
    
    # Start a new agent if all else fails
    logger.info("Starting new SSH agent...")
    try:
        # Start ssh-agent and capture its environment variables
        agent_output = subprocess.check_output(["ssh-agent", "-s"], text=True)
        # Parse and set environment variables
        for line in agent_output.splitlines():
            if line.startswith("SSH_AUTH_SOCK=") or line.startswith("SSH_AGENT_PID="):
                var, value = line.split(";", 1)[0].split("=", 1)
                os.environ[var] = value
        logger.info_success("SSH agent started.")
        
        # Save agent info to a file for future script runs
        agent_file = os.path.expanduser("~/.ssh/agent_info")
        with open(agent_file, "w") as f:
            f.write(agent_output)
        os.chmod(agent_file, 0o600)  # Secure the file
        return True
    except Exception as e:
        logger.error(f"Error starting SSH agent: {e}")
        logger.warning("Will continue anyway, in case agent is already running.")
        return False


def extract_fingerprint(output: str) -> Optional[str]:
    """
    Extract fingerprint from ssh-keygen output.
    
    Args:
        output (str): The output from ssh-keygen -l
        
    Returns:
        Optional[str]: The fingerprint if found, None otherwise
    """
    # Regular expression to extract the fingerprint hash
    match = re.search(r'([0-9a-f]{2}(:[0-9a-f]{2})+)', output)
    if match:
        return match.group(1)
    return None


def check_key_in_agent(key_path: str) -> bool:
    """
    Check if a key is already added to the SSH agent.
    
    Args:
        key_path (str): Path to the SSH key file.
        
    Returns:
        bool: True if the key is already in the agent, False otherwise.
    """
    try:
        # Get the key fingerprint
        key_fingerprint_cmd = ["ssh-keygen", "-l", "-f", key_path]
        key_result = subprocess.run(key_fingerprint_cmd, capture_output=True, text=True)
        
        if key_result.returncode == 0:
            key_fingerprint = extract_fingerprint(key_result.stdout)
            if key_fingerprint:
                # List keys in the agent with fingerprints
                agent_cmd = ["ssh-add", "-l"]
                agent_result = subprocess.run(agent_cmd, capture_output=True, text=True, env=os.environ)
                
                # Check if the fingerprint is in the agent output
                if agent_result.returncode == 0 and key_fingerprint in agent_result.stdout:
                    logger.debug(f"Key {os.path.basename(key_path)} is already in the agent")
                    return True
        
        # Test the key with SSH
        # Try to make a non-interactive connection (this will fail, but we're checking the error message)
        test_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "IdentitiesOnly=yes", "-i", key_path, "-p", "22", "user@localhost", "true"]
        test_result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=2)
        
        # If we get permission denied (public key), the key is loaded but not authorized
        # If we get connection refused, the key is loaded but localhost isn't running SSH
        if "Permission denied (publickey)" in test_result.stderr or "Connection refused" in test_result.stderr:
            logger.debug(f"Key {os.path.basename(key_path)} is in the agent (verified by test connection)")
            return True
                    
    except Exception as e:
        logger.debug(f"Error checking if key is in agent: {e}")
    
    return False


def add_key_to_agent(key_path: str) -> bool:
    """
    Add an SSH key to the agent.
    
    Args:
        key_path (str): Path to the SSH key file.
        
    Returns:
        bool: True if the key was added successfully, False otherwise.
    """
    # Check if the key is already in the agent
    if check_key_in_agent(key_path):
        logger.info_success("Key is already loaded in the agent.")
        return True
    
    logger.info("Adding key to SSH agent...")
    result = subprocess.run(["ssh-add", key_path], capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info_success("Key added successfully!")
        return True
    else:
        error = result.stderr.strip()
        logger.error(f"Failed to add key: {error}")
        if "already added" in error.lower():
            logger.info_success("Key was already in the agent.")
            return True
        return False


def select_ssh_key() -> Optional[str]:
    """
    Interactive selection of an SSH key from the available keys.
    
    Returns:
        Optional[str]: Path to the selected SSH key, or None if selection was cancelled.
    """
    start_ssh_agent()
    
    # Find available SSH keys
    candidates = find_ssh_keys()
    if not candidates:
        logger.warning("No key files found in ~/.ssh")
        return None
    
    # Display available keys to the user
    logger.info_highlight("Available SSH keys:")
    for idx, path in enumerate(candidates, 1):
        logger.info(f"{Colors.BOLD}{idx}{Colors.RESET}) {os.path.basename(path)}")
    
    # Check for a cached key selection
    cached_key_path = os.path.expanduser("~/.ssh/last_selected_key")
    if os.path.exists(cached_key_path):
        try:
            with open(cached_key_path, "r") as f:
                cached_key = f.read().strip()
                if os.path.exists(cached_key):
                    logger.info(f"{Colors.CYAN}Previously selected key: {os.path.basename(cached_key)}{Colors.RESET}")
                    use_cached = input(f"Use this key? (Y/n): ").strip().lower()
                    if use_cached == "" or use_cached == "y":
                        if not check_key_in_agent(cached_key):
                            add_key_to_agent(cached_key)
                        return cached_key
        except Exception:
            # Ignore errors with cached key, just continue
            pass
    
    # Let user select a key
    while True:
        choice = input(f"Select key [{Colors.YELLOW}1{Colors.RESET}-{Colors.YELLOW}{len(candidates)}{Colors.RESET}] or blank to cancel:\n> ").strip()
        if choice == "":
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            selected_key = candidates[int(choice) - 1]
            
            # Save the selected key for future runs
            try:
                with open(cached_key_path, "w") as f:
                    f.write(selected_key)
                os.chmod(cached_key_path, 0o600)  # Secure permissions
            except Exception:
                # Continue even if we can't save the selection
                pass
            
            # Add the key to the agent if needed
            if not check_key_in_agent(selected_key):
                add_key_to_agent(selected_key)
            
            return selected_key
        logger.warning("Invalid selection, try again.")


def get_ssh_command_base(key_path: Optional[str] = None) -> List[str]:
    """
    Build the base SSH command with appropriate options.
    
    Args:
        key_path (Optional[str]): Path to the SSH key file.
        
    Returns:
        List[str]: Base SSH command with options.
    """
    cmd = ["ssh"]
    
    # Always use the SSH agent if available
    if "SSH_AUTH_SOCK" in os.environ:
        cmd.extend(["-o", f"IdentityAgent={os.environ['SSH_AUTH_SOCK']}"])
    
    if key_path:
        cmd.extend(["-i", key_path])
    
    # Add additional options for non-interactive use
    cmd.extend([
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "IdentitiesOnly=no"  # Allow to use identities from ssh-agent
    ])
    
    return cmd 