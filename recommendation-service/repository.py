from __future__ import annotations
from base import JsonRepository
from models import Destination


class DestinationRepository:
    def __init__(self, file_path):
        self._store = JsonRepository(file_path, id_field="id")

    def all(self) -> list[Destination]:
        return [Destination(r) for r in self._store.all()]

    def find_by_id(self, destination_id: str) -> Destination | None:
        raw = self._store.find_by_id(destination_id)
        return Destination(raw) if raw else None

    def search(self, query: str = "", category: str = "") -> list[Destination]:
        destinations = self.all()
        if query:
            q = query.lower()
            destinations = [
                d for d in destinations
                if q in d.raw().get("name", "").lower()
                or q in d.raw().get("neighborhood", "").lower()
                or q in d.raw().get("description", "").lower()
            ]
        if category:
            destinations = [d for d in destinations if d.raw().get("category", "").lower() == category.lower()]
        return destinations

    def save_review(self, destination: Destination) -> None:
        def mutate(record):
            record["reviews"] = destination.raw().get("reviews", [])

        self._store.update(destination.id, mutate)
