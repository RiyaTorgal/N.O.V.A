"""Voice/typed input + spoken output for N.O.V.A.

Place this file at: src/input/voice_handler.py
"""
import time

import speech_recognition as sr

from src.input.text_handler import (
    CommandParser,
    InputHistory,
    Command,
    InputMethod,
    TypedInputHandler,
)
from src.output.tts_engine import create_tts_engine


class VoiceAssistant:
    def __init__(self, tts=None):
        self.recognizer = sr.Recognizer()
        # One shared TTS engine (XTTS cloned voice with pyttsx3 fallback).
        # Pass your own engine in if main.py already created one, so the
        # greeting and the replies use the SAME voice.
        self.tts = tts or create_tts_engine()
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
                print(self.handler._show_help())
                return self.handler.get_input

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
                    source=InputMethod.SPEAK,
                ))

                return normalized_command

            except (sr.UnknownValueError, sr.RequestError, Exception) as e:
                print(f"[listen] {type(e).__name__}: {e}")
                return f"Error: {str(e)}"

    def speak(self, text: str) -> None:
        """Print AND speak. Every reply should go through here."""
        if not text:
            return
        # print(f"N.O.V.A: {text}")
        try:
            self.tts.speak(text)
        except Exception as e:
            # Never let a TTS problem kill the assistant loop, but never hide it either
            print(f"[speak] TTS error: {type(e).__name__}: {e}")