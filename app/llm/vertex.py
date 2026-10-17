"""Gemini on Vertex AI using Application Default Credentials (no API key)."""
from __future__ import annotations

from .base import LLMError


class VertexGeminiClient:
    def __init__(self, project_id: str | None, location: str, model: str) -> None:
        self._project, self._location, self._model = project_id, location, model
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai

            project = self._project
            if not project:
                import google.auth

                _, project = google.auth.default()
            self._client = genai.Client(vertexai=True, project=project, location=self._location)
        return self._client

    def generate_json(self, system: str, user: str) -> str:
        from google.genai import types

        try:
            resp = self._get_client().models.generate_content(
                model=self._model,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=2048,
                ),
            )
        except Exception as exc:  # SDK raises many types; normalise
            raise LLMError("model call failed") from exc
        if not resp.text:
            raise LLMError("empty model response")
        return resp.text
