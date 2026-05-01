"""
LLM provider abstraction.

The deterministic engine in `core/` produces the *content* of every
recommendation. The LLM only paraphrases or expands those findings into
more conversational prose — its output is never allowed to change the
clinical conclusion. This abstraction keeps that boundary clean.

Three providers are supported:

* `mock`      — deterministic, runs offline, used in tests and as a default
* `anthropic` — Claude (set `ANTHROPIC_API_KEY` and `LLM_MODEL=claude-…`)
* `openai`    — GPT-4 family (set `OPENAI_API_KEY`)

Switching is done with `LLM_PROVIDER` in `.env`.
"""

from __future__ import annotations

import os
import textwrap
from typing import Protocol


class LLMProvider(Protocol):
    name: str
    def complete(self, system: str, user: str, *, max_tokens: int = 800,
                 temperature: float = 0.2) -> str: ...


class MockLLM:
    """Deterministic, offline 'paraphraser'.

    Produces output that is grammatical, on-topic, and predictable for tests.
    It composes the system + user prompt deterministically so tests can rely on it.
    """
    name = "mock"

    def complete(self, system: str, user: str, *, max_tokens: int = 800,
                 temperature: float = 0.2) -> str:
        # Strategy: extract bullet-style sentences from the user prompt and
        # echo them back as a polished paragraph. Good enough for offline demo.
        condensed = " ".join(line.strip() for line in user.splitlines() if line.strip())
        # Cap at ~2000 chars so callers never blow up token budgets in tests
        return textwrap.shorten(
            f"[Syntrx narrator] {condensed}",
            width=min(max_tokens * 4, 2000),
            placeholder="…",
        )


class AnthropicLLM:
    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        from anthropic import Anthropic  # imported lazily so tests don't need it
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str, *, max_tokens: int = 800,
                 temperature: float = 0.2) -> str:
        msg = self._client.messages.create(
            model=self._model, max_tokens=max_tokens, temperature=temperature,
            system=system, messages=[{"role": "user", "content": user}],
        )
        # The SDK returns a list of content blocks; concatenate the text ones
        return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")


class OpenAILLM:
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import OpenAI
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(self, system: str, user: str, *, max_tokens: int = 800,
                 temperature: float = 0.2) -> str:
        resp = self._client.chat.completions.create(
            model=self._model, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""


def get_llm() -> LLMProvider:
    """Read env vars and return the configured provider."""
    provider = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider == "anthropic":
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            return MockLLM()
        return AnthropicLLM(key, os.getenv("LLM_MODEL", "claude-sonnet-4-6"))
    if provider == "openai":
        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            return MockLLM()
        return OpenAILLM(key, os.getenv("LLM_MODEL", "gpt-4o-mini"))
    return MockLLM()
