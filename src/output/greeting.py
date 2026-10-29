"""Pre-rendered startup greeting, so the first words don't wait on XTTS.

Place this file at: src/output/greeting.py
Generate the wav once with:  python -m scripts.make_greeting
Re-run that script whenever you change GREETING_TEXT, the voice sample or the speed.
"""
from pathlib import Path

# src/output/greeting.py -> project root is two folders up
ROOT = Path(__file__).resolve().parents[2]

GREETING_TEXT = "Hello, I am Nova, your Python-Powered AI Assistant"
GREETING_PATH = ROOT / "assets" / "greeting.wav"


def play_greeting() -> bool:
    """Play the saved greeting. Returns True if it played, False if the file is
    missing or couldn't be played (caller should then speak the text instead)."""
    if not GREETING_PATH.exists():
        return False
    try:
        import sounddevice as sd
        import soundfile as sf

        data, sample_rate = sf.read(str(GREETING_PATH), dtype="float32")
        sd.play(data, sample_rate)
        sd.wait()
        return True
    except Exception as e:
        print(f"[greeting] could not play {GREETING_PATH.name}: {type(e).__name__}: {e}")
        return False