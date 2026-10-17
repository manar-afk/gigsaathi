import pytest

from app.llm.base import LLMError
from app.services.assistant import Assistant
from tests.conftest import FakeLLM, MemoryStore

UID = "123e4567-e89b-12d3-a456-426614174000"


def make(llm, kb, today, cities=None):
    from app.config import load_settings
    from app.retrieval.cities import CityDirectory
    cities = cities or CityDirectory.from_file(load_settings().cities_path)
    store = MemoryStore()
    return Assistant(llm, kb, store, cities, today=lambda: today), store


def test_earnings_log_uses_code_for_totals(kb, today):
    llm = FakeLLM({"intent": "earnings_log", "language": "en", "entries": [
        {"type": "income", "amount": 850, "trips": 3}, {"type": "expense", "amount": 200, "category": "fuel"}]})
    a, store = make(llm, kb, today)
    r = a.handle(UID, "earned 850 in 3 trips, 200 petrol")
    assert "₹650" in r.reply and len(store.rows[UID]) == 2 and llm.calls == 1


def test_invalid_entries_are_dropped(kb, today):
    llm = FakeLLM({"intent": "earnings_log", "language": "en", "entries": [{"type": "income", "amount": -5}]})
    a, store = make(llm, kb, today)
    assert UID not in store.rows and "amount" in a.handle(UID, "x").reply


def test_out_of_scope_makes_no_answer_call(kb, today):
    llm = FakeLLM({"intent": "other", "language": "hinglish"})
    a, _ = make(llm, kb, today)
    assert "madad" in a.handle(UID, "bitcoin tips").reply and llm.calls == 1


def test_grounded_answer_shows_source(kb, today):
    llm = FakeLLM(
        {"intent": "document_help", "language": "en", "english_query": "e-shram registration"},
        {"reply": "Register free on the portal.", "cited_ids": ["eshram-registration"]})
    a, _ = make(llm, kb, today)
    r = a.handle(UID, "how do I register on e-Shram")
    assert r.sources and r.sources[0].id == "eshram-registration"


def test_uncited_or_invented_source_is_refused(kb, today):
    llm = FakeLLM(
        {"intent": "document_help", "language": "en", "english_query": "e-shram registration"},
        {"reply": "Made-up scheme!", "cited_ids": ["invented-id"]})
    a, _ = make(llm, kb, today)
    r = a.handle(UID, "how do I register on e-Shram")
    assert "verified" in r.reply and not r.sources


def test_no_kb_match_skips_llm_answer(kb, today):
    llm = FakeLLM({"intent": "rights_schemes", "language": "en", "english_query": "lottery jackpot"})
    a, _ = make(llm, kb, today)
    assert "verified" in a.handle(UID, "lottery jackpot").reply and llm.calls == 1


def test_bad_json_raises_llm_error(kb, today):
    class Bad:
        def generate_json(self, s, u): return "not json"
    a, _ = make(Bad(), kb, today)
    with pytest.raises(LLMError):
        a.handle(UID, "hello")


def test_state_rules_used_when_city_selected(kb, today):
    llm = FakeLLM(
        {"intent": "rights_schemes", "language": "en", "english_query": "gig worker law welfare board"},
        {"reply": "Telangana has passed a law.", "cited_ids": ["telangana-gig-act"]})
    a, _ = make(llm, kb, today)
    r = a.handle(UID, "what are my rights as a gig worker", city="Hyderabad")
    assert r.sources[0].id == "telangana-gig-act" and r.sources[0].source_type == "secondary"
