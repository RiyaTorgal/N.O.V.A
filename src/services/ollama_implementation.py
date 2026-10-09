"""Local (Ollama) replacement for GeminiSearch, plus a backend picker.

Place this file at: src/services/local_ai.py

Backend is chosen with the LLM_BACKEND environment variable:
    ollama  -> always use the local model (default, works offline)
    gemini  -> always use Gemini (needs internet + GEMINI key)
    auto    -> use Ollama if it is running, otherwise fall back to Gemini
"""
import os
import re
from typing import Dict, Optional

import ollama

DEFAULT_MODEL = "llama3.2:3b"

SYSTEM_PROMPT = (
    "You are N.O.V.A, a voice assistant. Your answers are read aloud, so "
    "reply in plain spoken English: 1 to 3 short sentences, no markdown, "
    "no bullet points, no emojis. If the question is ambiguous, answer the "
    "most likely meaning. If you do not know, say so briefly."
)


def _clean_for_speech(text: str) -> str:
    """Strip markdown symbols so text-to-speech doesn't read them out."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


class OllamaSearch:
    """Same interface as GeminiSearch, backed by a local Ollama model."""

    def __init__(self, model: Optional[str] = None, host: Optional[str] = None) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self.client = ollama.Client(host=host or os.getenv("OLLAMA_HOST") or None)

    def _ask(self, prompt: str, max_tokens: int = 200, temperature: float = 0.2) -> str:
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            options={"temperature": temperature, "num_predict": max_tokens},
            keep_alive="30m",  # keep the model loaded so later answers are fast
        )
        return _clean_for_speech(response["message"]["content"])

    def is_available(self) -> bool:
        """True if the Ollama server is running and the model is pulled."""
        try:
            models = self.client.list()
            names = [m.get("model", "") or m.get("name", "") for m in models.get("models", [])]
            return any(n.split(":")[0] == self.model.split(":")[0] and
                       (":" not in self.model or n == self.model) for n in names)
        except Exception:
            return False

    def search(self, query: str) -> str:
        """Answer a question."""
        try:
            return self._ask(query)
        except Exception as e:
            return f"Search error: {e}"

    def quick_answer(self, query: str) -> Dict[str, str]:
        """Return a one-sentence snippet and a fuller answer."""
        try:
            snippet = self._ask(
                f"Answer in one short sentence: {query}", max_tokens=60, temperature=0.1
            )
            return {"snippet": snippet, "full_answer": self.search(query)}
        except Exception as e:
            return {"error": f"Quick answer error: {e}"}

    def define_term(self, term: str) -> str:
        """Define a term."""
        try:
            return self._ask(f"Define '{term}' clearly in one or two sentences.")
        except Exception as e:
            return f"Definition error: {e}"


def get_search_engine():
    """Return an object with search(), quick_answer() and define_term().

    Use this instead of GeminiSearch() wherever the assistant is set up.
    """
    backend = os.getenv("LLM_BACKEND", "ollama").lower()

    if backend == "gemini":
        from src.services.gemini_implementation import GeminiSearch  # lazy import
        return GeminiSearch()

    local = OllamaSearch()
    if backend == "ollama":
        return local

    # backend == "auto"
    if local.is_available():
        return local
    from src.services.gemini_implementation import GeminiSearch
    return GeminiSearch()