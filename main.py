from typing import Optional
import signal
import sys
import re
import os
from pathlib import Path
from dotenv import load_dotenv
from src.core.exceptions import AppOperationError, AssistantError, WeatherAPIError
from src.core.assistant import Assistant
from src.input.text_handler import TypedInputHandler
from src.input.voice_handler import VoiceAssistant
from src.services.weather import WeatherAPI

dotenv_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
load_dotenv(dotenv_path)

class NovaAssistant:
    def __init__(self):
        self.api_key = os.environ.get("API_KEY")
        self.assistant = Assistant()
        self.typeHandler = TypedInputHandler()
        self.voice = VoiceAssistant()
        self.weather = WeatherAPI(self.api_key)
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
        }
        self.setup_signal_handlers()

    def _display_welcome(self):
        """Display welcome ASCII art and message"""
        print("\n")
        print(" ██████   █████    ███████    █████   █████   █████████  ")
        print("░░██████ ░░███   ███░░░░░███ ░░███   ░░███   ███░░░░░███ ")
        print(" ░███░███ ░███  ███     ░░███ ░███    ░███  ░███    ░███ ")
        print(" ░███░░███░███ ░███      ░███ ░███    ░███  ░███████████ ")
        print(" ░███ ░░██████ ░███      ░███ ░░███   ███   ░███░░░░░███ ")
        print(" ░███  ░░█████ ░░███     ███   ░░░█████░    ░███    ░███ ")
        print(" █████  ░░█████ ░░░███████░      ░░███      █████   █████ ")
        print(" ░░░░░    ░░░░░    ░░░░░░░         ░░░      ░░░░░   ░░░░░ ")
        print("\n")
        print("="*50)
        print("Welcome to NOVA - Your Python-Powered AI Assistant!")
        print("Remember to start your commands with 'Nova'")
        print("For example: 'Nova tell me the time'")
        print("Type 'Nova help' for a list of available commands")
        print("="*50)
        print("\n")

    def _handle_help(self, _: str) -> str:
        """Handle the help command"""
        """Return The _show_help function from data.py"""
        return self.typeHandler._show_help()
    
    def _handle_function_list(self, _: str) -> str:
        """Display functionalities of the assistant"""
        return self.typeHandler.display_functions()

    def setup_signal_handlers(self):
        """Setup handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\nReceived shutdown signal. Cleaning up...")
        self.cleanup()
        sys.exit(0)

    def cleanup(self):
        """Cleanup resources before shutdown"""
        try:
            self.voice.speak("Goodbye!")
        except:
            pass
        print("\nThank you for using NOVA Assistant!")

    def _handle_open(self, command: str) -> str:
        """Handle both website and app opening commands"""
        parts = command.split(None, 2)
        if len(parts) < 2:
            return "Please specify what to open"
            
        target = parts[1]
        
        # Check if it's a website (contains domain-like structure)
        if '.' in target:
            try:
                self.assistant.open_website(target)
                return f"Opening website: {target}"
            except AppOperationError as e:
                return str(e)
        else:
            # Assume it's an application
            try:
                self.assistant.open_app(target)
                return f"Opening {target}"
            except AppOperationError as e:
                return str(e)

    def _handle_time(self, _: str) -> str:
        time, _ = self.assistant.get_datetime()
        return f"The current time is {time}"

    def _handle_date(self, _: str) -> str:
        _, date = self.assistant.get_datetime()
        return f"The current date is {date}"

    def _handle_calculation(self, command: str) -> str:
        # Extract the mathematical expression
        match = re.search(r'calculate\s+(.*)', command, re.IGNORECASE)
        if not match:
            return "Please provide a calculation (e.g., 'Nova calculate 2 + 2')"
        
        expression = match.group(1).strip()
        try:
            result = self.assistant.calculate(expression)
            return f"The result is: {result}"
        except ValueError as e:
            return str(e)

    def _handle_weather(self, command: str) -> str:
        # Extract city name
        match = re.search(r'weather\s+(?:of\s+|in\s+)?([a-zA-Z\s]+)', command, re.IGNORECASE)
        if not match:
            return "Please specify a city (e.g., 'Nova tell me the weather of London')"
        
        city = match.group(1).strip()
        try:
            weather_data = self.weather.get_weather(city)
            return str(weather_data)
        except WeatherAPIError as e:
            return str(e)

    def _handle_thanks(self, _: str) -> str:
        return "Happy to help! Have a great day! Come back to me if you have any doubts"
    
    def _handle_exit(self, _: str) -> str:
        sys.exit(0)

    # def process_command(self, command: str) -> Optional[str]:
    #     """Process user commands and return appropriate response"""
    #     if not command:
    #         return None
            
    #     command = command.lower().strip()
        
    #     # Handle help command explicitly
    #     if "help" in command:
    #         return self._handle_help(command)
            
    #     # Handle exit commands
    #     if command in ['exit', 'quit', 'bye']:
    #         return self._handle_exit(command)
            
    #     if any(word in command for word in ['thanks', 'thank you']):
    #         return self._handle_thanks(command)
            
    #     # Match command to handler
    #     for cmd_key, handler in self.commands.items():
    #         if cmd_key in command:
    #             return handler(command)
        
    #     return ("I'm sorry, I didn't understand that command. "
    #             "Please say 'help' to see available commands.")

    def process_command(self, command: str) -> Optional[str]:
        """Process user commands and return appropriate response"""
        if not command:
            return None
            
        command = command.lower().strip()
        
        # Handle exit commands first
        if command in ['exit', 'quit', 'bye']:
            self.cleanup()
            sys.exit(0)
            
        # Handle help command explicitly
        if "help" in command:
            return self._handle_help(command)
            
        if any(word in command for word in ['thanks', 'thank you']):
            return self._handle_thanks(command)
            
        # Match command to handler
        for cmd_key, handler in self.commands.items():
            if cmd_key in command:
                return handler(command)
        
        return ("I'm sorry, I didn't understand that command. "
                "Please say 'Nova help' to see available commands.")
    
    def choose_input_method(self):
        """Allow the user to select input method: text or speak."""
        while True:
            print("\nChoose Input Method:")
            print("1. Type commands using the keyboard")
            print("2. Speak commands using the microphone")
            
            choice = input("\nSelect input method (type/speak): ").lower().strip()
            
            if choice == "type":
                return self.typeHandler.get_input
            elif choice == "speak":
                return self.voice.listen
            else:
                print("Invalid choice. Please select either 'type' or 'speak'.")

    def run(self):
        """Main loop for the assistant"""
        self._display_welcome()  # Display ASCII art and welcome message
        self.voice.speak("Hello, I am Nova, your Python-Powered AI Assistant")
        # input_method = self.voice.get_input_method()
        # input_method = self.typeHandler.get_input
        input_method = self.choose_input_method()
        
        while True:
            try:
                command = input_method()
                if command in ["exit", "quit", "bye"]:
                    self.cleanup()
                    break
                    
                response = self.process_command(command)
                if response:
                    self.voice.speak(response)
                    
            except Exception as e:
                print(f"\nError: {str(e)}")
                self.voice.speak("I encountered an error. Please try again.")

def main():
    try:
        assistant = NovaAssistant()
        assistant.run()
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()