"""
Utility helper functions module.
Contains various utility functions used throughout the application.
"""

import random
import string
import time
import sys
import requests
from typing import Optional

from src.utils.logger import logger


def generate_random_string(length: int = 64) -> str:
    """
    Generate a random alphanumeric string.
    
    Args:
        length (int): Length of the string to generate.
        
    Returns:
        str: Random alphanumeric string.
    """
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def wait_for_router(router_ip: str, max_retries: int = 30, retry_delay: int = 1) -> bool:
    """
    Wait for router endpoint to become available.
    
    Args:
        router_ip (str): IP address of the router.
        max_retries (int): Maximum number of retry attempts.
        retry_delay (int): Delay between retry attempts (in seconds).
        
    Returns:
        bool: True if router became available, False if timed out.
    """
    endpoint = f"http://{router_ip}:80/~meta@1.0/info/address"
    logger.info(f"Waiting for router at {endpoint}...")
    
    for i in range(max_retries):
        try:
            response = requests.get(endpoint, timeout=2)
            if response.status_code == 200 and response.text:
                logger.info_success("Router is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        time.sleep(retry_delay)
        # Still use print for progress indicator dots to avoid cluttering logs
        sys.stdout.write(".")
        sys.stdout.flush()
    
    logger.error("Timed out waiting for router")
    return False 