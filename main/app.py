"""
Main application class for Nova Assistant.
Provides the core functionality and coordination of all components.
"""

from datetime import datetime
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from src.core.assistant import Assistant
from src.input.text_handler import TypedInputHandler
from src.input.voice_handler import VoiceAssistant
from src.services.weather import WeatherAPI
from src.services.ai_implementation import GeminiSearch
from src.utils.command_history import DatabaseCommandHistory
from src.dB.database import Database
from src.stats.system_monitor import SystemMonitor
from src.stats.system_monitor import Logger
from src.stats.connection_monitor import ConnectionMonitor
from main.command_handler import CommandHandlers
from main.ui import UIManager
from main.signal_manager import SignalManager

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
load_dotenv(dotenv_path)

class NovaAssistant:
    """Main application class for Nova Assistant."""
    
    def __init__(self):
        """Initialize the Nova Assistant application."""
        # Initialize Rich console
        self.console = Console()
        
        # Load API keys and initialize components
        self.api_key = os.environ.get("API_KEY")
        self.gemini_api_key = os.environ.get("GEMINI")
        
        # Initialize core components
        self.assistant = Assistant()
        self.stats = SystemMonitor()
        self.typeHandler = TypedInputHandler()
        self.voice = VoiceAssistant()
        self.weather = WeatherAPI(self.api_key)
        self.logger = Logger(log_to_console=True, log_to_file=False, log_file='logs.txt')
        self.connection_monitor = ConnectionMonitor()
        self.input_mode = "TEXT"  # Default input mode
        self.speech_enabled = False
        
        # Initialize UI manager
        self.ui = UIManager()
        
        # Initialize Gemini AI search if API key is available
        try:
            if self.gemini_api_key:
                self.gemini_search = GeminiSearch(self.gemini_api_key)
            else:
                self.console.print("[yellow]Warning: Gemini API key not found. AI search functionality will be disabled.[/yellow]")
                self.gemini_search = None
        except Exception as e:
            self.console.print(f"[red]Error initializing Gemini search: {e}[/red]")
            self.gemini_search = None
            
        # Set up database connection
        self.db_config = {
            'host': os.environ.get("DB_HOST", "localhost"),
            'user': os.environ.get("DB_USER", "root"),
            'password': os.environ.get("DB_PASSWORD", ""),
            'database': os.environ.get("DB_DATABASE", "nova"),
            'port': int(os.environ.get("DB_PORT", "3306"))
        }
        self.db = Database()
        self.command_history = DatabaseCommandHistory(self.db_config, self.db)
        
        # Initialize command handlers
        self.cmd_handlers = CommandHandlers(self)
        
        # Set up signal handler
        self.signal_manager = SignalManager(self)
        self.signal_manager.setup_signal_handlers()
        
        # Log system information on startup
        self._log_system_info()
        
        self.initialized = False

    def _log_system_info(self, display=True):
        """
        Log system information during startup.
        
        Args:
            display: Whether to display the information to console
        """
        system_info = self.stats.get_system_info()
        for key, value in system_info.items():
            self.logger.info("system", f"{key}: {value}")
        
        # Check and log connection status
        connection_status = self.connection_monitor.check_internet_connection()
        self.logger.info("network", f"Internet connection: {'Available' if connection_status else 'Unavailable'}")
        
        # Check and log available input devices
        input_devices = self.connection_monitor.check_input_device_availability()
        for device, available in input_devices.items():
            self.logger.info("devices", f"{device.capitalize()} available: {available}")
        
        # Check and log text-to-speech availability
        tts_available = self.connection_monitor.check_text_to_speech_availability()
        self.logger.info("devices", f"Text-to-speech available: {tts_available}")

    def initialize_database(self):
        """
        Initialize the database schema.
        
        Returns:
            bool: True if successful, False otherwise
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Initializing database...[/bold blue]"),
            console=self.console
        ) as progress:
            task = progress.add_task("", total=1)
            success = self.db.initialize_database()
            progress.update(task, advance=1)
            
        if success:
            self.console.print("[green]Database initialization complete![/green]")
        else:
            self.console.print("[red]Failed to initialize database.[/red]")
            
        return success

    def process_command(self, command):
        """
        Process user commands and return appropriate response.
        
        Args:
            command: User command string
            
        Returns:
            str: Response to the command or None
        """
        if not command:
            return None
            
        command = command.lower().strip()
        
        # Handle exit commands first
        if command in ['exit', 'quit', 'bye']:
            self.signal_manager.cleanup()
            sys.exit(0)
        
        # Record the command in history before processing
        try:
            context = {"execution_time": datetime.now().isoformat()}
            self.command_history.add_command(command, "initiated", context)
        except Exception as e:
            self.console.print(f"[red]Failed to record command: {e}[/red]")
            
        # Map commands to their handlers
        command_map = {
            "help": self.cmd_handlers.handle_help,
            "thanks": self.cmd_handlers.handle_thanks,
            "thank you": self.cmd_handlers.handle_thanks,
            "history": self.cmd_handlers.handle_history,
            "history start": self.cmd_handlers.handle_history_start,
            "history stop": self.cmd_handlers.handle_history_stop,
            "clear history": self.cmd_handlers.handle_clear_history,
            "search": self.cmd_handlers.handle_search_history,
            "time": self.cmd_handlers.handle_time,
            "date": self.cmd_handlers.handle_date,
            "calculate": self.cmd_handlers.handle_calculation,
            "weather": self.cmd_handlers.handle_weather,
            "open": self.cmd_handlers.handle_open,
            "functions": self.cmd_handlers.handle_function_list,
            "ask": self.cmd_handlers.handle_ai_query,
            "define": self.cmd_handlers.handle_define,
            "status": self.cmd_handlers.handle_system_status,
            "connection": self.cmd_handlers.handle_connection_status,
        }
        
        # Check for exact command matches first
        if command in command_map:
            response = command_map[command](command)
            self.save_response(command, response, "completed")
            return response
            
        # Check for commands that start with a specific prefix
        for cmd_prefix in ["search ", "ask ", "define ", "calculate ", "weather ", "open "]:
            if command.startswith(cmd_prefix):
                handler_key = cmd_prefix.strip()
                response = command_map[handler_key](command)
                self.save_response(command, response, "completed")
                return response
        
        # Check if any command keyword is contained within the full command
        for cmd_key in command_map:
            if cmd_key in command and cmd_key not in ["ask", "define", "search", "calculate", "weather", "open"]:
                response = command_map[cmd_key](command)
                self.save_response(command, response, "completed")
                return response

        # Handle unrecognized commands
        self.console.print("[red]I'm sorry, I didn't understand that command.[/red]")
        self.console.print("Please say 'Nova help' to see available commands.")
        response = ("I'm sorry, I didn't understand that command. "
                  "Please say 'Nova help' to see available commands.")
        self.save_response(command, response, "failed")
        return response
    
    def save_response(self, command, response, status):
        """
        Save response and update command status.
        
        Args:
            command: The command that was executed
            response: The response to the command
            status: The execution status
        """
        try:
            # Update both status and response
            self.command_history.update_command_status(command, status)
            # Add new method to save response (to be implemented in command_history class)
            self.command_history.save_response(command, response)
        except Exception as e:
            self.console.print(f"[red]Failed to save response: {e}[/red]")
    
    def choose_input_method(self):
        """
        Allow the user to select input method.
        
        Returns:
            Function: The selected input method function
        """
        choice = self.ui.prompt_for_input_method()
            
        if choice.lower() == "type":
            return self.typeHandler.get_input
        else:
            return self.voice.listen

    def run(self):
        """Main loop for the assistant."""
        # Initialize database and command history
        self.cmd_handlers.handle_history_start("")
        self.initialize_database()
        self.command_history.connect()
        
        # Display welcome screen
        self.ui.display_welcome(self.stats, self.logger)
        self.voice.speak("Hello, I am Nova, your Python-Powered AI Assistant")
        
        # Let user choose input method
        input_method = self.choose_input_method()
        
        while True:
            try:
                # Display command prompt
                self.ui.display_command_prompt()
                
                # Get command using selected input method
                command = input_method()
                if command in ["exit", "quit", "bye"]:
                    self.signal_manager.cleanup()
                    break
                
                # Display the command
                self.console.print(f"[dim]Command:[/dim] [bold green]{command}[/bold green]")
                
                # Show processing indicator
                self.ui.show_processing_indicator()
                
                # Process the command
                response = self.process_command(command)
                
                if response:
                    # Speak the response using text-to-speech
                    self.voice.speak(response)
                    
            except Exception as e:
                self.console.print(f"\n[red]Error: {str(e)}[/red]")
                self.voice.speak("I encountered an error. Please try again.")

def main():
    """Main entry point for Nova Assistant."""
    try:
        # Show an initial splash screen
        console = Console()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]Starting Nova Assistant...[/bold blue]"),
            console=console
        ) as progress:
            task = progress.add_task("", total=100)
            # Simulate loading steps
            for i in range(100):
                progress.update(task, completed=i+1)
                # Small delay to show progress
                import time
                time.sleep(0.02)
                
        assistant = NovaAssistant()
        assistant.run()
    except Exception as e:
        console = Console()
        console.print(f"\n[bold red]Fatal error:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()