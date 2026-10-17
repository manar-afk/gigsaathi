"""Storage interface for earnings records."""
from __future__ import annotations

from datetime import date
from typing import Protocol


class EarningsStore(Protocol):
    def add_entries(self, user_id: str, records: list[dict]) -> None: ...

    def list_entries(self, user_id: str, since: date | None) -> list[dict]: ...
