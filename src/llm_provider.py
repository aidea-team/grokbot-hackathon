"""Which LLM backs the chat agents (dog + G1): OpenAI or Grok (xAI). Both speak the Responses API, so only the client changes.

Switchable at runtime from the web UIs (POST /api/provider); the startup default is LLM_PROVIDER from .env (default: grok).

    openai: OPENAI_API_KEY, OPENAI_MODEL (default gpt-4o-mini), OPENAI_REASONING_EFFORT, OPENAI_BASE_URL (optional)
    grok:   XAI_API_KEY,    GROK_MODEL (default grok-4.5),      GROK_REASONING_EFFORT (default low)

grok-4.5 / low was picked on 2026-11-05 from a 3-call benchmark with an image + a forced tool call (parallel_tool_calls=false):
grok-4.3 effort none ~2 s, grok-4.20-0309-non-reasoning ~2 s, grok-4.5 low ~3 s, grok-4.7 low ~5 s, grok-4.6 low ~6 s,
grok-4.3 low ~10 s. All returned a valid tool call. grok-4.5 low is the closest to a "reasoning, low effort" OpenAI model.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

PROVIDERS = ("openai", "grok")
XAI_BASE_URL = "https://api.x.ai/v1"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
GROK_DEFAULT_MODEL = "grok-4.5"
GROK_DEFAULT_EFFORT = "low"


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    label: str
    api_key: str
    key_var: str
    base_url: str | None
    model: str
    effort: str | None  # default reasoning effort from the environment (the UI setting overrides it)


def default_provider() -> str:
    p = (os.environ.get("LLM_PROVIDER") or "grok").strip().lower()
    return p if p in PROVIDERS else "grok"


def config(provider: str) -> LLMConfig:
    """Read the environment each time: a key pasted into .env (and reloaded) is picked up without a restart."""
    if provider == "grok":
        return LLMConfig("grok", "Grok", os.environ.get("XAI_API_KEY") or "", "XAI_API_KEY", XAI_BASE_URL,
                         os.environ.get("GROK_MODEL") or GROK_DEFAULT_MODEL,
                         os.environ.get("GROK_REASONING_EFFORT") or GROK_DEFAULT_EFFORT)
    if provider == "openai":
        return LLMConfig("openai", "OpenAI", os.environ.get("OPENAI_API_KEY") or "", "OPENAI_API_KEY",
                         os.environ.get("OPENAI_BASE_URL") or None,
                         os.environ.get("OPENAI_MODEL") or OPENAI_DEFAULT_MODEL,
                         os.environ.get("OPENAI_REASONING_EFFORT") or None)
    raise ValueError(f"provider sconosciuto: {provider!r} (scegli tra {', '.join(PROVIDERS)})")


def key_ok(cfg: LLMConfig) -> bool:
    k = cfg.api_key.strip()
    return bool(k) and "REPLACE_ME" not in k


def missing_key_message(cfg: LLMConfig) -> str:
    return f"Manca la chiave {cfg.label}: metti {cfg.key_var} nel file .env della repo e rimanda il messaggio."


def make_client(cfg: LLMConfig):
    from openai import OpenAI  # the OpenAI SDK also talks to xAI (same Responses API, other base_url)
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url)
