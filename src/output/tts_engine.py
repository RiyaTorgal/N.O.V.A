"""Text-to-speech engines for N.O.V.A.

Place this file at: src/output/tts_engine.py
(NOTE: the filename must use an underscore, not a hyphen, or Python can't import it.)
"""
import os
import re
import sys
import threading
import time
import traceback
from abc import ABC, abstractmethod
from pathlib import Path

from dotenv import load_dotenv

# src/output/tts_engine.py -> project root is two folders up
ROOT = Path(__file__).resolve().parents[2]

# Load settings before TTS is imported, so TTS_HOME / HF_HOME are picked up
load_dotenv(ROOT / "config" / ".env")


def _log(msg: str) -> None:
    """Always-visible CLI log line."""
    print(f"[TTS] {msg}", file=sys.stderr, flush=True)


def _resolve(path_str: str) -> Path:
    """Relative paths in .env are resolved against the project root."""
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


class TTSEngine(ABC):
    @abstractmethod
    def speak(self, text: str) -> None:
        ...


class Pyttsx3Engine(TTSEngine):
    """Windows system voices (David, Hazel, Zira...). Fast, robotic, always available."""

    def __init__(self, voice_name: str | None = None, rate: int = 175):
        import pyttsx3

        self.voice_name = voice_name
        self.rate = rate
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self.engine.setProperty("volume", 1.0)
        if voice_name:
            for v in self.engine.getProperty("voices"):
                if voice_name.lower() in v.name.lower():
                    self.engine.setProperty("voice", v.id)
                    break
            else:
                _log(f"Voice '{voice_name}' not found, using default.")

    def speak(self, text: str) -> None:
        if not text or not text.strip():
            return
        self.engine.say(text)
        self.engine.runAndWait()


