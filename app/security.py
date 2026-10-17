"""Input validation, prompt-injection hygiene and rate limiting."""
from __future__ import annotations

import re
import threading
import time
import uuid
from collections import defaultdict, deque

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_TAG = re.compile(r"</?\s*user_message\s*>", re.IGNORECASE)


def clean_message(text: str, max_chars: int) -> str:
    """Strip control characters; reject empty or oversized input."""
    text = _CONTROL.sub("", text or "").strip()
    if not text:
        raise ValueError("empty")
    if len(text) > max_chars:
        raise ValueError("too_long")
    return text


def valid_user_id(value: str | None) -> str:
    """Anonymous per-browser id must be a UUID (also keeps Firestore paths safe)."""
    try:
        return str(uuid.UUID(value or ""))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("bad_user_id") from exc


def wrap_user_text(text: str) -> str:
    """Delimit user text as data; remove any attempt to close the delimiter."""
    return f"<user_message>\n{_TAG.sub('', text)}\n</user_message>"


class RateLimiter:
    """Sliding-window limiter, per process. Good enough for a single Cloud Run instance."""

    def __init__(self, limit: int, window_s: int = 60) -> None:
        self._limit, self._window = limit, window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > 10_000:  # bound memory
                self._hits.clear()
            q = self._hits[key]
            while q and now - q[0] > self._window:
                q.popleft()
            if len(q) >= self._limit:
                return False
            q.append(now)
            return True
