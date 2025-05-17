import socket
import urllib.request
import urllib.error
import psutil
from typing import Dict, List, Tuple, Optional

class ConnectionMonitor:
    """
    Utility class to monitor various connection states and hardware availability
    for the NOVA assistant.
    """
    
    def __init__(self):
        """Initialize the ConnectionMonitor"""
        self.last_connectivity_status = False
    
    def check_internet_connection(self, test_url: str = "https://www.google.com", timeout: int = 3) -> bool:
        """
        Check if internet connection is available by trying to connect to a URL.
        
        Args:
            test_url: URL to test connection with
            timeout: Connection timeout in seconds
            
        Returns:
            bool: True if connection is available, False otherwise
        """
        try:
            urllib.request.urlopen(test_url, timeout=timeout)
            if not self.last_connectivity_status:
                self.last_connectivity_status = True
            return True
        except (urllib.error.URLError, socket.timeout, ConnectionRefusedError):
            if self.last_connectivity_status:
                self.last_connectivity_status = False
            return False
    
    def get_network_stats(self) -> Dict:
        """
        Get network statistics.
        
        Returns:
            Dict: Dictionary containing network statistics
        """
        network_stats = {}
        try:
            net_io = psutil.net_io_counters()
            network_stats = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "errin": net_io.errin,
                "errout": net_io.errout,
                "dropin": net_io.dropin,
                "dropout": net_io.dropout
            }
        except Exception:
            # If we can't get network stats, return empty dict
            pass
        
        return network_stats
    
    def check_input_device_availability(self) -> Dict[str, bool]:
        """
        Check availability of input devices like microphone.
        
        Returns:
            Dict[str, bool]: Dictionary with device types as keys and availability as values
        """
        device_status = {
            "microphone": False,
            "keyboard": True  # Keyboard is assumed to be always available
        }
        
        # Check for microphone
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
            device_status["microphone"] = True
        except (ImportError, AttributeError, TypeError, ValueError):
            device_status["microphone"] = False
            
        return device_status
    
    def check_text_to_speech_availability(self) -> bool:
        """
        Check if text-to-speech functionality is available.
        
        Returns:
            bool: True if TTS is available, False otherwise
        """
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            return len(voices) > 0
        except (ImportError, Exception):
            return False
            
    def get_complete_status(self) -> Dict:
        """
        Get a complete status report of all monitored systems.
        
        Returns:
            Dict: Complete status information
        """
        input_devices = self.check_input_device_availability()
        
        return {
            "internet_connection": self.check_internet_connection(),
            "network_stats": self.get_network_stats(),
            "input_devices": input_devices,
            "text_to_speech": self.check_text_to_speech_availability(),
            "voice_input_available": input_devices.get("microphone", False),
            "text_input_available": input_devices.get("keyboard", True)
        }