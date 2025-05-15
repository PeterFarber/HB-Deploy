"""
Logging module.
Provides a centralized logging system for the application.
"""

import os
import sys
import json
import logging
import logging.handlers
import re
from typing import Dict, Any, Optional

# Remove the direct import of settings
# from src.config.settings import settings
from src.ui.colors import Colors


# Default configuration values for logging
DEFAULT_LOG_CONFIG = {
    "level": "INFO",
    "file": None,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
}


# Define custom log levels if needed
VERBOSE = 15  # Between DEBUG and INFO
logging.addLevelName(VERBOSE, "VERBOSE")


class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to log levels in console output."""
    
    COLORS = {
        'DEBUG': Colors.BLUE,
        'VERBOSE': Colors.CYAN,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.BOLD + Colors.RED
    }
    
    def __init__(self, fmt=None, datefmt=None, style='%'):
        """Initialize with standard format and simplified formats for console output."""
        super().__init__(fmt, datefmt, style)
        # Keep the full format for logging to file
        self.full_fmt = fmt
        # Create a simple format without timestamp and logger name for INFO level
        self.info_fmt = "%(message)s"
        # Create a format with just level name and message for non-INFO levels
        self.other_fmt = "%(levelname)s - %(message)s"
        
        # Create formatters
        self.info_formatter = logging.Formatter(self.info_fmt, datefmt, style)
        self.other_formatter = logging.Formatter(self.other_fmt, datefmt, style)
    
    def format(self, record):
        """
        Format the log record with simplified output for all levels in console.
        Always strips timestamp and logger name, keeps level name for non-INFO.
        """
        # Add colors to level name
        original_levelname = record.levelname
        if original_levelname in self.COLORS:
            record.levelname = f"{self.COLORS[original_levelname]}{original_levelname}{Colors.RESET}"
        
        # For INFO level, use format with just the message
        if record.levelno == logging.INFO:
            return self.info_formatter.format(record)
        
        # For other levels, use format with colored level name and message
        return self.other_formatter.format(record)


class ColorStripper(logging.Formatter):
    """Formatter that strips ANSI color codes from log messages."""
    
    def __init__(self, fmt=None, datefmt=None, style='%'):
        super().__init__(fmt, datefmt, style)
        # Regex to match ANSI escape sequences
        self.ansi_regex = re.compile(r'\x1b\[[0-9;]*m')
    
    def format(self, record):
        """Format the record and strip any color codes from the message."""
        # Format the record first
        formatted = super().format(record)
        # Strip ANSI color codes
        return self.ansi_regex.sub('', formatted)


class StructuredLogRecord(logging.LogRecord):
    """Custom LogRecord that supports structured logging."""
    
    def getMessage(self) -> str:
        """
        Format the log message with additional structured data.
        
        Returns:
            str: The formatted log message
        """
        msg = super().getMessage()
        if hasattr(self, 'structured_data') and self.structured_data:
            try:
                structured_part = json.dumps(self.structured_data)
                return f"{msg} {structured_part}"
            except Exception:
                return msg
        return msg


class StructuredLogger(logging.Logger):
    """Logger subclass that supports structured logging."""
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, 
                  func=None, extra=None, sinfo=None, **kwargs):
        """
        Create a custom LogRecord with structured data support.
        """
        structured_data = kwargs.pop('structured_data', None)
        
        # Create the standard log record
        record = super().makeRecord(name, level, fn, lno, msg, args, exc_info, 
                                   func, extra, sinfo)
        
        # Add structured data if provided
        if structured_data:
            record.structured_data = structured_data
        
        return record
    
    def verbose(self, msg, *args, **kwargs):
        """
        Log a message with VERBOSE level.
        """
        if self.isEnabledFor(VERBOSE):
            self._log(VERBOSE, msg, args, **kwargs)
    
    # Colored logging methods
    def info_success(self, msg, *args, **kwargs):
        """Log a success message with green color"""
        colored_msg = f"{Colors.GREEN}{msg}{Colors.RESET}"
        self.info(colored_msg, *args, **kwargs)
    
    def info_highlight(self, msg, *args, **kwargs):
        """Log a highlighted info message with bold formatting"""
        colored_msg = f"{Colors.BOLD}{msg}{Colors.RESET}"
        self.info(colored_msg, *args, **kwargs)
    
    def info_action(self, msg, *args, **kwargs):
        """Log an action message with blue color"""
        colored_msg = f"{Colors.BLUE}{msg}{Colors.RESET}"
        self.info(colored_msg, *args, **kwargs)
    
    def warning_highlight(self, msg, *args, **kwargs):
        """Log a warning message with yellow color and bold formatting"""
        colored_msg = f"{Colors.BOLD}{Colors.YELLOW}{msg}{Colors.RESET}"
        self.warning(colored_msg, *args, **kwargs)
    
    def error_highlight(self, msg, *args, **kwargs):
        """Log an error message with red color and bold formatting"""
        colored_msg = f"{Colors.BOLD}{Colors.RED}{msg}{Colors.RESET}"
        self.error(colored_msg, *args, **kwargs)


def get_config_value(section, key, default=None):
    """
    Get a configuration value safely without circular imports.
    
    Args:
        section: The configuration section
        key: The configuration key
        default: The default value if the key doesn't exist
        
    Returns:
        The configuration value
    """
    # Use DEFAULT_LOG_CONFIG if the section is "logging" to avoid import if possible
    if section == "logging" and key in DEFAULT_LOG_CONFIG:
        try:
            # Lazy import to avoid circular dependencies
            from src.config.settings import settings
            return settings.get(section, key, DEFAULT_LOG_CONFIG[key])
        except (ImportError, AttributeError):
            # Fall back to default if settings is not available
            return DEFAULT_LOG_CONFIG.get(key, default)
    else:
        # For non-logging configs, try to import settings
        try:
            from src.config.settings import settings
            return settings.get(section, key, default)
        except (ImportError, AttributeError):
            return default


def setup_logging(
    name: str = "hb",
    log_level: Optional[str] = None,
    log_file: Optional[str] = None
) -> StructuredLogger:
    """
    Set up the logging system.
    
    Args:
        name: The logger name
        log_level: The log level (overrides settings)
        log_file: The log file path (overrides settings)
        
    Returns:
        Logger: The configured logger
    """
    # Register the custom logger class
    logging.setLoggerClass(StructuredLogger)
    
    # Create the logger
    logger = logging.getLogger(name)
    
    # Clear any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Get log level from settings if not specified
    if log_level is None:
        log_level = get_config_value("logging", "level", "INFO")
    
    # Set the log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Create formatters
    log_format = get_config_value("logging", "format", 
                            "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    date_format = get_config_value("logging", "date_format", "%Y-%m-%d %H:%M:%S")
    
    # Use colored formatter for console
    colored_formatter = ColoredFormatter(log_format, date_format)
    console_handler.setFormatter(colored_formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # If a log file is specified or in settings, add a file handler
    log_file = log_file or get_config_value("logging", "file")
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Use a rotating file handler to prevent the log file from growing too large
        max_size = get_config_value("logging", "max_file_size", 10 * 1024 * 1024)  # 10MB
        backup_count = get_config_value("logging", "backup_count", 5)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=max_size, backupCount=backup_count
        )
        file_handler.setLevel(level)
        
        # Use color stripper formatter for files to remove ANSI color codes
        file_formatter = ColorStripper(log_format, date_format)
        file_handler.setFormatter(file_formatter)
        
        logger.addHandler(file_handler)
    
    return logger


# Create a default logger
logger = setup_logging() 