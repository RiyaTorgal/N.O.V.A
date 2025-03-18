import os
import webbrowser
from datetime import datetime
import re
import requests
from typing import Tuple
from src.core.exceptions import AssistantError, AppOperationError,WeatherAPIError
from src.input.text_handler import TypedInputHandler
from src.input.voice_handler import VoiceAssistant

class Assistant:
    def __init__(self):
        # self.api_key = os.environ.get("API_KEY")
        # if not self.api_key:
        #     raise AssistantError("API key not found in environment variables")
        # self.weather_api = WeatherAPI(self.api_key)
        self.voice_assistant = VoiceAssistant()
        self.typed_handler = TypedInputHandler()
        
    def open_website(self, url: str) -> None:
        """Open website with error handling and URL validation"""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        try:
            webbrowser.open(url)
        except Exception as e:
            raise AppOperationError(f"Failed to open website: {e}")

    def open_app(self, app_name: str) -> None:
        """Open application with improved error handling"""
        try:
            if app_name.lower() == "settings":
                os.startfile("ms-settings:")
            else:
                os.startfile(app_name)
        except Exception as e:
            raise AppOperationError(f"Failed to open {app_name}: {e}")

    def get_datetime(self) -> Tuple[str, str]:
        """Get current time and date"""
        now = datetime.now()
        return now.strftime("%H:%M"), now.strftime("%Y-%m-%d")

    def calculate(self, expression: str) -> float:
        """Safe mathematical expression evaluation"""
        # Whitelist of allowed characters for basic arithmetic
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            raise ValueError("Invalid characters in expression")
        try:
            result = eval(expression, {"__builtins__": {}})
            return float(result)
        except Exception as e:
            raise ValueError(f"Invalid expression: {e}")