"""City and state lookup so state-specific rules can be applied."""
from __future__ import annotations

import json
from pathlib import Path


class CityDirectory:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._to_state: dict[str, str] = {}
        for row in rows:
            state = row["state"]
            self._to_state[state.lower()] = state
            for name in [row["city"], *row.get("aliases", [])]:
                self._to_state[name.lower()] = state

    @classmethod
    def from_file(cls, path: Path) -> "CityDirectory":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def resolve_state(self, name: str | None) -> str | None:
        """State for a city, alias or state name; None if unknown."""
        return self._to_state.get((name or "").strip().lower())

    def listing(self) -> list[dict]:
        return sorted(({"city": r["city"], "state": r["state"]} for r in self._rows), key=lambda r: r["city"])
