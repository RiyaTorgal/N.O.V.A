from datetime import datetime
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
from src.services.ai_implementation import GeminiSearch
from src.utils.command_history import DatabaseCommandHistory
from src.dB.database import Database
from src.utils.stats import SystemMonitor
# from src.utils.stats import Logger
# from logs import NovaLogger as Logger
# import logging


dotenv_path = os.path.join(os.path.dirname(__file__), 'config', '.env')
load_dotenv(dotenv_path)

class NovaAssistant:
    def __init__(self):
        self.api_key = os.environ.get("API_KEY")
        self.assistant = Assistant()
        self.stats = SystemMonitor()
        self.typeHandler = TypedInputHandler()
        self.voice = VoiceAssistant()
        self.weather = WeatherAPI(self.api_key)
        self.gemini_api_key = os.environ.get("GEMINI")  # Make sure you have a GEMINI env variable
        # self.logger = Logger(log_to_console=True, log_to_file=True, log_file="nova_logs.txt")
        self.input_mode = "TEXT"  # Default input mode
        self.speech_enabled = False
        try:
            if self.gemini_api_key:
                self.gemini_search = GeminiSearch(self.gemini_api_key)
            else:
                print("Warning: Gemini API key not found. AI search functionality will be disabled.")
                self.gemini_search = None
        except Exception as e:
            print(f"Error initializing Gemini search: {e}")
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

    def initialize_database(self):
        """Initialize the database schema"""
        self.db = Database()  # Store as an instance variable
        success = self.db.initialize_database()
            
        if success:
            print("Database initialization complete!")
        else:
            print("Failed to initialize database.")
            
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
            # Get both a short snippet and a full answer
            result = self.gemini_search.quick_answer(query)
            
            if "error" in result:
                return result["error"]
                
            # First provide the short snippet followed by the option to hear more
            self.voice.speak(f"Quick answer: {result['snippet']}")
            quick_answer = f"Quick answer: {result['snippet']}"
            # print(f"\nQuick answer: {result['snippet']}")
            
            # Ask if the user wants more details
            print("\nWould you like to hear the full answer? (yes/no)")
            user_choice = input().lower().strip()
            
            if user_choice in ["yes", "y"]:
                return f"Full answer: {result['full_answer']}"
            else:
                return quick_answer + "Okay, ask me if you have any other questions."
        except Exception as e:
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
            definition = self.gemini_search.define_term(term)
            return f"Definition of '{term}': {definition}"
        except Exception as e:
            return f"Error defining the term: {str(e)}"

    def _display_welcome(self, debug_log=None, info_log=None, warn_log=None, error_log=None, refresh_console=True):
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
        print("NOTE: Ctrl + C if you want to quit")
        print("="*50)
        print("---------------------GENERAL INFO----------------------")
        self.stats.display_ram_usage()
        print("------------------------SYSTEM-------------------------")
        self.stats.display_system_overview()
        # print("-------------------------LOG---------------------------")
        # # Add logs if provided via parameters
        # if info_log:
        #     self.logger.info("root", info_log)
        # if debug_log:
        #     self.logger.debug("root", debug_log)
        # if warn_log:
        #     self.logger.warning("root", warn_log)
        # if error_log:
        #     self.logger.error("root", error_log)
        
        # Display the most recent logs
        # self.logger.display_logs()

        print("----------------------ASSISTANT------------------------")
        self.stats.display_date_and_time()
        print("="*50)
        # print("Welcome to NOVA - Your Python-Powered AI Assistant!")
        # print("Remember to start your commands with 'Nova'")
        # print("For example: 'Nova tell me the time'")
        # print("Type 'Nova help' for a list of available commands")
        # print("="*50)
        # print("\n")

    def _handle_help(self, _: str) -> str:
        """Handle the help command"""
        """Return The _show_help function from data.py"""
        return self.typeHandler._show_help()
    
    def _handle_function_list(self, _: str) -> str:
        """Display functionalities of the assistant"""
        return self.typeHandler.display_functions()
    
    def _handle_history(self, _: str) -> str:
        """Display command history"""
        history = self.command_history.get_history()
        if not history:
            return "No command history found."
        else:
            result = "Command History:\n"
            for i, entry in enumerate(history):
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                # Include response in history display if available
                response_info = f"\nResponse: {entry.response}" if entry.response else ""
                result += f"{i+1}: [{timestamp}] {entry.command} ({entry.execution_status}){response_info}\n"
            return result
    
    def _handle_history_start(self, _: str) -> str:
        """Start recording command history"""
        self.command_history.start_recording()
        return "Command history recording started."
    
    def _handle_history_stop(self, _: str) -> str:
        """Stop recording command history"""
        self.command_history.stop_recording()
        return "Command history recording stopped."
    
    def _handle_search_history(self, command: str) -> str:
        """Search command history"""
        match = re.search(r'search\s+(.*)', command, re.IGNORECASE)
        if not match:
            return "Please provide a search term (e.g., 'Nova search weather')"
        
        search_term = match.group(1).strip()
        results = self.command_history.search_history(search_term)
        
        if not results:
            return f"No results found for '{search_term}'."
        else:
            result = f"Search results for '{search_term}':\n"
            for i, entry in enumerate(results):
                timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                # Include response in search results if available
                response_info = f"\nResponse: {entry.response}" if entry.response else ""
                result += f"{i+1}: [{timestamp}] {entry.command}{response_info}\n"
            return result
    
    def _handle_clear_history(self, _: str) -> str:
        """Clear command history"""
        if self.command_history.clear_history():
            return "Command history cleared."
        else:
            return "Failed to clear command history."

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
            if hasattr(self, 'db'):
                self.db.close()
                print("Database connection closed.")
            self._handle_history_stop()
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
            print(f"Failed to record command: {e}")
            
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
            print(f"Failed to save response: {e}")
    
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
        self._handle_history_start("")
        self.initialize_database()
        self.command_history.connect()
        self._display_welcome()  # Display ASCII art and welcome message
        self.voice.speak("Hello, I am Nova, your Python-Powered AI Assistant")
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