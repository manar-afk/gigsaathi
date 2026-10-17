"""Request/response and LLM-output models. All LLM output is validated here."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, ValidationError

Intent = Literal[
    "earnings_log", "earnings_summary", "safety",
    "rights_schemes", "document_help", "grievance", "other",
]
Language = Literal["en", "hi", "hinglish"]
Period = Literal["today", "week", "month", "all"]


class EntryIn(BaseModel):
    type: Literal["income", "expense"]
    amount: float = Field(gt=0, le=10_000_000)
    category: str = Field(default="other", max_length=30)
    trips: int | None = Field(default=None, ge=0, le=500)
    hours: float | None = Field(default=None, ge=0, le=24)
    date: str | None = None


class Understanding(BaseModel):
    intent: Intent = "other"
    language: Language = "en"
    english_query: str = Field(default="", max_length=200)
    city: str | None = Field(default=None, max_length=60)
    period: Period | None = None
    entries: list[EntryIn] = Field(default_factory=list)

    @classmethod
    def from_llm(cls, raw: dict) -> "Understanding":
        """Validate LLM output; drop invalid entries instead of trusting them."""
        entries: list[EntryIn] = []
        for item in (raw.get("entries") or [])[:10]:
            try:
                entries.append(EntryIn.model_validate(item))
            except ValidationError:
                continue
        base = {k: v for k, v in raw.items() if k != "entries"}
        try:
            return cls(**base, entries=entries)
        except (ValidationError, TypeError):
            return cls(entries=entries)


class ChatRequest(BaseModel):
    message: str
    city: str | None = Field(default=None, max_length=60)


class Source(BaseModel):
    id: str
    title: str
    url: str
    last_verified: str | None = None
    source_type: Literal["official", "secondary"] = "official"


class ChatResponse(BaseModel):
    reply: str
    intent: Intent
    language: Language
    sources: list[Source] = Field(default_factory=list)
    summary: dict | None = None
