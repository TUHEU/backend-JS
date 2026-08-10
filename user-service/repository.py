"""Repository pattern: the only class allowed to know that users live
in a JSON file. Everything above this layer speaks in User objects."""
from __future__ import annotations
from base import JsonRepository
from models import User


class UserRepository:
    def __init__(self, file_path):
        self._store = JsonRepository(file_path, id_field="id")

    def find_by_email(self, email: str) -> User | None:
        raw = self._store.find(lambda r: r.get("email") == email)
        return User.from_dict(raw) if raw else None

    def find_by_id(self, user_id: str) -> User | None:
        raw = self._store.find_by_id(user_id)
        return User.from_dict(raw) if raw else None

    def save_new(self, user: User) -> User:
        self._store.add(user.to_dict())
        return user

    def update_preferences(self, user_id: str, preferences: list) -> User | None:
        def mutate(record):
            record["preferences"] = preferences

        raw = self._store.update(user_id, mutate)
        return User.from_dict(raw) if raw else None
