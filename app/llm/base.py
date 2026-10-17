"""LLM adapter interface. Services depend on this, never on a vendor SDK."""
from __future__ import annotations

from typing import Protocol


class LLMError(RuntimeError):
    """Raised when the model is unreachable or returns unusable output."""


class LLMClient(Protocol):
    def generate_json(self, system: str, user: str) -> str:
        """Return the model's JSON text for a system + user prompt."""
        ...
