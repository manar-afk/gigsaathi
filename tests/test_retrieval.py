import pytest

from app.retrieval.kb import KnowledgeBase


def test_finds_eshram(kb):
    hits = kb.search("how to register on e-Shram card", {"scheme", "document"})
    assert hits and hits[0].id == "eshram-registration"


def test_unknown_topic_returns_nothing(kb):
    assert kb.search("quantum computing stock tips", {"scheme", "rights"}) == []


def test_topic_filter(kb):
    assert all("safety" in e.topics for e in kb.search("heat helmet night", {"safety"}))


def test_every_entry_has_https_source(kb):
    assert all(e.source_url.startswith("https://") for e in kb._entries)


def test_rejects_non_https_source(tmp_path):
    p = tmp_path / "kb.json"
    p.write_text('[{"id":"x","topics":["safety"],"title":"t","text":"t","keywords":[],"source_url":"http://x"}]')
    with pytest.raises(ValueError):
        KnowledgeBase.from_file(p)


def test_state_entries_need_matching_state(kb):
    q = "gig worker law welfare board rights"
    assert "telangana-gig-act" not in [e.id for e in kb.search(q, {"rights"}, state=None, k=10)]
    assert "telangana-gig-act" not in [e.id for e in kb.search(q, {"rights"}, state="Bihar", k=10)]
    assert kb.search(q, {"rights"}, state="Telangana")[0].id == "telangana-gig-act"


def test_city_directory(cities):
    assert cities.resolve_state("Bangalore") == "Karnataka"
    assert cities.resolve_state("hyderabad") == "Telangana"
    assert cities.resolve_state("Atlantis") is None
    assert all(r["state"] for r in cities.listing())
