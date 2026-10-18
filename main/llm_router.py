"""
LLM router for Nova Assistant.

Place this file at: main/llm_router.py   (next to command_handler.py)

Instead of matching exact phrases, the local Ollama model reads what the user
said and picks one of the existing CommandHandlers methods (a "tool"), filling
in its argument. Your handlers still do all the real work: they show the rich
UI and return the text that gets spoken.

Flow:
    "do i need an umbrella in mumbai"
        -> model calls get_weather(city="mumbai")
        -> handle_weather("weather mumbai") runs exactly as before
"""
import json
import os
from typing import Any, Callable, Dict, List, Optional

import ollama
from rich.prompt import Prompt

from src.services.ollama_implementation import _clean_for_speech

DEFAULT_MODEL = "llama3.2:3b"
MAX_TOOL_CALLS = 3      # at most this many actions per request
MAX_HISTORY = 8         # recent messages kept for follow-ups ("and in Delhi?")

SYSTEM_PROMPT = (
    "You are N.O.V.A, a voice assistant running on the user's computer. "
    "Work out what the user wants. For anything that needs an action or live "
    "data (time, date, weather, calculations, opening apps or websites, "
    "system or connection status, command history, definitions), call the "
    "matching tool and never guess those values. For greetings, small talk "
    "and general knowledge questions, answer directly in one to three short "
    "spoken sentences with no markdown, lists or emojis. If the request is "
    "unclear, ask one short clarifying question."
)

# Tools that just return facts. For these, the facts are handed back to the
# model so it can answer the actual question (e.g. "should I carry an umbrella?")
COMPOSE_TOOLS = {"get_weather", "get_time", "get_date", "calculate",
                 "system_status", "connection_status"}

COMPOSE_PROMPT = (
    "You are N.O.V.A, a voice assistant. Answer the user's request using only "
    "the data provided. First state the relevant facts briefly, then answer "
    "any question or give any advice they asked for (for example whether to "
    "carry an umbrella or wear a jacket). Speak naturally in one to three "
    "short sentences with no markdown or lists. The data describes current "
    "conditions only, not a forecast, so do not make claims about later. If "
    "the data does not contain what is needed, say so."
)

# (tool name, description, {parameter name: parameter description})
# Every parameter listed here is required and is a string.
TOOL_DEFS = [
    ("get_time", "Get the current time.", {}),
    ("get_date", "Get today's date.", {}),
    ("calculate", "Evaluate a maths expression.",
        {"expression": "The expression to evaluate, e.g. '25 * 4' or '(2 + 3) ** 2'"}),
    ("get_weather", "Get the current weather for a city.",
        {"city": "City name, e.g. 'Mumbai'"}),
    ("open_target", "Open an application or a website on the computer.",
        {"target": "App name such as 'notepad' or 'chrome', or a website such as 'youtube.com'"}),
    ("define_term", "Give the definition of a word or term.",
        {"term": "The word or term to define"}),
    ("search_history", "Search the user's past commands with Nova.",
        {"term": "Word to look for in past commands"}),
    ("show_history", "Show the user's recent command history.", {}),
    ("clear_history", "Delete the user's entire command history.", {}),
    ("system_status", "Show system information such as RAM usage.", {}),
    ("connection_status", "Check the internet connection and network status.", {}),
    ("show_help", "Show help and the list of things Nova can do.", {}),
]


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a dict or an object (ollama versions differ)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


