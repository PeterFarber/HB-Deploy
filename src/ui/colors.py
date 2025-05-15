"""
ANSI color codes for terminal output.
"""

class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    
    @classmethod
    def colorize(cls, text, color):
        """
        Wrap text in the specified color code.
        
        Args:
            text (str): The text to colorize
            color (str): The color code to use (one of the class constants)
        
        Returns:
            str: The colorized text
        """
        return f"{color}{text}{cls.RESET}"
    
    @classmethod
    def bold(cls, text):
        """Make text bold."""
        return cls.colorize(text, cls.BOLD)
    
    @classmethod
    def underline(cls, text):
        """Make text underlined."""
        return cls.colorize(text, cls.UNDERLINE)
    
    @classmethod
    def red(cls, text):
        """Make text red."""
        return cls.colorize(text, cls.RED)
    
    @classmethod
    def green(cls, text):
        """Make text green."""
        return cls.colorize(text, cls.GREEN)
    
    @classmethod
    def yellow(cls, text):
        """Make text yellow."""
        return cls.colorize(text, cls.YELLOW)
    
    @classmethod
    def blue(cls, text):
        """Make text blue."""
        return cls.colorize(text, cls.BLUE)
    
    @classmethod
    def magenta(cls, text):
        """Make text magenta."""
        return cls.colorize(text, cls.MAGENTA)
    
    @classmethod
    def cyan(cls, text):
        """Make text cyan."""
        return cls.colorize(text, cls.CYAN) 