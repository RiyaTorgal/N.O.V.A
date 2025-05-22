import os
import sys
from main.app import NovaAssistant

def main():
    try:
        # Create and run the assistant
        assistant = NovaAssistant()
        assistant.run()
    except Exception as e:
        from rich.console import Console
        console = Console()
        console.print(f"\n[bold red]Fatal error:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()