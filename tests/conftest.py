import json
from datetime import date

import pytest

from app.retrieval.kb import KnowledgeBase
from app.config import load_settings
from app.retrieval.cities import CityDirectory


class FakeLLM:
    """Scripted LLM used only in tests; returns queued JSON strings."""

    def __init__(self, *responses: dict) -> None:
        self.queue = [json.dumps(r, ensure_ascii=False) for r in responses]
        self.calls = 0

    def generate_json(self, system: str, user: str) -> str:
        self.calls += 1
        return self.queue.pop(0)


class MemoryStore:
    """In-memory EarningsStore for tests only."""

    def __init__(self) -> None:
        self.rows: dict[str, list[dict]] = {}

    def add_entries(self, user_id, records):
        self.rows.setdefault(user_id, []).extend(records)

    def list_entries(self, user_id, since):
        return [r for r in self.rows.get(user_id, []) if since is None or r["date"] >= since.isoformat()]


@pytest.fixture
def kb():
    return KnowledgeBase.from_file(load_settings().kb_path)


@pytest.fixture
def today():
    return date(2026, 10, 17)


@pytest.fixture
def cities():
    return CityDirectory.from_file(load_settings().cities_path)
