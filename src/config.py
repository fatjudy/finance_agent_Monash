from __future__ import annotations
import os
import anthropic
from dotenv import load_dotenv

load_dotenv()      # reads a .env file in the project root into environment variables

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
MAX_STEPS = int(os.environ.get("AGENT_MAX_STEPS", "12"))

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()      # reads ANTHROPIC_API_KEY from env
    return _client