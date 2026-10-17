"""Environment-driven configuration. No secrets live here."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    project_id: str | None
    vertex_location: str
    model_name: str
    max_message_chars: int
    rate_limit_per_minute: int
    kb_path: Path
    cities_path: Path


def load_settings() -> Settings:
    return Settings(
        project_id=os.getenv("PROJECT_ID"),
        vertex_location=os.getenv("VERTEX_LOCATION", "us-central1"),
        model_name=os.getenv("MODEL_NAME", "gemini-2.5-flash"),
        max_message_chars=int(os.getenv("MAX_MESSAGE_CHARS", "1000")),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "20")),
        kb_path=Path(os.getenv("KB_PATH", str(_ROOT / "data" / "knowledge_base.json"))),
        cities_path=Path(os.getenv("CITIES_PATH", str(_ROOT / "data" / "cities.json"))),
    )
