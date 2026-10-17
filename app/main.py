"""FastAPI entrypoint: serves the API and the static frontend."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.staticfiles import StaticFiles

from app.config import Settings, load_settings
from app.llm.base import LLMClient, LLMError
from app.llm.vertex import VertexGeminiClient
from app.retrieval.cities import CityDirectory
from app.retrieval.kb import KnowledgeBase
from app.schemas import ChatRequest, ChatResponse
from app.security import RateLimiter, clean_message, valid_user_id
from app.services.assistant import Assistant
from app.storage.base import EarningsStore
from app.storage.firestore_store import FirestoreStore

log = logging.getLogger("gigsaathi")
_STATIC = Path(__file__).parent / "static"
_CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")


def create_app(
    settings: Settings | None = None,
    llm: LLMClient | None = None,
    kb: KnowledgeBase | None = None,
    store: EarningsStore | None = None,
    cities: CityDirectory | None = None,
) -> FastAPI:
    settings = settings or load_settings()
    llm = llm or VertexGeminiClient(settings.project_id, settings.vertex_location, settings.model_name)
    kb = kb or KnowledgeBase.from_file(settings.kb_path)
    store = store or FirestoreStore(settings.project_id)
    cities = cities or CityDirectory.from_file(settings.cities_path)
    assistant = Assistant(llm, kb, store, cities)
    user_limiter = RateLimiter(settings.rate_limit_per_minute)
    ip_limiter = RateLimiter(settings.rate_limit_per_minute * 3)

    app = FastAPI(title="GigSaathi", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = _CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "microphone=(self)"
        return response

    def identify(request: Request, header_value: str | None) -> str:
        try:
            uid = valid_user_id(header_value)
        except ValueError:
            raise HTTPException(400, "invalid_input")
        forwarded = request.headers.get("x-forwarded-for", "")
        ip = forwarded.split(",")[0].strip() or (request.client.host if request.client else "?")
        if not (user_limiter.allow(uid) and ip_limiter.allow(ip)):
            raise HTTPException(429, "rate_limited")
        return uid

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(body: ChatRequest, request: Request, x_user_id: str | None = Header(default=None)):
        uid = identify(request, x_user_id)
        try:
            message = clean_message(body.message, settings.max_message_chars)
        except ValueError:
            raise HTTPException(400, "invalid_input")
        started = time.monotonic()
        try:
            result = assistant.handle(uid, message, body.city)
        except LLMError:
            log.warning("llm_unavailable")
            raise HTTPException(503, "llm_unavailable")
        log.info("chat intent=%s lang=%s ms=%d", result.intent, result.language,
                 (time.monotonic() - started) * 1000)  # no message text or ids logged
        return ChatResponse(**result.__dict__)

    @app.get("/api/cities")
    def list_cities() -> list[dict]:
        return cities.listing()

    @app.get("/api/earnings/summary")
    def earnings_summary(request: Request, period: Literal["today", "week", "month", "all"] = "today",
                         x_user_id: str | None = Header(default=None)) -> dict:
        uid = identify(request, x_user_id)
        return assistant.summary(uid, period).summary or {}

    app.mount("/", StaticFiles(directory=_STATIC, html=True), name="static")
    return app


app = create_app()
