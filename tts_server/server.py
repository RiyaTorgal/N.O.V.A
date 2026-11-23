"""
N.O.V.A TTS server: loads XTTS-v2 onto the GPU once and keeps it there.

Run from the project root (inside .venv-tts):
    python -m uvicorn tts_server.server:app --host 127.0.0.1 --port 8020

The port only opens AFTER the model is loaded, the voice is analysed and the
warm-up is done, so "server reachable" == "server ready".
"""
import os
import re
import threading
import time
from pathlib import Path

import numpy as np
import torch
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent.parent
# Load settings BEFORE importing TTS so TTS_HOME / HF_HOME are picked up
load_dotenv(ROOT / "config" / ".env")

from TTS.api import TTS  # noqa: E402


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


VOICE = _resolve(os.getenv("NOVA_VOICE_SAMPLE", "ai-models/voices/new-voice-updated.wav"))
if not VOICE.exists():
    raise SystemExit(f"Voice sample not found: {VOICE} (set NOVA_VOICE_SAMPLE in config/.env)")

def _boost_process() -> None:
    """Windows: ask for above-normal priority and opt out of power/efficiency
    throttling, which can slow a background console process on laptops.
    Best effort only: failures are printed and ignored."""
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.SetProcessInformation.argtypes = [
            wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        handle = k32.GetCurrentProcess()
        ok_prio = bool(k32.SetPriorityClass(handle, 0x00008000))  # ABOVE_NORMAL

        class _PowerThrottling(ctypes.Structure):
            _fields_ = [("Version", wintypes.ULONG),
                        ("ControlMask", wintypes.ULONG),
                        ("StateMask", wintypes.ULONG)]

        state = _PowerThrottling(1, 1, 0)  # control execution-speed throttling, set OFF
        ok_thr = bool(k32.SetProcessInformation(
            handle, 4, ctypes.byref(state), ctypes.sizeof(state)))  # 4 = ProcessPowerThrottling
        print(f"[tts-server] priority raised: {ok_prio}, throttling disabled: {ok_thr}", flush=True)
    except Exception as e:  # never block startup on this
        print(f"[tts-server] could not adjust process priority ({e})", flush=True)


_boost_process()

DEVICE = os.getenv("NOVA_TTS_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")

# TF32 matmuls: free speed-up on RTX 30-series cards (small, inaudible precision change).
# Set NOVA_TTS_TF32=0 in config/.env to turn it off and compare.
if DEVICE == "cuda" and os.getenv("NOVA_TTS_TF32", "1") == "1":
    torch.set_float32_matmul_precision("high")
    print("[tts-server] TF32 matmul enabled", flush=True)

t0 = time.time()
print(f"[tts-server] Loading XTTS-v2 on {DEVICE} ...", flush=True)
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(DEVICE)
model = tts.synthesizer.tts_model
SAMPLE_RATE = tts.synthesizer.output_sample_rate

# Voice "fingerprint": computed ONCE, reused for every request
cfg = model.config
gpt_cond, spk_emb = model.get_conditioning_latents(
    audio_path=[str(VOICE)],
    gpt_cond_len=cfg.gpt_cond_len,
    max_ref_length=cfg.max_ref_len,
    sound_norm_refs=cfg.sound_norm_refs,
)

# Warm-up: pay the one-off GPU start-up costs now, not on the first reply
model.inference("Ready.", "en", gpt_cond, spk_emb)
print(f"[tts-server] Ready in {time.time() - t0:.1f}s", flush=True)

# Tell the assistant's autostart logic that loading is finished
try:
    (ROOT / "tts_server" / ".starting").unlink(missing_ok=True)
except OSError:
    pass

_gpu_lock = threading.Lock()  # one synthesis at a time on a 4 GB card
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

app = FastAPI(title="N.O.V.A TTS")


class SynthRequest(BaseModel):
    text: str
    lang: str = "en"
    speed: float = 1.0


@app.get("/health")
def health():
    return {"status": "ok", "sample_rate": SAMPLE_RATE}


@app.post("/synthesize")
def synthesize(req: SynthRequest):
    """One piece of text -> the whole waveform as raw float32 mono PCM.
    The client does the pipelining (same approach as the old in-process engine)."""
    with _gpu_lock:
        t = time.time()
        out = model.inference(
            req.text,
            req.lang,
            gpt_cond,
            spk_emb,
            speed=req.speed,
            enable_text_splitting=False,
        )
        took = time.time() - t
    wav = np.asarray(out["wav"], dtype=np.float32)
    audio_s = len(wav) / SAMPLE_RATE
    print(
        f"[tts-server] {len(req.text.split())} words -> {audio_s:.1f}s audio "
        f"in {took:.1f}s (x{took / max(audio_s, 0.01):.2f} of real time)",
        flush=True,
    )
    return Response(content=wav.tobytes(), media_type="application/octet-stream")


@app.post("/speak")
def speak(req: SynthRequest):
    """Streaming endpoint (raw int16 mono PCM). Handy for quick tests;
    N.O.V.A itself uses /synthesize."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(req.text) if s.strip()]

    def gen():
        with _gpu_lock:
            for sentence in sentences:
                for chunk in model.inference_stream(
                    sentence,
                    req.lang,
                    gpt_cond,
                    spk_emb,
                    stream_chunk_size=40,
                    speed=req.speed,
                    enable_text_splitting=False,
                ):
                    pcm = (chunk.clamp(-1, 1) * 32767).to(torch.int16).cpu().numpy()
                    yield pcm.tobytes()

    return StreamingResponse(gen(), media_type="application/octet-stream")