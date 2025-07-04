import os
import webbrowser
from datetime import datetime
import re
import requests
import subprocess
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

    # def open_app(self, app_name: str) -> None:
    #     """Open desktop or Microsoft Store app (UWP) dynamically."""
    #     try:
    #         # Step 1: Try common URI-based Store apps
    #         known_uris = {
    #             "netflix": "start netflix:",
    #             "spotify": "start spotify:",
    #             "mail": "start outlookmail:",
    #             "settings": "start ms-settings:"
    #         }

    #         uri_command = known_uris.get(app_name.lower())
    #         if uri_command:
    #             os.system(uri_command)
    #             return

    #         # Step 2: Dynamic AUMID search for store apps
    #         output = subprocess.check_output(
    #             ['powershell', '-Command', 'Get-StartApps'],
    #             universal_newlines=True
    #         )

    #         for line in output.splitlines():
    #             if app_name.lower() in line.lower():
    #                 parts = line.strip().split(None, 1)
    #                 if len(parts) == 2:
    #                     aumid = parts[1]
    #                     os.system(f'start shell:AppsFolder\\{aumid}')
    #                     return

    #         # Step 3: Fallback to classic .exe launch
    #         os.startfile(app_name)
    #     except Exception as e:
    #         raise AssistantError(f"Failed to open '{app_name}': {e}")
    def open_app(self, app_name: str) -> None:
        """Open application with improved error handling"""
        try:
            if app_name.lower() == "settings":
                os.startfile("ms-settings:")
            else:
                os.startfile(app_name)
        except Exception as e:
            raise AppOperationError(f"Failed to open {app_name}: {e}")

        
    def play_media(self, query: str, media_type: str, platform: str) -> None:
        """
        Play media using either youtube or spotify."""
        if platform.lower() == "spotify":
            search_url = f"https://open.spotify.com/search/{query.replace(' ', '%20')}"
        elif platform.lower() == "youtube":
            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        else:
            raise AppOperationError(f"Unsupported platform: {platform}")
        webbrowser.open(search_url)

    def handle_open_media_command(self, command: str) -> str:
        """
        Handles commands like:
        'open [media name] song/video on spotify/youtube'
        """
        match = re.match(r"open (.+) (song|video) on (spotify|youtube)", command, re.IGNORECASE)
        if not match:
            return "Invalid command format. Use 'open [name] song/video on [platform]'."
        
        media_name = match.group(1).strip()
        media_type = match.group(2).strip()
        platform = match.group(3).strip()

        try:
            self.play_media(media_name, media_type, platform)
            return f"Opening {media_type} '{media_name}' on {platform.capitalize()}."
        except AssistantError as e:
            return str(e)

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