import psutil
import platform
import datetime
from typing import List, Dict, Optional
import os

class Logger:
    """
    Enhanced Logger class for N.O.V.A assistant to display formatted, colorful log messages
    similar to the assistant's UI display
    """
    
    # ANSI color codes for terminal output
    LOG_LEVELS = {
        "INFO": "\033[94m",    # Blue
        "DEBUG": "\033[92m",   # Green
        "ERROR": "\033[91m",   # Red
        "WARNING": "\033[93m"  # Yellow
    }
    RESET = "\033[0m"
    
    def __init__(self, log_to_console=True, log_to_file=True, log_file="nova_logs.txt", max_logs=100):
        """
        Initialize the logger with configuration options
        
        :param log_to_console: Whether to output logs to console
        :param log_to_file: Whether to save logs to file
        :param log_file: Path to the log file
        :param max_logs: Maximum number of logs to keep in memory
        """
        self.log_to_console = log_to_console
        self.log_to_file = log_to_file
        self.log_file = log_file
        self.max_logs = max_logs
        self.logs: List[Dict] = []
        
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Initialize log file with header if it doesn't exist
        if log_to_file and not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write(f"# NOVA Assistant Logs - Created on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("# Timestamp - Source - Level - Message\n")
                f.write("#" + "-" * 80 + "\n\n")
    
    def log(self, level: str, source: str, message: str) -> None:
        """
        Add a log entry with timestamp, level, source and message
        
        :param level: Log level (INFO, DEBUG, ERROR, WARNING)
        :param source: Source of the log (e.g., 'root', 'system', etc.)
        :param message: The log message
        """
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Create log entry as dictionary for flexible access later
        log_entry = {
            "timestamp": timestamp,
            "source": source,
            "level": level,
            "message": message,
        }
        
        # Add to in-memory logs
        self.logs.append(log_entry)
        
        # Maintain max logs limit
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
        
        # Format log entry as string
        log_str = f"{timestamp} - {source} - {level} - {message}"
        
        # Output to console with color
        if self.log_to_console:
            color = self.LOG_LEVELS.get(level, "")
            print(f"{color}{log_str}{self.RESET}")
        
        # Write to file
        if self.log_to_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(f"{log_str}\n")
            except Exception as e:
                # If we can't write to file, at least print the error
                if self.log_to_console:
                    print(f"\033[91mFailed to write to log file: {e}{self.RESET}")
    
    def info(self, source: str, message: str) -> None:
        """Log an INFO level message"""
        self.log("INFO", source, message)
    
    def debug(self, source: str, message: str) -> None:
        """Log a DEBUG level message"""
        self.log("DEBUG", source, message)
    
    def error(self, source: str, message: str) -> None:
        """Log an ERROR level message"""
        self.log("ERROR", source, message)
    
    def warning(self, source: str, message: str) -> None:
        """Log a WARNING level message"""
        self.log("WARNING", source, message)
    
    def get_recent_logs(self, count: int = 6) -> List[Dict]:
        """
        Get the most recent logs
        
        :param count: Number of recent logs to retrieve
        :return: List of log dictionaries
        """
        return self.logs[-count:] if self.logs else []
    
    def get_logs_by_level(self, level: str, count: Optional[int] = None) -> List[Dict]:
        """
        Get logs filtered by level
        
        :param level: Log level to filter by
        :param count: Optional limit on number of logs to return
        :return: List of filtered log dictionaries
        """
        filtered = [log for log in self.logs if log["level"] == level]
        if count is not None:
            return filtered[-count:]
        return filtered
    
    def get_logs_by_source(self, source: str, count: Optional[int] = None) -> List[Dict]:
        """
        Get logs filtered by source
        
        :param source: Source to filter by
        :param count: Optional limit on number of logs to return
        :return: List of filtered log dictionaries
        """
        filtered = [log for log in self.logs if log["source"] == source]
        if count is not None:
            return filtered[-count:]
        return filtered
    
    def display_logs(self, count: int = 6) -> None:
        """
        Display the most recent logs with formatting
        
        :param count: Number of logs to display
        """
        recent_logs = self.get_recent_logs(count)
        if not recent_logs:
            print("No logs available.")
            return
            
        for log in recent_logs:
            # Format with color
            color = self.LOG_LEVELS.get(log["level"], "")
            log_str = f"{log['timestamp']} - {log['source']} - {log['level']} - {log['message']}"
            print(f"{color}{log_str}{self.RESET}")
    
    def clear_logs(self) -> bool:
        """
        Clear all in-memory logs
        
        :return: True if successful
        """
        self.logs = []
        return True
    
    def export_logs(self, export_file: Optional[str] = None) -> str:
        """
        Export all logs to a file
        
        :param export_file: File to export to (defaults to timestamped file)
        :return: Path to the exported file
        """
        if export_file is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            export_file = f"nova_logs_export_{timestamp}.txt"
            
        try:
            with open(export_file, "w", encoding="utf-8") as f:
                f.write(f"# NOVA Assistant Logs - Exported on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("# Total logs: {}\n".format(len(self.logs)))
                f.write("#" + "-" * 80 + "\n\n")
                
                for log in self.logs:
                    log_str = f"{log['timestamp']} - {log['source']} - {log['level']} - {log['message']}"
                    f.write(f"{log_str}\n")
                    
            return export_file
        except Exception as e:
            print(f"\033[91mFailed to export logs: {e}{self.RESET}")
            return ""

class SystemMonitor:
    def get_ram_usage(self):
        """
        Get current RAM usage.
        
        :return: RAM usage in GB
        """
        # memory = psutil.virtual_memory()
        # return memory.used / (1024 * 1024 * 1024)  # Convert to GB
        pid = os.getpid()
        py = psutil.Process(pid)
        return py.memory_info()[0] / 2. ** 30
    
    def get_system_info(self):
        """
        Retrieve comprehensive system information.
        
        :return: Dictionary of system details
        """
        return {
            "OS": platform.system(),
            "OS Version": platform.release(),
            "Machine": platform.machine(),
            "Processor": platform.processor(),
            "Python Version": platform.python_version()
        }
    
    def display_system_overview(self):
        """
        Display a comprehensive system overview.
        """
        # System Information
        print("System Details:")
        system_info = self.get_system_info()
        for key, value in system_info.items():
            print(f"  {key}: {value}")
    
    def display_ram_usage(self):
        """
        Display a RAM used.
        """
        # RAM Usage
        ram_usage = self.get_ram_usage()
        print(f"RAM Usage: {ram_usage:.2f} GB")

    def display_date_and_time(self):
        """
        Display current date and time.
        """
        # Current Date and Time
        current_time = datetime.datetime.now()
        print(f"Current Date: {current_time.strftime('%Y-%m-%d')}")
        print(f"Current Time: {current_time.strftime('%H:%M:%S')}")