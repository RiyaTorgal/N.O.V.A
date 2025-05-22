"""
Signal handling and cleanup for Nova Assistant.
Provides functions for managing system signals and graceful shutdown.
"""

import signal
import sys
from rich.console import Console
from rich.panel import Panel


class SignalManager:
    """Manages signal handling and cleanup operations for Nova Assistant."""
    
    def __init__(self, app_instance):
        """
        Initialize the SignalManager.
        
        Args:
            app_instance: The main NovaAssistant instance to manage
        """
        self.app = app_instance
        self.console = Console()
    
    def setup_signal_handlers(self):
        """Setup handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """
        Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.console.print("\n[yellow]Received shutdown signal. Cleaning up...[/yellow]")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Cleanup resources before shutdown"""
        try:
            self.console.print("[blue]Performing cleanup...[/blue]")
            if hasattr(self.app, 'db'):
                self.app.db.close()
                self.console.print("[green]Database connection closed.[/green]")
            
            # Stop history recording
            if hasattr(self.app, 'command_history'):
                self.app.command_history.stop_recording()
            
            # Say goodbye
            if hasattr(self.app, 'voice'):
                self.app.voice.speak("Goodbye!")
                
        except Exception as e:
            self.console.print(f"[red]Error during cleanup: {str(e)}[/red]")
        
        thank_you_panel = Panel.fit(
            "Thank you for using NOVA Assistant!",
            border_style="green"
        )
        self.console.print(thank_you_panel)