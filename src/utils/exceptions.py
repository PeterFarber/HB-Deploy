"""
Custom exceptions module.
Defines custom exception classes for the application.
"""


class HBDeployError(Exception):
    """Base exception for all application errors."""
    pass


class ConfigurationError(HBDeployError):
    """Exception raised for configuration errors."""
    pass


class SSHError(HBDeployError):
    """Base exception for SSH-related errors."""
    pass


class SSHConnectionError(SSHError):
    """Exception raised when an SSH connection fails."""
    
    def __init__(self, server=None, message=None, cause=None):
        self.server = server
        self.cause = cause
        msg = f"Failed to connect to server"
        if server:
            msg += f" {server['name']} ({server['ip']})"
        if message:
            msg += f": {message}"
        if cause:
            msg += f" - {str(cause)}"
        super().__init__(msg)


class SSHCommandError(SSHError):
    """Exception raised when an SSH command fails."""
    
    def __init__(self, command=None, server=None, return_code=None, output=None):
        self.command = command
        self.server = server
        self.return_code = return_code
        self.output = output
        
        msg = "SSH command failed"
        if server:
            msg += f" on {server['name']} ({server['ip']})"
        if command:
            msg += f": {command}"
        if return_code is not None:
            msg += f" (exit code: {return_code})"
        super().__init__(msg)


class SSHKeyError(SSHError):
    """Exception raised for SSH key-related errors."""
    pass


class RouterError(HBDeployError):
    """Exception raised for router-related errors."""
    
    def __init__(self, router=None, message=None):
        self.router = router
        msg = "Router error"
        if router:
            msg += f" on {router['name']} ({router['ip']})"
        if message:
            msg += f": {message}"
        super().__init__(msg)


class TimeoutError(HBDeployError):
    """Exception raised when an operation times out."""
    
    def __init__(self, operation=None, timeout=None):
        self.operation = operation
        self.timeout = timeout
        msg = "Operation timed out"
        if operation:
            msg += f": {operation}"
        if timeout:
            msg += f" after {timeout} seconds"
        super().__init__(msg)


class BuildError(HBDeployError):
    """Exception raised for build-related errors."""
    
    def __init__(self, server=None, message=None):
        self.server = server
        msg = "Build error"
        if server:
            msg += f" on {server['name']} ({server['ip']})"
        if message:
            msg += f": {message}"
        super().__init__(msg)


class MaxRetriesExceededError(HBDeployError):
    """Exception raised when max retries are exceeded."""
    
    def __init__(self, operation=None, max_retries=None):
        self.operation = operation
        self.max_retries = max_retries
        msg = "Max retries exceeded"
        if operation:
            msg += f" for operation: {operation}"
        if max_retries:
            msg += f" (max: {max_retries})"
        super().__init__(msg) 