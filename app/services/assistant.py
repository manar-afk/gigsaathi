"""Orchestrates intent detection, earnings logic and grounded answers (R1-R5)."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Callable
from zoneinfo import ZoneInfo

from app.cache import TTLCache
from app.llm.base import LLMClient, LLMError
from app.retrieval.cities import CityDirectory
from app.retrieval.kb import KBEntry, KnowledgeBase
from app.schemas import Intent, Language, Source, Understanding
from app.security import wrap_user_text
from app.services import earnings
from app.services.messages import format_summary, msg
from app.services.prompts import (
    ANSWER_SYSTEM, GRIEVANCE_TASK, LANGUAGE_NAMES, UNDERSTAND_SYSTEM,
)
from app.storage.base import EarningsStore

_TOPICS: dict[str, set[str]] = {
    "safety": {"safety"},
    "rights_schemes": {"scheme", "rights"},
    "document_help": {"document"},
    "grievance": {"grievance"},
}


@dataclass(frozen=True)
class ChatResult:
    reply: str
    intent: Intent
    language: Language
    sources: list[Source] = field(default_factory=list)
    summary: dict | None = None


def _today_ist() -> date:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def _parse_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise LLMError("model returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise LLMError("model returned unexpected JSON")
    return data


def _normalise(text: str) -> str:
    return " ".join(text.lower().split())


class Assistant:
    def __init__(
        self,
        llm: LLMClient,
        kb: KnowledgeBase,
        store: EarningsStore,
        cities: CityDirectory,
        cache: TTLCache | None = None,
        today: Callable[[], date] = _today_ist,
    ) -> None:
        self._llm, self._kb, self._store, self._cities = llm, kb, store, cities
        self._cache = cache or TTLCache()
        self._today = today

    # ---- public API -------------------------------------------------
    def handle(self, user_id: str, message: str, city: str | None = None) -> ChatResult:
        today = self._today()
        u = self._understand(message, today)
        if u.intent == "other":
            return ChatResult(msg(u.language, "out_of_scope"), u.intent, u.language)
        if u.intent == "earnings_log":
            return self._log(user_id, u, today)
        if u.intent == "earnings_summary":
            return self.summary(user_id, u.period or "today", u.language, u.intent)
        state = self._cities.resolve_state(city) or self._cities.resolve_state(u.city)
        return self._answer(u, message, state)

    def summary(self, user_id: str, period, lang: Language = "en",
                intent: Intent = "earnings_summary") -> ChatResult:
        today = self._today()
        records = self._store.list_entries(user_id, earnings.period_start(period, today))
        s = earnings.summarise(records)
        if s.entries == 0:
            text = msg(lang, "no_data", period=msg(lang, period))
        else:
            text = format_summary(lang, period, s)
        return ChatResult(text, intent, lang, summary={"period": period, **s.as_dict()})

    # ---- internals --------------------------------------------------
    def _understand(self, message: str, today: date) -> Understanding:
        key = f"u:{today}:{_normalise(message)}"
        cached = self._cache.get(key)
        if cached:
            return cached
        system = UNDERSTAND_SYSTEM.replace("{today}", today.isoformat())
        raw = _parse_json(self._llm.generate_json(system, wrap_user_text(message)))
        understood = Understanding.from_llm(raw)
        self._cache.set(key, understood)
        return understood

    def _log(self, user_id: str, u: Understanding, today: date) -> ChatResult:
        if not u.entries:
            return ChatResult(msg(u.language, "need_entries"), u.intent, u.language)
        records = [earnings.to_record(e, today) for e in u.entries]
        self._store.add_entries(user_id, records)
        todays = self._store.list_entries(user_id, today)
        s = earnings.summarise(todays)
        text = f"{msg(u.language, 'saved', n=len(records))}\n{format_summary(u.language, 'today', s)}"
        return ChatResult(text, u.intent, u.language, summary={"period": "today", **s.as_dict()})

    def _answer(self, u: Understanding, message: str, state: str | None) -> ChatResult:
        lang, intent = u.language, u.intent
        grievance = intent == "grievance"
        hits = self._kb.search(f"{u.english_query} {message}", _TOPICS[intent], state)
        if not hits and not grievance:
            return ChatResult(msg(lang, "no_grounded"), intent, lang)

        cache_key = f"a:{intent}:{lang}:{state}:{_normalise(message)}"
        if not grievance and (cached := self._cache.get(cache_key)):
            return cached

        system = ANSWER_SYSTEM.replace("{language_name}", LANGUAGE_NAMES[lang])
        if grievance:
            system += GRIEVANCE_TASK
        user = (f"<knowledge_base>\n{self._format_kb(hits)}\n</knowledge_base>\n"
                f"<user_state>{state or 'unknown'}</user_state>\n{wrap_user_text(message)}")
        data = _parse_json(self._llm.generate_json(system, user))

        reply = str(data.get("reply", "")).strip()[:3000]
        allowed = {e.id: e for e in hits}
        cited = [allowed[i] for i in data.get("cited_ids", []) if isinstance(i, str) and i in allowed]
        if not reply:
            raise LLMError("empty reply")
        if not grievance and not cited:
            return ChatResult(msg(lang, "no_grounded"), intent, lang)
        if grievance:
            reply = f"{reply}\n\n{msg(lang, 'grievance_note')}"

        result = ChatResult(reply, intent, lang, sources=[
            Source(id=e.id, title=e.title, url=e.source_url, last_verified=e.last_verified,
                   source_type=e.source_type)
            for e in cited
        ])
        if not grievance:
            self._cache.set(cache_key, result)
        return result

    @staticmethod
    def _format_kb(entries: list[KBEntry]) -> str:
        if not entries:
            return "(no entries)"
        return "\n".join(f"[{e.id}] {e.title}: {e.text} (source: {e.source_url})" for e in entries)
