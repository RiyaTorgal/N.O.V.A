import psutil
import platform
import datetime
from typing import List, Dict, Optional, Any
import os
import socket
import json
from pathlib import Path
import time

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
        "WARNING": "\033[93m", # Yellow
        "SUCCESS": "\033[96m", # Cyan
        "CRITICAL": "\033[95m" # Purple
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
        
        :param level: Log level (INFO, DEBUG, ERROR, WARNING, SUCCESS, CRITICAL)
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
        
    def success(self, source: str, message: str) -> None:
        """Log a SUCCESS level message"""
        self.log("SUCCESS", source, message)
        
    def critical(self, source: str, message: str) -> None:
        """Log a CRITICAL level message"""
        self.log("CRITICAL", source, message)
    
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
    
    def display_logs(self, count: int = 6, exclude_sources: List[str] = None) -> None:
        """
        Display the most recent logs with formatting, optionally excluding specific sources
        
        :param count: Number of logs to display
        :param exclude_sources: List of source names to exclude from display
        """
        if exclude_sources is None:
            exclude_sources = []
            
        # Filter out logs from excluded sources
        filtered_logs = [log for log in self.logs if log["source"] not in exclude_sources]
        
        # Get the most recent logs after filtering
        recent_logs = filtered_logs[-count:] if filtered_logs else []
        
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
    
    # def export_logs(self, export_file: Optional[str] = None) -> str:
    #     """
    #     Export all logs to a file
        
    #     :param export_file: File to export to (defaults to timestamped file)
    #     :return: Path to the exported file
    #     """
    #     if export_file is None:
    #         timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    #         export_file = f"nova_logs_export_{timestamp}.txt"
            
    #     try:
    #         with open(export_file, "w", encoding="utf-8") as f:
    #             f.write(f"# NOVA Assistant Logs - Exported on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    #             f.write("# Total logs: {}\n".format(len(self.logs)))
    #             f.write("#" + "-" * 80 + "\n\n")
                
    #             for log in self.logs:
    #                 log_str = f"{log['timestamp']} - {log['source']} - {log['level']} - {log['message']}"
    #                 f.write(f"{log_str}\n")
                    
    #         return export_file
    #     except Exception as e:
    #         print(f"\033[91mFailed to export logs: {e}{self.RESET}")
    #         return ""


