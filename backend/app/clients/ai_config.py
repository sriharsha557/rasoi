"""
Shared OpenAI / Azure AI Foundry configuration.

Food Buddy uses an OpenAI-compatible endpoint (Azure AI Foundry v1 API). The OpenAI
Python SDK talks to it directly by pointing ``base_url`` at the ``/openai/v1``
path and passing the API key.

Environment variables (set these in Render, never commit the key):
    OPENAI_API_KEY     -> the Azure AI Foundry API key (required)
    OPENAI_BASE_URL    -> the /openai/v1 endpoint (optional, has a default)
    OPENAI_MODEL       -> deployment name, e.g. "gpt-5.5" (optional, has a default)
"""

import os
from openai import AsyncOpenAI, OpenAI

# Azure AI Foundry v1 endpoint (OpenAI-compatible). Overridable via env.
DEFAULT_BASE_URL = "https://IntelligentPantry-ai-foundry.services.ai.azure.com/openai/v1"
DEFAULT_MODEL = "gpt-5.5"


def get_base_url() -> str:
    return os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)


def get_model() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


def get_reasoning_effort() -> str | None:
    """
    Reasoning effort for gpt-5-series models. Lower effort leaves more of the
    completion-token budget for the actual answer and is ideal for structured
    extraction/JSON tasks. Set OPENAI_REASONING_EFFORT="" to omit the parameter
    entirely (e.g. when pointing OPENAI_MODEL at a non-reasoning model).
    Supported by gpt-5.5: none | low | medium | high | xhigh.
    """
    val = os.getenv("OPENAI_REASONING_EFFORT", "low").strip().lower()
    return val or None


def completion_kwargs() -> dict:
    """Extra kwargs passed to chat.completions.create (reasoning_effort if set)."""
    effort = get_reasoning_effort()
    return {"reasoning_effort": effort} if effort else {}



def _require_api_key(api_key: str | None = None) -> str:
    key = api_key or os.getenv("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY environment variable is not set")
    return key


def get_async_client(api_key: str | None = None) -> AsyncOpenAI:
    """Create an async OpenAI client pointed at the Azure AI Foundry endpoint."""
    return AsyncOpenAI(api_key=_require_api_key(api_key), base_url=get_base_url())


def get_sync_client(api_key: str | None = None) -> OpenAI:
    """Create a sync OpenAI client pointed at the Azure AI Foundry endpoint."""
    return OpenAI(api_key=_require_api_key(api_key), base_url=get_base_url())
