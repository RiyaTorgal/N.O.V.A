@echo off
title N.O.V.A TTS Server
set PROJECT=D:\Coding\N.O.V.A

cd /d "%PROJECT%"
echo Working folder: %CD%

if not exist ".venv-tts\Scripts\python.exe" (
    echo Cannot find .venv-tts\Scripts\python.exe in %CD%
    pause
    exit /b 1
)

".venv-tts\Scripts\python.exe" -m uvicorn tts_server.server:app --host 127.0.0.1 --port 8020
pause