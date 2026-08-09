import time

class Logger:
    """Logger with the same levels and colors as Lua logger"""
    
    # Log levels
    SILLY = 0
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4
    
    # ANSI color codes (matching Lua logger)
    COLORS = {
        'SILLY': '\033[35m',  # Magenta
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',   # Green
        'WARN': '\033[33m',   # Yellow
        'ERROR': '\033[31m',  # Red
        'RESET': '\033[0m'
    }
    
    def __init__(self, level=DEBUG, log_file=None, enable_color_in_file=False, on_log=None):
        """
        Initialize logger.

        Args:
            level (int): Minimum log level to display
            log_file (str): Optional path to log file
            enable_color_in_file (bool): Whether to use color codes in file
            on_log (callable): Optional callback(level_name: str, message: str) invoked
                                on every logged line that passes the level filter, in
                                addition to the normal terminal/file output. Useful for
                                streaming logs into a UI. Called on whatever thread logs.
        """
        self.current_level = level
        self.log_file = None
        self.enable_color_in_file = enable_color_in_file
        self.on_log = on_log

        if log_file:
            try:
                self.log_file = open(log_file, 'a')
            except Exception as e:
                print(f"⚠️ Failed to open log file: {log_file} - {e}")

    def _log(self, level, level_name, message, use_color=False):
        """Internal log function"""
        if self.current_level <= level:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            line = f"{timestamp} [{level_name}] {message}"

            # Terminal output
            if use_color:
                color_code = self.COLORS.get(level_name, '')
                reset_code = self.COLORS['RESET']
                print(f"{color_code}{line}{reset_code}")
            else:
                print(line)

            # File output
            if self.log_file:
                if self.enable_color_in_file and use_color:
                    color_code = self.COLORS.get(level_name, '')
                    reset_code = self.COLORS['RESET']
                    self.log_file.write(f"{color_code}{line}{reset_code}\n")
                else:
                    self.log_file.write(f"{line}\n")
                self.log_file.flush()

            if self.on_log:
                self.on_log(level_name, message)
    
    # Plain log functions
    def silly(self, msg):
        self._log(self.SILLY, 'SILLY', msg, False)
    
    def debug(self, msg):
        self._log(self.DEBUG, 'DEBUG', msg, False)
    
    def info(self, msg):
        self._log(self.INFO, 'INFO', msg, False)
    
    def warn(self, msg):
        self._log(self.WARN, 'WARN', msg, False)
    
    def error(self, msg):
        self._log(self.ERROR, 'ERROR', msg, False)
    
    # Color log functions
    def color_silly(self, msg):
        self._log(self.SILLY, 'SILLY', msg, True)
    
    def color_debug(self, msg):
        self._log(self.DEBUG, 'DEBUG', msg, True)
    
    def color_info(self, msg):
        self._log(self.INFO, 'INFO', msg, True)
    
    def color_warn(self, msg):
        self._log(self.WARN, 'WARN', msg, True)
    
    def color_error(self, msg):
        self._log(self.ERROR, 'ERROR', msg, True)
    
    def set_level(self, level):
        """Set minimum log level"""
        self.current_level = level
    
    def close(self):
        """Close log file if open"""
        if self.log_file:
            self.log_file.close()


# Create global logger instance
logger = Logger(level=Logger.SILLY, log_file='/tmp/wingspan_python.log', enable_color_in_file=True)

# Helper function for backward compatibility
def log(message):
    """Simple log function for backward compatibility"""
    logger.color_info(message)