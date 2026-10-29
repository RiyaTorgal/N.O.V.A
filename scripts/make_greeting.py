"""One-time script: render the startup greeting in your cloned voice.

Place this file at: scripts/make_greeting.py
Run from the project root (D:\\Coding\\N.O.V.A):

    python scripts/make_greeting.py
or  python -m scripts.make_greeting

Takes ~45s (it has to load XTTS once). Re-run whenever you change
GREETING_TEXT in src/output/greeting.py, the voice sample, or NOVA_SPEED.
"""
import sys
from pathlib import Path

# Make `src` importable when run as a plain script
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import soundfile as sf

from src.output.greeting import GREETING_PATH, GREETING_TEXT
from src.output.tts_engine import create_tts_engine


def main() -> None:
    engine = create_tts_engine().wait()          # blocks until XTTS has loaded
    xtts = getattr(engine, "primary", engine)    # unwrap SafeTTS -> XTTSEngine

    if not hasattr(xtts, "model"):
        raise SystemExit(
            "XTTS isn't the active engine (it fell back to pyttsx3?). "
            "Set NOVA_TTS=xtts in config/.env and check the log above."
        )

    out = xtts.model.inference(
        GREETING_TEXT,
        xtts.language,
        xtts.gpt_cond_latent,
        xtts.speaker_embedding,
        speed=xtts.speed,
        enable_text_splitting=False,
    )
    wav = np.asarray(out["wav"], dtype=np.float32)

    if xtts.semitones:
        import librosa

        wav = librosa.effects.pitch_shift(wav, sr=xtts.sample_rate, n_steps=xtts.semitones)

    GREETING_PATH.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(GREETING_PATH), wav, xtts.sample_rate, subtype="PCM_16")
    print(f"Saved {GREETING_PATH}  ({len(wav) / xtts.sample_rate:.1f}s of audio)")


if __name__ == "__main__":
    main()