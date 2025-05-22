"""
Command handlers for Nova Assistant.
Contains all methods for processing and executing different user commands.
"""

import re
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt
from src.core.exceptions import AppOperationError, WeatherAPIError


class CommandHandlers:
    """Handles command processing and execution for Nova Assistant."""
    
    def __init__(self, app):
        """
        Initialize command handlers with a reference to the main app.
        
        Args:
            app: Main NovaAssistant instance
        """
        self.app = app
        # Initialize shortcuts for frequently used components
        self.console = app.console
        self.ui = app.ui
        self.voice = app.voice
        self.assistant = app.assistant
        self.weather = app.weather
        self.gemini_search = app.gemini_search
        self.command_history = app.command_history
        self.stats = app.stats
        self.connection_monitor = app.connection_monitor
        self.typeHandler = app.typeHandler

    # Time and Date Commands
    def handle_time(self, _):
        """
        Handle time command.
        
        Args:
            _: Original command string
            
        Returns:
            str: Response message
        """
        time, _ = self.assistant.get_datetime()
        self.ui.display_time(time)
        return f"The current time is {time}"

    def handle_date(self, _):
        """
        Handle date command.
        
        Args:
            _: Original command string
            
        Returns:
            str: Response message
        """
        _, date = self.assistant.get_datetime()
        self.ui.display_date(date)
        return f"The current date is {date}"

    # Math and Calculation Commands
    def handle_calculation(self, command):
        """
        Handle calculation commands.
        
        Args:
            command: Original command string
            
        Returns:
            str: Response message with calculation result
        """
        # Extract the mathematical expression
        match = re.search(r'calculate\s+(.*)', command, re.IGNORECASE)
        if not match:
            self.console.print("[yellow]Please provide a calculation (e.g., 'Nova calculate 2 + 2')[/yellow]")
            return "Please provide a calculation (e.g., 'Nova calculate 2 + 2')"
        
        expression = match.group(1).strip()
        try:
            result = self.assistant.calculate(expression)
            self.ui.display_calculation_result(expression, result)
            return f"The result is: {result}"
        except ValueError as e:
            self.console.print(f"[red]{str(e)}[/red]")
            return str(e)

    # Weather Commands
    def handle_weather(self, command):
        """
        Handle weather commands.
        
        Args:
            command: Original command string
            
        Returns:
            str: Response message with weather information
        """
        # Extract city name
        match = re.search(r'weather\s+(?:of\s+|in\s+)?([a-zA-Z\s]+)', command, re.IGNORECASE)
        if not match:
            self.console.print("[yellow]Please specify a city (e.g., 'Nova tell me the weather of London')[/yellow]")
            return "Please specify a city (e.g., 'Nova tell me the weather of London')"
        
        city = match.group(1).strip()
        try:
            # Show text indicator
            self.console.print(f"[bold blue]Fetching weather for {city}...[/bold blue]")
            
            # Get the weather data
            weather_data = self.weather.get_weather(city)
            
            # Display weather data
            self.ui.display_weather(city, weather_data)
            
            return str(weather_data)
        except WeatherAPIError as e:
            self.console.print(f"[red]{str(e)}[/red]")
            return str(e)

    # App and Website Commands
    def handle_open(self, command):
        """
        Handle both website and app opening commands.
        
        Args:
            command: Original command string
            
        Returns:
            str: Response message
        """
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

    # Help and Information Commands
    def handle_help(self, _):
        """
        Handle the help command.
        
        Args:
            _: Original command string
            
        Returns:
            str: Help information
        """
        help_text = self.typeHandler._show_help()
        self.ui.display_help(help_text)
        return help_text
    
    def handle_function_list(self, _):
        """
        Display list of available functions.
        
        Args:
            _: Original command string
            
        Returns:
            str: Function list information
        """
        functions_text = self.typeHandler.display_functions()
        self.ui.display_functions_table(functions_text)
        return functions_text

    # Thank You Command
    def handle_thanks(self, _):
        """
        Handle thank you command.
        
        Args:
            _: Original command string
            
        Returns:
            str: Response message
        """
        thanks_message = "Happy to help! Have a great day! Come back to me if you have any doubts"
        self.console.print(f"[green]{thanks_message}[/green]")
        return thanks_message

    # System Status Commands
    def handle_system_status(self, _):
        """
        Handle system status check command.
        
        Args:
            _: Original command string
            
        Returns:
            str: System status information
        """
        # Get system information
        system_info = self.stats.get_system_info()
        ram_usage = self.stats.get_ram_usage()
        
        # Create system status information
        system_stats = {'ram_usage': ram_usage}
        system_stats.update(system_info)
        
        # Display the system status
        self.ui.display_system_status(system_stats)
        
        # Log that system status was checked
        self.app.logger.info("commands", "System status check performed")
        
        # Return simple text for voice output
        response = "System Status:\n"
        response += f"RAM Usage: {ram_usage:.2f} GB\n"
        for key, value in system_info.items():
            response += f"{key}: {value}\n"
        return response
    
    def handle_connection_status(self, _):
        """
        Handle connection status check command.
        
        Args:
            _: Original command string
            
        Returns:
            str: Connection status information
        """
        # Get complete connection status
        status = self.connection_monitor.get_complete_status()
        
        # Display the connection status
        self.ui.display_connection_status(status)
        
        # Log that connection status was checked
        self.app.logger.info("commands", "Connection status check performed")
        
        # Return simple text for voice output
        response = "Connection Status:\n"
        response += f"Internet Connection: {'Available' if status['internet_connection'] else 'Unavailable'}\n"
        
        # Include some network stats if available
        if status['network_stats']:
            response += "\nNetwork Statistics:\n"
            response += f"  - Bytes Sent: {status['network_stats']['bytes_sent']} bytes\n"
            response += f"  - Bytes Received: {status['network_stats']['bytes_recv']} bytes\n"
        
        return response

    # Command History Commands
    def handle_history(self, _):
        """
        Display command history.
        
        Args:
            _: Original command string
            
        Returns:
            str: Command history information
        """
        history = self.command_history.get_history()
        if not history:
            self.console.print("[yellow]No command history found.[/yellow]")
            return "No command history found."
        else:
            # Display the history table
            self.ui.display_history_table(history)
            
            # Return plain text for voice response
            result = "Command History:\n"
            for i, entry in enumerate(history):
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                response_info = f"\nResponse: {entry.response}" if entry.response else ""
                result += f"{i+1}: [{timestamp}] {entry.command} ({entry.execution_status}){response_info}\n"
            return result
    
    def handle_history_start(self, _):
        """
        Start recording command history.
        
        Args:
            _: Original command string
            
        Returns:
            str: Response message
        """
        self.command_history.start_recording()
        self.console.print("[green]Command history recording started.[/green]")
        return "Command history recording started."
    
    def handle_history_stop(self, _):
        """
        Stop recording command history.
        
        Args:
            _: Original command string
            
        Returns:
            str: Response message
        """
        self.command_history.stop_recording()
        self.console.print("[yellow]Command history recording stopped.[/yellow]")
        return "Command history recording stopped."
    
    def handle_search_history(self, command):
        """
        Search command history.
        
        Args:
            command: Original command string
            
        Returns:
            str: Search results
        """
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
            # Display search results
            self.ui.display_search_results(search_term, results)
            
            # Return plain text for voice response
            result = f"Search results for '{search_term}':\n"
            for i, entry in enumerate(results):
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                response_info = f"\nResponse: {entry.response}" if entry.response else ""
                result += f"{i+1}: [{timestamp}] {entry.command}{response_info}\n"
            return result
    
    def handle_clear_history(self, _):
        """
        Clear command history.
        
        Args:
            _: Original command string
            
        Returns:
            str: Response message
        """
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

    # AI and Search Commands
    def handle_ai_query(self, command):
        """
        Handle AI search queries using Gemini.
        
        Args:
            command: Original command string
            
        Returns:
            str: AI response
        """
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
                
            # Display the quick answer
            self.ui.display_ai_answer(result)
            
            # First provide the short snippet followed by the option to hear more
            self.voice.speak(f"Quick answer: {result['snippet']}")
            quick_answer = f"Quick answer: {result['snippet']}"
            
            # Ask if the user wants more details
            user_choice = Prompt.ask("\nWould you like to hear the full answer?", choices=["yes", "no"], default="yes")
            
            if user_choice.lower() in ["yes", "y"]:
                # Display the full answer
                self.ui.display_full_ai_answer(result['full_answer'])
                return f"Full answer: {result['full_answer']}"
            else:
                return quick_answer + "Okay, ask me if you have any other questions."
        except Exception as e:
            self.console.print(f"[red]Error processing your question: {str(e)}[/red]")
            return f"Error processing your question: {str(e)}"
    
    def handle_define(self, command):
        """
        Handle term definition requests using Gemini.
        
        Args:
            command: Original command string
            
        Returns:
            str: Definition response
        """
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
            
            # Display the definition
            self.ui.display_definition(term, definition)
            
            return f"Definition of '{term}': {definition}"
        except Exception as e:
            self.console.print(f"[red]Error defining the term: {str(e)}[/red]")
            return f"Error defining the term: {str(e)}"