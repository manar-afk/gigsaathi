"""Firestore-backed earnings store (keyless auth via ADC)."""
from __future__ import annotations

from datetime import date


class FirestoreStore:
    def __init__(self, project_id: str | None = None) -> None:
        self._project = project_id
        self._db = None

    def _client(self):
        if self._db is None:
            from google.cloud import firestore

            self._db = firestore.Client(project=self._project)
        return self._db

    def _entries(self, user_id: str):
        return self._client().collection("users").document(user_id).collection("entries")

    def add_entries(self, user_id: str, records: list[dict]) -> None:
        col = self._entries(user_id)
        batch = self._client().batch()
        for record in records:
            batch.set(col.document(), record)
        batch.commit()

    def list_entries(self, user_id: str, since: date | None) -> list[dict]:
        from google.cloud.firestore_v1.base_query import FieldFilter

        query = self._entries(user_id)
        if since:
            query = query.where(filter=FieldFilter("date", ">=", since.isoformat()))
        return [doc.to_dict() for doc in query.limit(5000).stream()]