class XTTSEngine(TTSEngine):
    """Your cloned voice via XTTS-v2. Natural, but slower and needs VRAM."""

    def __init__(
        self,
        voice_sample: str,
        speed: float = 1.0,
        semitones: float = 0.0,
        language: str = "en",
        device: str | None = None,
    ):
        import torch
        from TTS.api import TTS

        if not os.path.exists(voice_sample):
            raise FileNotFoundError(f"Voice sample not found: {voice_sample}")

        self.voice_sample = voice_sample
        self.speed = speed
        self.semitones = semitones
        self.language = language

        device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.device = device
        _log(f"Loading XTTS on {device}...")
        self.tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
        self.sample_rate = self.tts.synthesizer.output_sample_rate

        # Compute the voice "fingerprint" ONCE. The slow path (tts.tts with
        # speaker_wav=...) re-reads and re-analyses the wav on every sentence.
        self.model = self.tts.synthesizer.tts_model
        cfg = self.model.config
        self.gpt_cond_latent, self.speaker_embedding = self.model.get_conditioning_latents(
            audio_path=[voice_sample],
            gpt_cond_len=cfg.gpt_cond_len,
            max_ref_length=cfg.max_ref_len,
            sound_norm_refs=cfg.sound_norm_refs,
        )

        # Warm-up: the very first synthesis pays one-off GPU start-up costs
        # (kernel setup, memory allocation). Pay them now, not on the greeting.
        try:
            t0 = time.time()
            self.model.inference(
                "Ready.", self.language, self.gpt_cond_latent, self.speaker_embedding
            )
            _log(f"warm-up done in {time.time() - t0:.1f}s")
        except Exception as e:
            _log(f"warm-up skipped ({type(e).__name__}: {e})")
        _log("XTTS loaded.")

    @staticmethod
    def _split(text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p for p in parts if p]

    def _plan_chunks(self, text: str) -> list[str]:
        """Split text so the FIRST piece is short (fast to generate) and later
        pieces grow, so each one is ready before the previous one finishes playing.
        NOVA_TTS_FIRST_WORDS=0 disables this and speaks whole sentences."""
        first = int(os.getenv("NOVA_TTS_FIRST_WORDS", "6"))
        sentences = self._split(text)
        if first <= 0:
            return sentences

        chunks: list[str] = []
        budget = first
        for sentence in sentences:
            words = sentence.split()
            while words:
                if len(words) <= budget * 1.4 + 1:
                    chunks.append(" ".join(words))
                    words = []
                else:
                    cut = budget
                    lo, hi = max(3, budget - 2), min(len(words) - 2, budget + 2)
                    for i in range(lo, hi + 1):  # prefer a natural pause near the budget
                        if words[i - 1].endswith((",", ";", ":")):
                            cut = i
                            break
                    chunks.append(" ".join(words[:cut]))
                    words = words[cut:]
                budget = min(int(budget * 1.7), 16)  # grow gently so pieces stay ahead of playback
        return chunks

    def speak(self, text: str) -> None:
        if not text or not text.strip():
            return
        # Pitch shifting needs the whole clip, so it can't be pipelined/streamed.
        if self.semitones:
            return self._speak_blocking(text)

        played = [False]  # set once any audio has actually been heard
        try:
            if os.getenv("NOVA_TTS_STREAM", "0") == "1":
                self._speak_streaming(text, played)
            else:
                self._speak_pipelined(text, played)
        except Exception as e:
            if played[0]:
                # Already spoke part of it; don't repeat the whole reply.
                _log(f"playback interrupted ({type(e).__name__}: {e})")
                return
            _log(f"fast path failed ({type(e).__name__}: {e}); using slow path")
            self._speak_blocking(text)

    def _speak_pipelined(self, text: str, played: list) -> None:
        """Smooth playback: synthesise sentence N+1 in a background thread while
        sentence N is playing. Each sentence is generated whole, so there are no
        chunk-boundary clicks or buffer underruns inside a sentence."""
        import queue

        import numpy as np
        import sounddevice as sd

        sentences = self._plan_chunks(text)
        q: queue.Queue = queue.Queue(maxsize=2)
        errors: list = []

        def producer() -> None:
            try:
                for sentence in sentences:
                    out = self.model.inference(
                        sentence,
                        self.language,
                        self.gpt_cond_latent,
                        self.speaker_embedding,
                        speed=self.speed,
                        enable_text_splitting=False,
                    )
                    q.put(np.asarray(out["wav"], dtype=np.float32))
            except Exception as e:  # reported on the playing thread
                errors.append(e)
            finally:
                q.put(None)

        t0 = time.time()
        worker = threading.Thread(target=producer, daemon=True)
        worker.start()

        first = True
        while True:
            wav = q.get()
            if wav is None:
                break
            if first:
                _log(f"first audio after {time.time() - t0:.1f}s")
                first = False
            played[0] = True
            sd.play(wav, self.sample_rate)
            sd.wait()

        worker.join()
        if errors:
            raise errors[0]

    def _speak_streaming(self, text: str, played: list) -> None:
        """Lower first-sound delay, but needs a GPU fast enough to stay ahead of
        playback. Buffers NOVA_TTS_PREBUFFER seconds first so it doesn't stutter."""
        import numpy as np
        import sounddevice as sd

        prebuffer = int(float(os.getenv("NOVA_TTS_PREBUFFER", "2.0")) * self.sample_rate)
        t0 = time.time()
        pending: list = []
        buffered = 0
        started = False

        with sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as out:
            for sentence in self._split(text):
                for chunk in self.model.inference_stream(
                    sentence,
                    self.language,
                    self.gpt_cond_latent,
                    self.speaker_embedding,
                    stream_chunk_size=40,
                    speed=self.speed,
                    enable_text_splitting=False,
                ):
                    audio = chunk.detach().cpu().numpy().astype(np.float32).reshape(-1, 1)
                    if not started:
                        pending.append(audio)
                        buffered += len(audio)
                        if buffered >= prebuffer:
                            started = True
                            _log(f"first audio after {time.time() - t0:.1f}s")
                            played[0] = True
                            for a in pending:
                                out.write(a)
                            pending = []
                    else:
                        out.write(audio)
            for a in pending:  # short reply that never hit the prebuffer size
                played[0] = True
                out.write(a)

    def _speak_blocking(self, text: str) -> None:
        """Original method: generate each sentence fully, then play it."""
        import numpy as np
        import sounddevice as sd

        for chunk in self._split(text):
            wav = self.tts.tts(
                text=chunk,
                speaker_wav=self.voice_sample,
                language=self.language,
                speed=self.speed,
            )
            wav = np.asarray(wav, dtype=np.float32)

            if self.semitones:
                import librosa

                wav = librosa.effects.pitch_shift(
                    wav, sr=self.sample_rate, n_steps=self.semitones
                )

            sd.play(wav, self.sample_rate)
            sd.wait()