class SystemMonitor:
    def __init__(self, log_to_console=True, log_to_file=True):
        """Initialize SystemMonitor with optional logger"""
        self.logger = Logger(log_to_console=log_to_console, log_to_file=log_to_file)
        self.start_time = datetime.datetime.now()
        self.initial_ram = self.get_ram_usage()
        self.health_check_interval = 300  # 5 minutes between health checks
        self.last_health_check = time.time()
        self.connection_status = False
        
    def check_internet_connection(self, test_url: str = "https://www.google.com", timeout: int = 3) -> bool:
        """
        Check if internet connection is available by trying to connect to a URL.
        
        Args:
            test_url: URL to test connection with
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if connection is available, False otherwise
        """
        try:
            import urllib.request
            import urllib.error
            urllib.request.urlopen(test_url, timeout=timeout)
            if not self.connection_status:
                self.connection_status = True
                self.logger.success("SystemMonitor", "Internet connection available")
            return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError) as e:
            if self.connection_status:
                self.connection_status = False
                self.logger.warning("SystemMonitor", f"Internet connection unavailable: {str(e)}")
            return False
        except Exception as e:
            self.logger.error("SystemMonitor", f"Error checking internet connection: {str(e)}")
            return False
            
    def check_required_services(self) -> Dict[str, bool]:
        """
        Check if required services/modules are available.
        
        Returns:
            Dict[str, bool]: Status of required services
        """
        services = {
            "speech_recognition": False,
            "pyttsx3": False,
            "psutil": False,
            "database": False,
            "gemini": False
        }
        
        # Check speech recognition
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            services["speech_recognition"] = True
            self.logger.debug("SystemMonitor", "Speech recognition module available")
        except (ImportError, Exception) as e:
            self.logger.warning("SystemMonitor", f"Speech recognition not available: {str(e)}")
            
        # Check text-to-speech
        try:
            import pyttsx3
            engine = pyttsx3.init()
            services["pyttsx3"] = True
            self.logger.debug("SystemMonitor", "Text-to-speech module available")
        except (ImportError, Exception) as e:
            self.logger.warning("SystemMonitor", f"Text-to-speech not available: {str(e)}")
            
        # Check psutil
        try:
            import psutil
            services["psutil"] = True
            self.logger.debug("SystemMonitor", "System monitoring available")
        except ImportError:
            self.logger.warning("SystemMonitor", "System monitoring not available")
            
        # Check database connection
        try:
            import mysql.connector
            services["database"] = True
            self.logger.debug("SystemMonitor", "Database connectivity available")
        except ImportError:
            self.logger.warning("SystemMonitor", "Database connectivity not available")
            
        # Check Gemini API
        if os.environ.get("GEMINI"):
            services["gemini"] = True
            self.logger.debug("SystemMonitor", "Gemini API key available")
        else:
            self.logger.warning("SystemMonitor", "Gemini API key not available")
            
        return services
    
    def check_input_methods(self) -> Dict[str, bool]:
        """
        Check which input methods are available.
        
        Returns:
            Dict[str, bool]: Available input methods
        """
        methods = {
            "keyboard": True,  # Keyboard is assumed to be always available
            "microphone": False
        }
        
        # Check microphone availability
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            methods["microphone"] = True
            self.logger.success("SystemMonitor", "Microphone is available")
        except (ImportError, AttributeError, TypeError, ValueError) as e:
            self.logger.warning("SystemMonitor", f"Microphone not available: {str(e)}")
            
        return methods

    def get_ram_usage(self) -> float:
        """
        Get current RAM usage.
        
        :return: RAM usage in GB
        """
        pid = os.getpid()
        py = psutil.Process(pid)
        return py.memory_info()[0] / 2. ** 30
    
    def get_system_info(self) -> Dict[str, str]:
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
    
    def check_application_health(self) -> Dict[str, Any]:
        """
        Perform a health check of the application.
        
        Returns:
            Dict: Application health metrics
        """
        current_time = time.time()
        
        # Only perform a full health check if enough time has passed
        if current_time - self.last_health_check < self.health_check_interval:
            return {"status": "skipped", "message": "Health check interval not reached"}
            
        self.last_health_check = current_time
        
        # Get uptime in hours
        uptime = (datetime.datetime.now() - self.start_time).total_seconds() / 3600
        
        # Get memory usage delta since start
        current_ram = self.get_ram_usage()
        ram_delta = current_ram - self.initial_ram
        
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.5)
        
        # Check internet connection
        internet_available = self.check_internet_connection()
        
        # Check disk space
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Collect health metrics
        health = {
            "status": "healthy" if internet_available and disk_percent < 90 and cpu_percent < 80 else "degraded",
            "uptime_hours": round(uptime, 2),
            "ram_usage_gb": round(current_ram, 3),
            "ram_delta_gb": round(ram_delta, 3),
            "cpu_percent": cpu_percent,
            "disk_percent": disk_percent,
            "internet_connection": internet_available,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Log health status
        if health["status"] == "healthy":
            self.logger.info("SystemHealth", f"Application healthy: Uptime {health['uptime_hours']}h, RAM {health['ram_usage_gb']}GB")
        else:
            self.logger.warning("SystemHealth", f"Application degraded: RAM {health['ram_usage_gb']}GB, CPU {health['cpu_percent']}%, Internet: {health['internet_connection']}")
            
        return health
    
    def log_application_start(self) -> None:
        """Log application startup information"""
        self.logger.success("Application", "NOVA Assistant starting up")
        
        # Log system information
        sys_info = self.get_system_info()
        for key, value in sys_info.items():
            self.logger.info("System", f"{key}: {value}")
            
        # Check internet connection
        internet = self.check_internet_connection()
        self.logger.info("Network", f"Internet connection: {'Available' if internet else 'Unavailable'}")
        
        # Check required services
        services = self.check_required_services()
        for service, available in services.items():
            status = "Available" if available else "Unavailable"
            self.logger.info("Services", f"{service}: {status}")
            
        # Check input methods
        input_methods = self.check_input_methods()
        for method, available in input_methods.items():
            status = "Available" if available else "Unavailable"
            self.logger.info("InputMethods", f"{method}: {status}")
            
        self.logger.success("Application", "Initialization complete")
    
    def log_input_method_selection(self, method: str) -> None:
        """Log input method selection"""
        self.logger.info("UserInteraction", f"Input method selected: {method}")
    
    def display_system_overview(self) -> None:
        """
        Display a comprehensive system overview.
        """
        # System Information
        print("System Details:")
        system_info = self.get_system_info()
        for key, value in system_info.items():
            print(f"  {key}: {value}")
    
    def display_ram_usage(self) -> None:
        """
        Display RAM used.
        """
        # RAM Usage
        ram_usage = self.get_ram_usage()
        print(f"RAM Usage: {ram_usage:.2f} GB")

    def display_date_and_time(self) -> None:
        """
        Display current date and time.
        """
        # Current Date and Time
        current_time = datetime.datetime.now()
        print(f"Current Date: {current_time.strftime('%Y-%m-%d')}")
        print(f"Current Time: {current_time.strftime('%H:%M:%S')}")