class LLMRouter:
    """Turns free-form requests into calls to the existing CommandHandlers."""

    def __init__(self, handlers, model: Optional[str] = None, host: Optional[str] = None):
        self.h = handlers
        self.console = handlers.console
        self.ui = handlers.ui
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self.client = ollama.Client(host=host or os.getenv("OLLAMA_HOST") or None)
        # LLM_BACKEND=gemini means "no local model", so the router stays off
        self.enabled = os.getenv("LLM_BACKEND", "ollama").lower() != "gemini"
        # NOVA_COMPOSE=0 skips the second model call (faster, raw handler text)
        self.compose = os.getenv("NOVA_COMPOSE", "1") != "0"
        self.history: List[Dict[str, str]] = []

        h = self.h
        self._runners: Dict[str, Callable[[Dict[str, str]], str]] = {
            "get_time": lambda a: h.handle_time(""),
            "get_date": lambda a: h.handle_date(""),
            "calculate": lambda a: h.handle_calculation(f"calculate {a['expression']}"),
            "get_weather": lambda a: h.handle_weather(f"weather {a['city']}"),
            "open_target": lambda a: h.handle_open(f"open {a['target']}"),
            "define_term": lambda a: h.handle_define(f"define {a['term']}"),
            "search_history": lambda a: h.handle_search_history(f"search {a['term']}"),
            "show_history": lambda a: h.handle_history(""),
            "clear_history": self._clear_history_confirmed,
            "system_status": lambda a: h.handle_system_status(""),
            "connection_status": lambda a: h.handle_connection_status(""),
            "show_help": lambda a: h.handle_help(""),
        }
        self._required = {name: list(params) for name, _, params in TOOL_DEFS}
        self._specs = [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": {
                        "type": "object",
                        "properties": {p: {"type": "string", "description": d}
                                       for p, d in params.items()},
                        "required": list(params),
                    },
                },
            }
            for name, desc, params in TOOL_DEFS
        ]

    # ------------------------------------------------------------------ public
    def route(self, text: str) -> Optional[str]:
        """Handle one request. Returns the text to speak, or None if the
        local model is unavailable or produced nothing usable."""
        if not self.enabled or not text.strip():
            return None

        messages = [{"role": "system", "content": SYSTEM_PROMPT},
                    *self.history,
                    {"role": "user", "content": text}]
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                tools=self._specs,
                options={"temperature": 0, "num_predict": 300},
                keep_alive="30m",
            )
        except Exception as e:
            self.console.print(f"[yellow]Local AI unavailable: {e}[/yellow]")
            return None

        message = _get(response, "message")
        calls = _get(message, "tool_calls") or []

        if calls:
            result, composable = self._run_tools(calls)
            if result:
                if composable and self.compose:
                    result = self._compose(text, result)
                self._remember(text, result)
                return result

        # No tool needed (or none recognised): treat it as conversation
        content = _clean_for_speech(_get(message, "content") or "")
        if not content:
            return None
        try:
            self.ui.display_full_ai_answer(content)
        except Exception:
            self.console.print(content)
        self._remember(text, content)
        return content

    # ---------------------------------------------------------------- internal
    def _run_tools(self, calls):
        """Run the requested tools. Returns (text, only_plain_data)."""
        outputs: List[str] = []
        data_only = True
        for call in list(calls)[:MAX_TOOL_CALLS]:
            fn = _get(call, "function")
            name = _get(fn, "name")
            args = _get(fn, "arguments") or {}
            if isinstance(args, str):           # some versions return JSON text
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}

            runner = self._runners.get(name)
            if runner is None:
                continue                        # unknown tool name: ignore it

            args = {k: str(v).strip() for k, v in dict(args).items()}
            missing = [p for p in self._required[name] if not args.get(p)]
            if missing:
                outputs.append(f"I need the {missing[0]} to do that.")
                data_only = False
                continue

            try:
                outputs.append(runner(args))
                if name not in COMPOSE_TOOLS:
                    data_only = False
            except Exception as e:
                self.console.print(f"[red]Error running {name}: {e}[/red]")
                outputs.append(f"Sorry, {name.replace('_', ' ')} failed.")
                data_only = False
        text = "\n".join(o for o in outputs if o)
        return text, bool(text) and data_only

    def _compose(self, request: str, data: str) -> str:
        """Let the model turn raw tool output into an answer to the request."""
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "system", "content": COMPOSE_PROMPT},
                          {"role": "user", "content": f"Request: {request}\nData:\n{data}"}],
                options={"temperature": 0.2, "num_predict": 150},
                keep_alive="30m",
            )
            answer = _clean_for_speech(_get(_get(response, "message"), "content") or "")
        except Exception:
            return data                      # fall back to the plain handler text
        if not answer:
            return data
        self.console.print(answer, style="bold cyan", markup=False)
        return answer

    def _clear_history_confirmed(self, _args: Dict[str, str]) -> str:
        """Destructive action: always ask first, default to no."""
        answer = Prompt.ask("[bold red]Clear all command history?[/bold red]",
                            choices=["yes", "no"], default="no")
        if answer.lower() != "yes":
            return "Okay, I left your history alone."
        return self.h.handle_clear_history("")

    def _remember(self, user_text: str, reply: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": reply[:300]})
        self.history = self.history[-MAX_HISTORY:]