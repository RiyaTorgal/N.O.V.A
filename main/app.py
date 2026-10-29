"""
Main application class for Nova Assistant.
Provides the core functionality and coordination of all components.
"""

from datetime import datetime
import os
import sys
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.assistant import Assistant
from src.input.text_handler import TypedInputHandler
from src.input.voice_handler import VoiceAssistant
from src.services.weather import WeatherAPI
from src.utils.command_history import DatabaseCommandHistory
from src.dB.database import Database
from src.stats.system_monitor import SystemMonitor
from src.stats.system_monitor import Logger
from src.stats.connection_monitor import ConnectionMonitor
from main.command_handler import CommandHandlers
from main.llm_router import LLMRouter
from main.ui import UIManager
from main.signal_manager import SignalManager

# Load environment variables
dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'config', '.env')
load_dotenv(dotenv_path)

EXIT_WORDS = {"exit", "quit", "bye"}


class NovaAssistant:
    """Main application class for Nova Assistant."""

    def __init__(self):
        """Initialize the Nova Assistant application."""
        self.console = Console()

        # Load API keys and initialize components
        self.api_key = os.environ.get("OPEN_WEATHER_API_KEY")

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

        # Tool implementations + the local-LLM router that calls them
        self.cmd_handlers = CommandHandlers(self)
        self.router = LLMRouter(self.cmd_handlers)

        # Set up signal handler
        self.signal_manager = SignalManager(self)
        self.signal_manager.setup_signal_handlers()

        # Log system information on startup
        self._log_system_info()

        self.initialized = False

    def _log_system_info(self, display=True):
        """Log system information during startup."""
        system_info = self.stats.get_system_info()
        for key, value in system_info.items():
            self.logger.info("system", f"{key}: {value}")

        connection_status = self.connection_monitor.check_internet_connection()
        self.logger.info("network", f"Internet connection: {'Available' if connection_status else 'Unavailable'}")

        input_devices = self.connection_monitor.check_input_device_availability()
        for device, available in input_devices.items():
            self.logger.info("devices", f"{device.capitalize()} available: {available}")

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
        Send a user command to the LLM router and record the result.

        Args:
            command: User command string

        Returns:
            str: Response to speak, or None for empty input
        """
        if not command or not command.strip():
            return None
        command = command.strip()

        # Record the command in history before processing
        try:
            context = {"execution_time": datetime.now().isoformat()}
            self.command_history.add_command(command, "initiated", context)
        except Exception as e:
            self.console.print(f"[red]Failed to record command: {e}[/red]")

        response = self.router.route(command)
        if response:
            self.save_response(command, response, "completed")
            return response

        # Router returned nothing: the local model is down or gave no answer
        response = "Sorry, I couldn't process that. Is the local model running?"
        self.console.print(f"[red]{response}[/red]")
        self.save_response(command, response, "failed")
        return response

    def save_response(self, command, response, status):
        """Save response and update command status."""
        try:
            self.command_history.update_command_status(command, status)
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
        self.command_history.start_recording()
        self.initialize_database()
        self.command_history.connect()

        # Display welcome screen
        self.ui.display_welcome(self.stats, self.logger)
        self.voice.greet()  # pre-rendered wav (assets/greeting.wav); no wait on XTTS

        # Let user choose input method
        input_method = self.choose_input_method()

        while True:
            try:
                self.ui.display_command_prompt()

                command = input_method()
                # The voice handler returns "Error: ..." text when it can't
                # understand the audio; don't treat that as a command.
                if not command or command.strip().lower().startswith("error:"):
                    continue
                command = command.strip()

                if command.lower() in EXIT_WORDS:
                    self.signal_manager.cleanup()
                    break

                self.console.print(f"[dim]Command:[/dim] [bold green]{command}[/bold green]")
                self.ui.show_processing_indicator()

                response = self.process_command(command)
                if response:
                    self.voice.speak(response)

            except Exception as e:
                self.console.print(f"\n[red]Error: {str(e)}[/red]")
                self.voice.speak("I encountered an error. Please try again.")


def main():
    """Main entry point for Nova Assistant."""
    try:
        assistant = NovaAssistant()
        assistant.run()
    except Exception as e:
        console = Console()
        console.print(f"\n[bold red]Fatal error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()