"""
Shared Anthropic Claude configuration.

Food Buddy talks to the Claude API directly via the official Anthropic Python SDK.

Environment variables (set these in Render, never commit the key):
    ANTHROPIC_API_KEY  -> the Claude API key (required)
    ANTHROPIC_MODEL    -> model id (optional, defaults to claude-opus-4-8)
"""

import os
from anthropic import Anthropic, AsyncAnthropic

DEFAULT_MODEL = "claude-opus-4-8"


def get_model() -> str:
    return os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL)


def _require_api_key(api_key: str | None = None) -> str:
    key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")
    return key


def get_async_client(api_key: str | None = None) -> AsyncAnthropic:
    """Create an async Anthropic client."""
    return AsyncAnthropic(api_key=_require_api_key(api_key))


def get_sync_client(api_key: str | None = None) -> Anthropic:
    """Create a sync Anthropic client."""
    return Anthropic(api_key=_require_api_key(api_key))
