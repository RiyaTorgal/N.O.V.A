<div align="center">
  <img src="https://github.com/RiyaTorgal/N.O.V.A/blob/main/img/NOVA.png" />
</div>

# N.O.V.A - An A.I Consciousness

**N.O.V.A** is a voice-commanding assistant service in Python 3.8. It can recognize human speech, interact with users, and execute basic commands.

## Requirements

- **Operating System**: Windows 11  
- **Python Version**: 3.8x

## Assistant Skills

- Opens Web pages (e.g., `Nova open youtube.com`)
- Opens Desktop applications (e.g., `Nova open notepad`)
- Tells Current time (e.g., `Nova tell me the time`)
- Tells Current date (e.g., `Nova tell me the date`)
- Performs Basic calculations (e.g., `Nova calculate 2 + 2`)
- Tells Current weather of a city (e.g., `Nova tell me the weather of Pune`)
- Help command prints all skills with descriptions (e.g., `Nova help`)
- Tells what functions it can perform (e.g., `Nova functions`)

## Assistant Features

- Supports two different user input modes: text or speech. Users can write or speak into the mic.
- Provides vocal and text responses.

## Getting Started

### Creating API Keys for Third-Party APIs

N.O.V.A uses third-party APIs for speech recognition, web searches, weather forecasting, etc. All the following APIs offer free non-commercial API calls. Subscribe to the following APIs to access free keys:

1. **OpenWeatherMap**: API for weather forecasting.

### Setup N.O.V.A in Windows

1. **Download the GitHub repository locally**  
   ```bash
   https://github.com/RiyaTorgal/N.O.V.A.git
   ```
2. **Change the directory**  

   ```bash
   cd .\N.O.V.A\
   ```
### Start the Assistant
<div>
  <img src="https://github.com/RiyaTorgal/N.O.V.A/blob/main/img/NOVA_Output.png" width="800" />
</div>
- Start the Assistant service

   ```bash
   python -u "your\Folder\Location\main.py"
```
## Decision Model
<div>
  <img src="https://github.com/RiyaTorgal/N.O.V.A/blob/main/img/decision%20model.png" width="400" />
</div>

## Contributions
Contributions are welcome! Please fork the repository and submit a pull request with your changes.

## License
This project is licensed under the MIT license - see the LICENSE file for details.
