from datetime import datetime
from typing import Optional
import signal
import sys
import re
import os
from pathlib import Path
from dotenv import load_dotenv
# Rich library imports
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.live import Live
from rich.layout import Layout
from rich.prompt import Prompt
from rich import box
from rich.markdown import Markdown

from src.core.exceptions import AppOperationError, AssistantError, WeatherAPIError
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


dotenv_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
load_dotenv(dotenv_path)

class NovaAssistant:
    def __init__(self):
        # Initialize Rich console
        self.console = Console()
        self.layout = Layout()
        self.api_key = os.environ.get("API_KEY")
        self.assistant = Assistant()
        self.stats = SystemMonitor()
        self.typeHandler = TypedInputHandler()
        self.voice = VoiceAssistant()
        self.weather = WeatherAPI(self.api_key)
        self.gemini_api_key = os.environ.get("GEMINI")  # Make sure you have a GEMINI env variable
        self.logger = Logger(log_to_console=True, log_to_file=True, log_file="nova_logs.txt")
        self.connection_monitor = ConnectionMonitor()
        self.input_mode = "TEXT"  # Default input mode
        self.speech_enabled = False
        try:
            if self.gemini_api_key:
                self.gemini_search = GeminiSearch(self.gemini_api_key)
            else:
                self.console.print("[yellow]Warning: Gemini API key not found. AI search functionality will be disabled.[/yellow]")
                self.gemini_search = None
        except Exception as e:
            self.console.print(f"[red]Error initializing Gemini search: {e}[/red]")
            self.gemini_search = None
        self.commands = {
            "time": self._handle_time,
            "date": self._handle_date,
            "calculate": self._handle_calculation,
            "weather": self._handle_weather,
            "open": self._handle_open,
            "exit": self._handle_exit,
            "thanks": self._handle_thanks,
            "help": self._handle_help,
            "functions": self._handle_function_list,
            "history": self._handle_history,
            "search": self._handle_search_history,
            "clear history": self._handle_clear_history,
            "ask": self._handle_ai_query,
            "define": self._handle_define,
            "status": self._handle_system_status,
            "connection": self._handle_connection_status,
        }
        self.db_config = {
            'host': os.environ.get("DB_HOST", "localhost"),
            'user': os.environ.get("DB_USER", "root"),
            'password': os.environ.get("DB_PASSWORD", ""),
            'database': os.environ.get("DB_DATABASE", "nova"),
            'port': int(os.environ.get("DB_PORT", "3306"))
        }
        self.db = Database()
        self.command_history = DatabaseCommandHistory(self.db_config, self.db)
        self.initialized = False
        self.setup_signal_handlers()
        self._log_system_info()

    def _log_system_info(self, display=True):
        """Log system information during startup"""
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
        
    def _handle_system_status(self, _: str) -> str:
        """Handle system status check command"""
        # Get system information
        system_info = self.stats.get_system_info()
        ram_usage = self.stats.get_ram_usage()
        
        # Create a rich table for system status
        table = Table(title="System Status", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("RAM Usage", f"{ram_usage:.2f} GB")
        for key, value in system_info.items():
            table.add_row(key, str(value))
            
        # Render the table to string for voice output, but display rich version
        self.console.print(table)
        
        # Log that system status was checked
        self.logger.info("commands", "System status check performed")
        
        # Return simple text for voice output
        response = "System Status:\n"
        response += f"RAM Usage: {ram_usage:.2f} GB\n"
        for key, value in system_info.items():
            response += f"{key}: {value}\n"
        return response
    
    def _handle_connection_status(self, _: str) -> str:
        """Handle connection status check command"""
        # Get complete connection status
        status = self.connection_monitor.get_complete_status()
        
        # Create a rich table for connection status
        table = Table(title="Connection Status", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        
        connection_value = "Available" if status['internet_connection'] else "Unavailable"
        connection_style = "green" if status['internet_connection'] else "red"
        
        table.add_row("Internet Connection", f"[{connection_style}]{connection_value}[/{connection_style}]")
        
        # Include some network stats if available
        if status['network_stats']:
            for key, value in status['network_stats'].items():
                if key in ['bytes_sent', 'bytes_recv']:
                    table.add_row(f"Network {key.replace('_', ' ').title()}", f"{value} bytes")
        
        # Render the table
        self.console.print(table)
        
        # Log that connection status was checked
        self.logger.info("commands", "Connection status check performed")
        
        # Return simple text for voice output
        response = "Connection Status:\n"
        response += f"Internet Connection: {'Available' if status['internet_connection'] else 'Unavailable'}\n"
        
        # Include some network stats if available
        if status['network_stats']:
            response += "\nNetwork Statistics:\n"
            response += f"  - Bytes Sent: {status['network_stats']['bytes_sent']} bytes\n"
            response += f"  - Bytes Received: {status['network_stats']['bytes_recv']} bytes\n"
        
        return response

    def initialize_database(self):
        """Initialize the database schema"""
        self.db = Database()  # Store as an instance variable
        
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
    
    def _handle_ai_query(self, command: str) -> str:
        """Handle AI search queries using Gemini"""
        if not self.gemini_search:
            return "Gemini AI is not initialized. Please check your API key."
            
        # Extract the query from the command
        match = re.search(r'ask\s+(.*)', command, re.IGNORECASE)
        if not match:
            return "Please provide a question to ask (e.g., 'Nova ask what is artificial intelligence')"
        
        query = match.group(1).strip()
        try:
            # Create a spinner while waiting for AI response
            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]Thinking...[/bold blue]"),
                console=self.console
            ) as progress:
                task = progress.add_task("", total=None)
                # Get both a short snippet and a full answer
                result = self.gemini_search.quick_answer(query)
            
            if "error" in result:
                self.console.print(f"[red]{result['error']}[/red]")
                return result["error"]
                
            # Display the quick answer in a panel
            quick_panel = Panel.fit(
                result['snippet'], 
                title="Quick Answer", 
                border_style="blue"
            )
            self.console.print(quick_panel)
            
            # First provide the short snippet followed by the option to hear more
            self.voice.speak(f"Quick answer: {result['snippet']}")
            quick_answer = f"Quick answer: {result['snippet']}"
            
            # Ask if the user wants more details
            user_choice = Prompt.ask("\nWould you like to hear the full answer?", choices=["yes", "no"], default="yes")
            
            if user_choice.lower() in ["yes", "y"]:
                # Display the full answer in a markdown panel
                full_panel = Panel.fit(
                    Markdown(result['full_answer']),
                    title="Full Answer",
                    border_style="green", 
                    width=100
                )
                self.console.print(full_panel)
                return f"Full answer: {result['full_answer']}"
            else:
                return quick_answer + "Okay, ask me if you have any other questions."
        except Exception as e:
            self.console.print(f"[red]Error processing your question: {str(e)}[/red]")
            return f"Error processing your question: {str(e)}"
    
    def _handle_define(self, command: str) -> str:
        """Handle term definition requests using Gemini"""
        if not self.gemini_search:
            return "Gemini AI is not initialized. Please check your API key."
            
        # Extract the term from the command
        match = re.search(r'define\s+(.*)', command, re.IGNORECASE)
        if not match:
            return "Please provide a term to define (e.g., 'Nova define artificial intelligence')"
        
        term = match.group(1).strip()
        try:
            # Show a spinner while waiting for the definition
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[bold blue]Looking up definition for '{term}'...[/bold blue]"),
                console=self.console
            ) as progress:
                task = progress.add_task("", total=None)
                definition = self.gemini_search.define_term(term)
            
            # Display the definition in a panel
            definition_panel = Panel.fit(
                definition,
                title=f"Definition of '{term}'",
                border_style="cyan"
            )
            self.console.print(definition_panel)
            
            return f"Definition of '{term}': {definition}"
        except Exception as e:
            self.console.print(f"[red]Error defining the term: {str(e)}[/red]")
            return f"Error defining the term: {str(e)}"

    def _display_welcome(self, debug_log=None, info_log=None, warn_log=None, error_log=None, refresh_console=True):
        """Display welcome ASCII art and message with Rich styling"""
        # Clear the console
        self.console.clear()
        self.console.print("\n")
        # Create a welcome panel with the ASCII art
        welcome_text = """
 ██████   █████    ███████    █████   █████   █████████  
░░██████ ░░███   ███░░░░░███ ░░███   ░░███   ███░░░░░███ 
 ░███░███ ░███  ███     ░░███ ░███    ░███  ░███    ░███ 
 ░███░░███░███ ░███      ░███ ░███    ░███  ░███████████ 
 ░███ ░░██████ ░███      ░███ ░░███   ███   ░███░░░░░███ 
 ░███  ░░█████ ░░███     ███   ░░░█████░    ░███    ░███ 
 █████  ░░█████ ░░░███████░      ░░███      █████   █████ 
 ░░░░░    ░░░░░    ░░░░░░░         ░░░      ░░░░░   ░░░░░ 
        """
        
        welcome_panel = Panel.fit(
            Text(welcome_text, style="bright_cyan"),
            title="Welcome to Nova Assistant",
            subtitle="[yellow]NOTE: Ctrl + C if you want to quit[/yellow]",
            border_style="bright_cyan"
        )
        self.console.print(welcome_panel)
        
        # Create a system info table
        # self.console.print("\n")
        self.console.print("[bold blue]SYSTEM INFORMATION[/bold blue]")
        system_table = Table(box=box.SIMPLE)
        system_table.add_column("Parameter", style="cyan")
        system_table.add_column("Value", style="green")
        
        # Add RAM usage
        ram_usage = self.stats.get_ram_usage()
        system_table.add_row("RAM Usage", f"{ram_usage:.2f} GB")
        
        # Add system overview
        system_info = self.stats.get_system_info()
        for key, value in system_info.items():
            system_table.add_row(key, str(value))
        
        self.console.print(system_table)
        
        # Display logs with Rich
        
        self.console.print("[bold blue]RECENT LOGS[/bold blue]")
        logs = self.logger.display_logs(exclude_sources=["system"])
        if logs:
            log_table = Table(box=box.SIMPLE)
            log_table.add_column("Time", style="dim")
            log_table.add_column("Source", style="cyan")
            log_table.add_column("Message")
            
            for log in logs[-5:]:  # Show last 5 logs
                log_time = log.get('timestamp', 'Unknown')
                log_source = log.get('source', 'Unknown')
                log_message = log.get('message', 'No message')
                log_table.add_row(log_time, log_source, log_message)
            
            self.console.print(log_table)
        # else:
        #     self.console.print("[dim]No logs available[/dim]")
        
        # Display current date and time in a panel
        # self.console.print("\n")
        current_time, current_date = self.assistant.get_datetime()
        date_panel = Panel.fit(
            f"[bold]Time:[/bold] {current_time}\n[bold]Date:[/bold] {current_date}",
            title="Current DateTime",
            border_style="green"
        )
        self.console.print(date_panel)
        
        # Add a divider
        self.console.print("=" * 75, style="bright_blue")

    def _handle_help(self, _: str) -> str:
        """Handle the help command with Rich formatting"""
        help_text = self.typeHandler._show_help()
        
        # Create a rich panel with the help information
        help_panel = Panel.fit(
            Markdown(help_text),
            title="Nova Assistant Help",
            border_style="green",
            width=100
        )
        self.console.print(help_panel)
        
        return help_text
    
    def _handle_function_list(self, _: str) -> str:
        """Display functionalities of the assistant with Rich formatting"""
        functions_text = self.typeHandler.display_functions()
        
        # Create a table to display functions
        table = Table(title="Nova Assistant Functions", box=box.ROUNDED)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="green")
        
        # Parse the functions text and add to table
        for line in functions_text.split('\n'):
            if ':' in line:
                command, description = line.split(':', 1)
                table.add_row(command.strip(), description.strip())
        
        self.console.print(table)
        return functions_text
    
    def _handle_history(self, _: str) -> str:
        """Display command history with Rich formatting"""
        history = self.command_history.get_history()
        if not history:
            self.console.print("[yellow]No command history found.[/yellow]")
            return "No command history found."
        else:
            # Create a table for history
            table = Table(title="Command History", box=box.ROUNDED)
            table.add_column("#", style="dim")
            table.add_column("Timestamp", style="cyan")
            table.add_column("Command", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Response", style="blue")
            
            for i, entry in enumerate(history):
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                status_style = "green" if entry.execution_status == "completed" else "red"
                response = entry.response if entry.response else "No response"
                
                table.add_row(
                    str(i+1),
                    timestamp,
                    entry.command,
                    f"[{status_style}]{entry.execution_status}[/{status_style}]",
                    Text(response, overflow="fold")
                )
            
            self.console.print(table)
            
            # Return plain text for voice response
            result = "Command History:\n"
            for i, entry in enumerate(history):
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                response_info = f"\nResponse: {entry.response}" if entry.response else ""
                result += f"{i+1}: [{timestamp}] {entry.command} ({entry.execution_status}){response_info}\n"
            return result
    
    def _handle_history_start(self, _: str) -> str:
        """Start recording command history"""
        self.command_history.start_recording()
        self.console.print("[green]Command history recording started.[/green]")
        return "Command history recording started."
    
    def _handle_history_stop(self, _: str) -> str:
        """Stop recording command history"""
        self.command_history.stop_recording()
        self.console.print("[yellow]Command history recording stopped.[/yellow]")
        return "Command history recording stopped."
    
    def _handle_search_history(self, command: str) -> str:
        """Search command history with Rich formatting"""
        match = re.search(r'search\s+(.*)', command, re.IGNORECASE)
        if not match:
            self.console.print("[yellow]Please provide a search term (e.g., 'Nova search weather')[/yellow]")
            return "Please provide a search term (e.g., 'Nova search weather')"
        
        search_term = match.group(1).strip()
        results = self.command_history.search_history(search_term)
        
        if not results:
            self.console.print(f"[yellow]No results found for '{search_term}'.[/yellow]")
            return f"No results found for '{search_term}'."
        else:
            # Create a table for search results
            table = Table(title=f"Search Results for '{search_term}'", box=box.ROUNDED)
            table.add_column("#", style="dim")
            table.add_column("Timestamp", style="cyan")
            table.add_column("Command", style="green")
            table.add_column("Response", style="blue")
            
            for i, entry in enumerate(results):
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                response = entry.response if entry.response else "No response"
                
                table.add_row(
                    str(i+1),
                    timestamp,
                    entry.command,
                    Text(response, overflow="fold")
                )
            
            self.console.print(table)
            
            # Return plain text for voice response
            result = f"Search results for '{search_term}':\n"
            for i, entry in enumerate(results):
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                response_info = f"\nResponse: {entry.response}" if entry.response else ""
                result += f"{i+1}: [{timestamp}] {entry.command}{response_info}\n"
            return result
    
    def _handle_clear_history(self, _: str) -> str:
        """Clear command history"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold red]Clearing history...[/bold red]"),
            console=self.console
        ) as progress:
            task = progress.add_task("", total=1)
            success = self.command_history.clear_history()
            progress.update(task, advance=1)
            
        if success:
            self.console.print("[green]Command history cleared.[/green]")
            return "Command history cleared."
        else:
            self.console.print("[red]Failed to clear command history.[/red]")
            return "Failed to clear command history."

    def setup_signal_handlers(self):
        """Setup handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.console.print("\n[yellow]Received shutdown signal. Cleaning up...[/yellow]")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Cleanup resources before shutdown"""
        try:
            self.console.print("[blue]Performing cleanup...[/blue]")
            if hasattr(self, 'db'):
                self.db.close()
                self.console.print("[green]Database connection closed.[/green]")
            self._handle_history_stop("")
            self.voice.speak("Goodbye!")
        except Exception as e:
            self.console.print(f"[red]Error during cleanup: {str(e)}[/red]")
        
        thank_you_panel = Panel.fit(
            "Thank you for using NOVA Assistant!",
            border_style="green"
        )
        self.console.print(thank_you_panel)

    def _handle_open(self, command: str) -> str:
        """Handle both website and app opening commands"""
        parts = command.split(None, 2)
        if len(parts) < 2:
            self.console.print("[yellow]Please specify what to open[/yellow]")
            return "Please specify what to open"
            
        target = parts[1]
        
        # Check if it's a website (contains domain-like structure)
        if '.' in target:
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn(f"[bold blue]Opening website {target}...[/bold blue]"),
                    console=self.console
                ) as progress:
                    task = progress.add_task("", total=1)
                    self.assistant.open_website(target)
                    progress.update(task, advance=1)
                
                self.console.print(f"[green]Opening website: {target}[/green]")
                return f"Opening website: {target}"
            except AppOperationError as e:
                self.console.print(f"[red]{str(e)}[/red]")
                return str(e)
        else:
            # Assume it's an application
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn(f"[bold blue]Opening {target}...[/bold blue]"),
                    console=self.console
                ) as progress:
                    task = progress.add_task("", total=1)
                    self.assistant.open_app(target)
                    progress.update(task, advance=1)
                    
                self.console.print(f"[green]Opening {target}[/green]")
                return f"Opening {target}"
            except AppOperationError as e:
                self.console.print(f"[red]{str(e)}[/red]")
                return str(e)

    def _handle_time(self, _: str) -> str:
        time, _ = self.assistant.get_datetime()
        time_panel = Panel.fit(
            time, 
            title="Current Time",
            border_style="blue"
        )
        self.console.print(time_panel)
        return f"The current time is {time}"

    def _handle_date(self, _: str) -> str:
        _, date = self.assistant.get_datetime()
        date_panel = Panel.fit(
            date, 
            title="Current Date",
            border_style="green"
        )
        self.console.print(date_panel)
        return f"The current date is {date}"

    def _handle_calculation(self, command: str) -> str:
        # Extract the mathematical expression
        match = re.search(r'calculate\s+(.*)', command, re.IGNORECASE)
        if not match:
            self.console.print("[yellow]Please provide a calculation (e.g., 'Nova calculate 2 + 2')[/yellow]")
            return "Please provide a calculation (e.g., 'Nova calculate 2 + 2')"
        
        expression = match.group(1).strip()
        try:
            result = self.assistant.calculate(expression)
            
            # Create a syntax highlighted expression
            syntax = Syntax(
                f"{expression} = {result}", 
                "python", 
                theme="monokai",
                word_wrap=True
            )
            
            calc_panel = Panel.fit(
                syntax,
                title="Calculation Result",
                border_style="cyan"
            )
            self.console.print(calc_panel)
            
            return f"The result is: {result}"
        except ValueError as e:
            self.console.print(f"[red]{str(e)}[/red]")
            return str(e)

    def _handle_weather(self, command: str) -> str:
        """Handle weather queries without using nested Live displays"""
        # Extract city name
        match = re.search(r'weather\s+(?:of\s+|in\s+)?([a-zA-Z\s]+)', command, re.IGNORECASE)
        if not match:
            self.console.print("[yellow]Please specify a city (e.g., 'Nova tell me the weather of London')[/yellow]")
            return "Please specify a city (e.g., 'Nova tell me the weather of London')"
        
        city = match.group(1).strip()
        try:
            # Show text indicator instead of spinner
            self.console.print(f"[bold blue]Fetching weather for {city}...[/bold blue]")
            
            # Get the weather data without a progress spinner
            weather_data = self.weather.get_weather(city)
            
            # Format weather data in a panel
            weather_text = str(weather_data)
            weather_panel = Panel.fit(
                weather_text,
                title=f"Weather in {city}",
                border_style="blue"
            )
            self.console.print(weather_panel)
            
            return str(weather_data)
        except WeatherAPIError as e:
            self.console.print(f"[red]{str(e)}[/red]")
            return str(e)

    def _handle_thanks(self, _: str) -> str:
        thanks_message = "Happy to help! Have a great day! Come back to me if you have any doubts"
        self.console.print(f"[green]{thanks_message}[/green]")
        return thanks_message
    
    def _handle_exit(self, _: str) -> str:
        self.cleanup()
        sys.exit(0)

    def process_command(self, command: str) -> Optional[str]:
        """Process user commands and return appropriate response"""
        if not command:
            return None
            
        command = command.lower().strip()
        
        # Handle exit commands first
        if command in ['exit', 'quit', 'bye']:
            self.cleanup()
            sys.exit(0)
        
        # Record the command in history before processing
        try:
            context = {"execution_time": datetime.now().isoformat()}
            self.command_history.add_command(command, "initiated", context)
        except Exception as e:
            self.console.print(f"[red]Failed to record command: {e}[/red]")
            
        # Handle help command explicitly
        if "help" in command:
            response = self._handle_help(command)
            self.save_response(command, response, "completed")
            return response
            
        if any(word in command for word in ['thanks', 'thank you']):
            response = self._handle_thanks(command)
            self.save_response(command, response, "completed")
            return response
        
        # Handle history commands
        if command == "history":
            response = self._handle_history(command)
            self.save_response(command, response, "completed")
            return response
        elif command == "history start":
            response = self._handle_history_start(command)
            self.save_response(command, response, "completed")
            return response
        elif command == "history stop":
            response = self._handle_history_stop(command)
            self.save_response(command, response, "completed")
            return response
        elif command == "clear history":
            response = self._handle_clear_history(command)
            self.save_response(command, response, "completed")
            return response
        elif command.startswith("search "):
            response = self._handle_search_history(command)
            self.save_response(command, response, "completed")
            return response
            
        # Match command to handler
        for cmd_key, handler in self.commands.items():
            if cmd_key in command:
                response = handler(command)
                # Save the response and update command status
                self.save_response(command, response, "completed")
                return response

        # Handle unrecognized commands
        self.console.print("[red]I'm sorry, I didn't understand that command.[/red]")
        self.console.print("Please say 'Nova help' to see available commands.")
        response = ("I'm sorry, I didn't understand that command. "
                  "Please say 'Nova help' to see available commands.")
        self.save_response(command, response, "failed")
        return response
    
    def save_response(self, command: str, response: str, status: str):
        """Save response and update command status"""
        try:
            # Update both status and response
            self.command_history.update_command_status(command, status)
            # Add new method to save response (to be implemented in command_history class)
            self.command_history.save_response(command, response)
        except Exception as e:
            self.console.print(f"[red]Failed to save response: {e}[/red]")
    
    def choose_input_method(self):
        """Allow the user to select input method: text or speak using Rich UI."""
        choices_panel = Panel.fit(
            "1. [cyan]Type[/cyan] commands using the keyboard\n"
            "2. [cyan]Speak[/cyan] commands using the microphone",
            title="Choose Input Method",
            border_style="green"
        )
        # self.console.print("\n")
        self.console.print(choices_panel)
        
        choice = Prompt.ask("\nSelect input method", choices=["type", "speak"], default="type")
            
        if choice.lower() == "type":
            self.console.print("[green]Selected: Keyboard input[/green]")
            return self.typeHandler.get_input
        else:
            self.console.print("[green]Selected: Voice input[/green]")
            return self.voice.listen

    def run(self):
        """Main loop for the assistant"""
        self._handle_history_start("")
        self.initialize_database()
        self.command_history.connect()
        self._display_welcome()  # Display ASCII art and welcome message
        self.voice.speak("Hello, I am Nova, your Python-Powered AI Assistant")
        input_method = self.choose_input_method()
        
        while True:
            try:
                # Create a stylish prompt
                self.console.print("\n[bold cyan]NOVA[/bold cyan] [dim cyan]is listening...[/dim cyan]")
                
                command = input_method()
                if command in ["exit", "quit", "bye"]:
                    self.cleanup()
                    break
                
                # Display the command with styling
                self.console.print(f"[dim]Command:[/dim] [bold green]{command}[/bold green]")
                
                # Instead of showing a progress spinner, just indicate processing
                self.console.print("[dim]Processing...[/dim]")
                
                # Process the command without a nested progress display
                response = self.process_command(command)
                
                if response:
                    # Don't display the response again, just speak it
                    self.voice.speak(response)
                    
            except Exception as e:
                self.console.print(f"\n[red]Error: {str(e)}[/red]")
                self.voice.speak("I encountered an error. Please try again.")

def main():
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