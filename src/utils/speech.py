"""Place this file at: src/utils/speech.py"""
import re


def clean_for_speech(text: str) -> str:
    """Strip markdown symbols so text-to-speech doesn't read them out."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"[*_`#>]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()