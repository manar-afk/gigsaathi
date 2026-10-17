from fastapi.testclient import TestClient

from app.config import load_settings
from app.main import create_app
from tests.conftest import FakeLLM, MemoryStore

UID = "123e4567-e89b-12d3-a456-426614174000"


def client(*responses):
    return TestClient(create_app(load_settings(), FakeLLM(*responses), store=MemoryStore()))


def test_health_and_security_headers():
    r = client().get("/health")
    assert r.status_code == 200 and "Content-Security-Policy" in r.headers


def test_bad_user_id_rejected():
    r = client().post("/api/chat", json={"message": "hi"}, headers={"X-User-Id": "nope"})
    assert r.status_code == 400


def test_oversized_message_rejected():
    r = client().post("/api/chat", json={"message": "x" * 5000}, headers={"X-User-Id": UID})
    assert r.status_code == 400


def test_chat_roundtrip_and_summary():
    c = client({"intent": "earnings_log", "language": "en",
                "entries": [{"type": "income", "amount": 500}]})
    r = c.post("/api/chat", json={"message": "earned 500"}, headers={"X-User-Id": UID})
    assert r.status_code == 200 and r.json()["summary"]["income"] == 500
    s = c.get("/api/earnings/summary?period=all", headers={"X-User-Id": UID})
    assert s.json()["net"] == 500
