"""Curated knowledge base with dependency-free keyword retrieval."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

_STOP = frozenset(
    "a an the is are am to of in on for and or my me i do can how what where which "
    "with from it this that be have has you your if so at by as".split()
)
_WORD = re.compile(r"\w+", re.UNICODE)


def _tokens(text: str) -> set[str]:
    return {t for t in _WORD.findall(text.lower()) if len(t) > 1 and t not in _STOP}


@dataclass(frozen=True)
class KBEntry:
    id: str
    topics: frozenset[str]
    title: str
    text: str
    keywords: frozenset[str]
    source_url: str
    last_verified: str | None
    states: frozenset[str] = frozenset()
    source_type: str = "official"


class KnowledgeBase:
    def __init__(self, entries: list[KBEntry]) -> None:
        self._entries = entries
        self._kw = {e.id: _tokens(" ".join(e.keywords)) | _tokens(e.title) for e in entries}
        self._body = {e.id: _tokens(e.text) for e in entries}

    @classmethod
    def from_file(cls, path: Path) -> "KnowledgeBase":
        entries = []
        for raw in json.loads(Path(path).read_text(encoding="utf-8")):
            if not str(raw["source_url"]).startswith("https://"):
                raise ValueError(f"KB entry {raw['id']} needs an https source_url")
            entries.append(KBEntry(
                id=raw["id"], topics=frozenset(raw["topics"]), title=raw["title"],
                text=raw["text"], keywords=frozenset(raw["keywords"]),
                source_url=raw["source_url"], last_verified=raw.get("last_verified"),
                states=frozenset(raw.get("states", [])), source_type=raw.get("source_type", "official"),
            ))
        return cls(entries)

    def search(self, query: str, topics: set[str], state: str | None = None,
               k: int = 3, min_score: int = 2) -> list[KBEntry]:
        """Top-k entries within the given topics. Keyword hits count 2, body hits 1.

        State-specific entries are only eligible when `state` matches; a matching state adds a bonus.
        """
        q = _tokens(query)
        scored = []
        for entry in self._entries:
            if not topics & entry.topics:
                continue
            if entry.states and state not in entry.states:
                continue
            score = 2 * len(q & self._kw[entry.id]) + len(q & self._body[entry.id])
            if entry.states and score >= 1:
                score += 3
            if score >= min_score:
                scored.append((score, entry))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [entry for _, entry in scored[:k]]
