"""Which LLM backs the chat agents (dog + G1): Grok (xAI), through the Responses API.

    XAI_API_KEY, GROK_MODEL (default grok-4.5), GROK_REASONING_EFFORT (default low)

The `openai` Python package is only the HTTP client: it talks to https://api.x.ai/v1 (same Responses API, other base_url).
No OpenAI service is called anywhere in this repo.

grok-4.5 / low was picked on 2026-11-05 from a 3-call benchmark with an image + a forced tool call (parallel_tool_calls=false):
grok-4.3 effort none ~2 s, grok-4.20-0309-non-reasoning ~2 s, grok-4.5 low ~3 s, grok-4.7 low ~5 s, grok-4.6 low ~6 s,
grok-4.3 low ~10 s. All returned a valid tool call.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

XAI_BASE_URL = "https://api.x.ai/v1"
GROK_DEFAULT_MODEL = "grok-4.5"
GROK_DEFAULT_EFFORT = "low"


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    label: str
    api_key: str
    key_var: str
    base_url: str
    model: str
    effort: str | None  # default reasoning effort from the environment (the UI setting overrides it)


def config() -> LLMConfig:
    """Read the environment each time: a key pasted into .env (and reloaded) is picked up without a restart."""
    return LLMConfig("grok", "Grok", os.environ.get("XAI_API_KEY") or "", "XAI_API_KEY", XAI_BASE_URL,
                     os.environ.get("GROK_MODEL") or GROK_DEFAULT_MODEL,
                     os.environ.get("GROK_REASONING_EFFORT") or GROK_DEFAULT_EFFORT)


def key_ok(cfg: LLMConfig) -> bool:
    k = cfg.api_key.strip()
    return bool(k) and "REPLACE_ME" not in k


def missing_key_message(cfg: LLMConfig) -> str:
    return f"Manca la chiave {cfg.label}: metti {cfg.key_var} nel file .env della repo e rimanda il messaggio."


def make_client(cfg: LLMConfig):
    from openai import OpenAI  # the OpenAI SDK also talks to xAI (same Responses API, other base_url)
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
