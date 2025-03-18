from dataclasses import dataclass
import requests
from src.core.exceptions import WeatherAPIError

@dataclass
class WeatherData:
    description: str
    temperature: float
    temp_min: float
    temp_max: float
    city: str

    def __str__(self) -> str:
        return (f"The weather of {self.city} is {self.description}. "
                f"The current temperature is {self.temperature}°C. "
                f"The high for today is {self.temp_max}°C, and the low is {self.temp_min}°C.")

class WeatherAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_weather(self, city: str) -> WeatherData:
        URL = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            'q': city,
            'appid': self.api_key,
            'units': 'metric'
        }
        
        try:
            response = requests.get(URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            return WeatherData(
                description=data['weather'][0]['description'],
                temperature=data['main']['temp'],
                temp_min=data['main']['temp_min'],
                temp_max=data['main']['temp_max'],
                city=city
            )
        except requests.RequestException as e:
            raise WeatherAPIError(f"Failed to fetch weather data: {e}")
        except (KeyError, IndexError) as e:
            raise WeatherAPIError(f"Invalid weather data format: {e}")