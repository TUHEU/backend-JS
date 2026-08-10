from __future__ import annotations
from base import JsonRepository
from models import Itinerary


class ItineraryRepository:
    def __init__(self, file_path):
        self._store = JsonRepository(file_path, id_field="id")

    def find_by_id(self, itinerary_id: str) -> Itinerary | None:
        raw = self._store.find_by_id(itinerary_id)
        return Itinerary.from_dict(raw) if raw else None

    def find_owned_by(self, user_id: str) -> list[Itinerary]:
        return [Itinerary.from_dict(r) for r in self._store.filter(lambda r: r.get("user_id") == user_id)]

    def find_shared_with(self, email: str) -> list[Itinerary]:
        return [
            Itinerary.from_dict(r)
            for r in self._store.filter(lambda r: email in r.get("shared_with", []))
        ]

    def save_new(self, itinerary: Itinerary) -> Itinerary:
        self._store.add(itinerary.to_dict())
        return itinerary

    def update_fields(self, itinerary_id: str, fields: dict) -> Itinerary | None:
        def mutate(record):
            record.update(fields)

        raw = self._store.update(itinerary_id, mutate)
        return Itinerary.from_dict(raw) if raw else None

    def delete(self, itinerary_id: str) -> bool:
        return self._store.delete(itinerary_id)
