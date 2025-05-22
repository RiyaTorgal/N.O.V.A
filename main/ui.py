"""
UI management for Nova Assistant.
Handles display and interface elements using Rich library.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.syntax import Syntax
from rich.layout import Layout
from rich.prompt import Prompt
from rich import box
from rich.markdown import Markdown


class UIManager:
    """Handles UI display and management for Nova Assistant."""
    
    def __init__(self):
        """Initialize the UI manager"""
        self.console = Console()
        self.layout = Layout()
    
    def clear_screen(self):
        """Clear the console screen"""
        self.console.clear()
    
    def display_welcome(self, stats, logger):
        """
        Display welcome ASCII art and message with Rich styling.
        
        Args:
            stats: SystemMonitor instance for system stats
            logger: Logger instance for logs
        """
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
        self.console.print("[bold blue]SYSTEM INFORMATION[/bold blue]")
        system_table = Table(box=box.SIMPLE)
        system_table.add_column("Parameter", style="cyan")
        system_table.add_column("Value", style="green")
        
        # Add RAM usage
        ram_usage = stats.get_ram_usage()
        system_table.add_row("RAM Usage", f"{ram_usage:.2f} GB")
        
        # Add system overview
        system_info = stats.get_system_info()
        for key, value in system_info.items():
            system_table.add_row(key, str(value))
        
        self.console.print(system_table)
        
        # Display logs with Rich
        self.console.print("[bold blue]RECENT LOGS[/bold blue]")
        logs = logger.display_logs(exclude_sources=["system"])
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
        
        # Add a divider
        self.console.print("=" * 75, style="bright_blue")
    
    def display_command_prompt(self):
        """Display the command prompt"""
        self.console.print("\n[bold cyan]NOVA[/bold cyan] [dim cyan]is listening...[/dim cyan]")
    
    def display_time(self, time_str):
        """
        Display the current time in a panel.
        
        Args:
            time_str: Time string to display
        """
        time_panel = Panel.fit(
            time_str, 
            title="Current Time",
            border_style="blue"
        )
        self.console.print(time_panel)
    
    def display_date(self, date_str):
        """
        Display the current date in a panel.
        
        Args:
            date_str: Date string to display
        """
        date_panel = Panel.fit(
            date_str, 
            title="Current Date",
            border_style="green"
        )
        self.console.print(date_panel)
    
    def display_datetime(self, time_str, date_str):
        """
        Display the current date and time in a panel.
        
        Args:
            time_str: Time string to display
            date_str: Date string to display
        """
        date_panel = Panel.fit(
            f"[bold]Time:[/bold] {time_str}\n[bold]Date:[/bold] {date_str}",
            title="Current DateTime",
            border_style="green"
        )
        self.console.print(date_panel)
    
    def display_calculation_result(self, expression, result):
        """
        Display a calculation result with syntax highlighting.
        
        Args:
            expression: The mathematical expression
            result: The calculated result
        """
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
    
    def display_weather(self, city, weather_data):
        """
        Display weather information in a panel.
        
        Args:
            city: The city name
            weather_data: Weather data to display
        """
        weather_text = str(weather_data)
        weather_panel = Panel.fit(
            weather_text,
            title=f"Weather in {city}",
            border_style="blue"
        )
        self.console.print(weather_panel)
    
    def display_help(self, help_text):
        """
        Display help information in a panel.
        
        Args:
            help_text: Help text to display
        """
        help_panel = Panel.fit(
            Markdown(help_text),
            title="Nova Assistant Help",
            border_style="green",
            width=100
        )
        self.console.print(help_panel)
    
    def display_functions_table(self, functions_text):
        """
        Display available functions in a table.
        
        Args:
            functions_text: Text describing functions
        """
        table = Table(title="Nova Assistant Functions", box=box.ROUNDED)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="green")
        
        # Parse the functions text and add to table
        for line in functions_text.split('\n'):
            if ':' in line:
                command, description = line.split(':', 1)
                table.add_row(command.strip(), description.strip())
        
        self.console.print(table)
    
    def display_history_table(self, history):
        """
        Display command history in a table.
        
        Args:
            history: List of history entries
        """
        if not history:
            self.console.print("[yellow]No command history found.[/yellow]")
            return
            
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
    
    def display_search_results(self, search_term, results):
        """
        Display search results in a table.
        
        Args:
            search_term: The search term
            results: List of search results
        """
        if not results:
            self.console.print(f"[yellow]No results found for '{search_term}'.[/yellow]")
            return
            
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
    
    def display_system_status(self, system_stats):
        """
        Display system status in a table.
        
        Args:
            system_stats: Dictionary of system statistics
        """
        table = Table(title="System Status", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        
        ram_usage = system_stats.get('ram_usage', 0)
        table.add_row("RAM Usage", f"{ram_usage:.2f} GB")
        
        for key, value in system_stats.items():
            if key != 'ram_usage':
                table.add_row(key, str(value))
                
        self.console.print(table)
    
    def display_connection_status(self, connection_status):
        """
        Display connection status in a table.
        
        Args:
            connection_status: Dictionary of connection status information
        """
        table = Table(title="Connection Status", box=box.ROUNDED)
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        
        connection_value = "Available" if connection_status['internet_connection'] else "Unavailable"
        connection_style = "green" if connection_status['internet_connection'] else "red"
        
        table.add_row("Internet Connection", f"[{connection_style}]{connection_value}[/{connection_style}]")
        
        # Include some network stats if available
        if connection_status['network_stats']:
            for key, value in connection_status['network_stats'].items():
                if key in ['bytes_sent', 'bytes_recv']:
                    table.add_row(f"Network {key.replace('_', ' ').title()}", f"{value} bytes")
        
        self.console.print(table)
    
    def display_ai_answer(self, result):
        """
        Display AI answer in panels.
        
        Args:
            result: Dictionary containing AI response data
        """
        if "error" in result:
            self.console.print(f"[red]{result['error']}[/red]")
            return
            
        # Display the quick answer in a panel
        quick_panel = Panel.fit(
            result['snippet'], 
            title="Quick Answer", 
            border_style="blue"
        )
        self.console.print(quick_panel)
        
    def display_full_ai_answer(self, full_answer):
        """
        Display the full AI answer in a panel.
        
        Args:
            full_answer: Full answer text to display
        """
        full_panel = Panel.fit(
            Markdown(full_answer),
            title="Full Answer",
            border_style="green", 
            width=100
        )
        self.console.print(full_panel)
    
    def display_definition(self, term, definition):
        """
        Display a term definition in a panel.
        
        Args:
            term: The term being defined
            definition: The definition text
        """
        definition_panel = Panel.fit(
            definition,
            title=f"Definition of '{term}'",
            border_style="cyan"
        )
        self.console.print(definition_panel)
    
    def display_error(self, error_message):
        """
        Display an error message.
        
        Args:
            error_message: Error message to display
        """
        self.console.print(f"[red]{error_message}[/red]")
    
    def display_success(self, success_message):
        """
        Display a success message.
        
        Args:
            success_message: Success message to display
        """
        self.console.print(f"[green]{success_message}[/green]")
    
    def display_warning(self, warning_message):
        """
        Display a warning message.
        
        Args:
            warning_message: Warning message to display
        """
        self.console.print(f"[yellow]{warning_message}[/yellow]")
    
    def display_info(self, info_message):
        """
        Display an info message.
        
        Args:
            info_message: Info message to display
        """
        self.console.print(f"[blue]{info_message}[/blue]")
    
    def prompt_for_input_method(self):
        """
        Prompt the user to select an input method.
        
        Returns:
            str: Selected input method ('type' or 'speak')
        """
        choices_panel = Panel.fit(
            "1. [cyan]Type[/cyan] commands using the keyboard\n"
            "2. [cyan]Speak[/cyan] commands using the microphone",
            title="Choose Input Method",
            border_style="green"
        )
        self.console.print(choices_panel)
        
        choice = Prompt.ask("\nSelect input method", choices=["type", "speak"], default="type")
        
        if choice.lower() == "type":
            self.console.print("[green]Selected: Keyboard input[/green]")
        else:
            self.console.print("[green]Selected: Voice input[/green]")
            
        return choice.lower()
    
    def show_processing_indicator(self):
        """Show a processing indicator"""
        self.console.print("[dim]Processing...[/dim]")
    
    def show_spinner(self, message, callback, *args, **kwargs):
        """
        Show a spinner while executing a callback function.
        
        Args:
            message: Message to display with spinner
            callback: Function to execute
            *args: Arguments to pass to callback
            **kwargs: Keyword arguments to pass to callback
            
        Returns:
            Result of the callback function
        """
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[bold blue]{message}[/bold blue]"),
            console=self.console
        ) as progress:
            task = progress.add_task("", total=None)
            result = callback(*args, **kwargs)
        return result