import speech_recognition as sr
import pyttsx3
import time
from src.input.text_handler import CommandParser, InputHistory, Command, InputMethod,TypedInputHandler

class VoiceAssistant:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.history = InputHistory()
        self.parser = CommandParser()
        self.handler = TypedInputHandler()

    def get_input_method(self) -> callable:
        """Get user's preferred input method"""
        while True:
            print("\nAvailable input methods:")
            print("1. type - Type commands using keyboard")
            print("2. speak - Use voice commands")
            
            choice = input("\nChoose input method (type/speak): ").lower().strip()
            
            if choice == InputMethod.SPEAK.value:
                self.speak("Now listening. Remember to start your command with 'Nova'")
                return self.listen
            elif choice == InputMethod.TYPE.value:
                print(self.typed_handler._show_help())
                return self.typed_handler.get_input
            
            print("Invalid choice. Please choose 'speak' or 'type'")

    def listen(self) -> str:
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5)
                query = self.recognizer.recognize_google(audio, language="en-in")
                print(f"You said: {query}")
                
                is_valid, command = self.parser.parse_command(query)
                if not is_valid:
                    self.speak("Please start your command with 'Nova'")
                    return ""
                
                normalized_command = self.parser.normalize_command(command)
                self.history.add(Command(
                    text=query,
                    timestamp=time.time(),
                    source=InputMethod.SPEAK
                ))
                
                return normalized_command
                
            except (sr.UnknownValueError, sr.RequestError, Exception) as e:
                return f"Error: {str(e)}"

    def speak(self, text: str) -> None:
        self.engine.say(text)
        self.engine.runAndWait()