"""Thin client for the N.O.V.A TTS server (tts_server/server.py)."""
import os
import time

import numpy as np
import requests

SERVER_URL = os.getenv("TTS_SERVER_URL", "http://127.0.0.1:8020")
_sample_rate: int | None = None


def is_ready(timeout: float = 0.5) -> bool:
    """True if the server is up (it only listens once the model is loaded)."""
    try:
        return requests.get(f"{SERVER_URL}/health", timeout=timeout).ok
    except requests.RequestException:
        return False


def wait_until_ready(timeout: float = 180, poll: float = 1.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_ready():
            return True
        time.sleep(poll)
    return False


def get_sample_rate() -> int:
    global _sample_rate
    if _sample_rate is None:
        r = requests.get(f"{SERVER_URL}/health", timeout=2)
        r.raise_for_status()
        _sample_rate = int(r.json().get("sample_rate", 24000))
    return _sample_rate


def synthesize(text: str, lang: str = "en", speed: float = 1.0) -> np.ndarray:
    """Generate one piece of speech; returns a float32 mono waveform."""
    r = requests.post(
        f"{SERVER_URL}/synthesize",
        json={"text": text, "lang": lang, "speed": speed},
        timeout=(3, 120),
    )
    r.raise_for_status()
    return np.frombuffer(r.content, dtype=np.float32).copy()


def speak(text: str, lang: str = "en", speed: float = 1.0) -> None:
    """Quick-test helper: stream audio from /speak and play it as it arrives."""
    import sounddevice as sd

    leftover = b""
    with requests.post(
        f"{SERVER_URL}/speak",
        json={"text": text, "lang": lang, "speed": speed},
        stream=True,
        timeout=(3, 120),
    ) as r:
        r.raise_for_status()
        with sd.RawOutputStream(samplerate=get_sample_rate(), channels=1, dtype="int16") as out:
            for chunk in r.iter_content(chunk_size=4096):
                if not chunk:
                    continue
                data = leftover + chunk
                usable = len(data) - (len(data) % 2)  # keep whole int16 samples
                leftover = data[usable:]
                if usable:
                    out.write(data[:usable])