class SafeTTS(TTSEngine):
    """Wraps a primary engine. If it fails while speaking (e.g. CUDA out of
    memory after the LLM loads), log the real error and fall back so the
    assistant never goes silent."""

    def __init__(self, primary: TTSEngine, fallback_factory):
        self.primary = primary
        self._fallback_factory = fallback_factory
        self._fallback: TTSEngine | None = None
        self._lock = threading.Lock()  # one utterance at a time, any thread

    def speak(self, text: str) -> None:
        if not text or not text.strip():
            return

        with self._lock:
            _log(f"speaking ({type(self.primary).__name__}): {text[:60]!r}")
            try:
                self.primary.speak(text)
                return
            except Exception as e:
                _log(f"{type(self.primary).__name__} FAILED: {type(e).__name__}: {e}")
                traceback.print_exc()
                self._free_gpu()

            # Fallback path
            try:
                if self._fallback is None:
                    self._fallback = self._fallback_factory()
                _log(f"falling back to {type(self._fallback).__name__}")
                self._fallback.speak(text)
            except Exception as e:
                _log(f"Fallback also FAILED: {type(e).__name__}: {e}")
                traceback.print_exc()

    @staticmethod
    def _free_gpu() -> None:
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


_ENGINE: TTSEngine | None = None


def create_tts_engine() -> TTSEngine:
    """Return the ONE shared engine (built on first call, reused after).

    Your log showed the engine being created twice at startup; with XTTS that
    would load the model twice and waste ~2-3 GB of VRAM.
    """
    global _ENGINE
    if _ENGINE is None:
        _log(f"building the shared engine (module name: {__name__}); called from:")
        traceback.print_stack(limit=4, file=sys.stderr)  # remove once the double-load is gone
        _ENGINE = _build_tts_engine()
    return _ENGINE


def _build_tts_engine() -> TTSEngine:
    """Pick the engine from config/.env. Falls back to pyttsx3 if XTTS fails."""
    kind = os.getenv("NOVA_TTS", "pyttsx3").lower()
    _log(f"NOVA_TTS={kind!r}")

    def make_pyttsx3() -> Pyttsx3Engine:
        return Pyttsx3Engine(os.getenv("NOVA_VOICE"))

    if kind == "xtts":
        try:
            sample = _resolve(
                os.getenv("NOVA_VOICE_SAMPLE", "ai-models/voices/new-voice-updated.wav")
            )
            xtts = XTTSEngine(
                voice_sample=str(sample),
                speed=float(os.getenv("NOVA_SPEED", "1.0")),
                semitones=float(os.getenv("NOVA_SEMITONES", "0")),
                device=os.getenv("NOVA_TTS_DEVICE") or None,
            )
            return SafeTTS(xtts, make_pyttsx3)
        except Exception as e:
            _log(f"XTTS failed to load ({type(e).__name__}: {e}). Falling back to pyttsx3.")
            traceback.print_exc()

    return make_pyttsx3()


if __name__ == "__main__":
    create_tts_engine().speak("Hello, I am Nova. The voice engine is working.")