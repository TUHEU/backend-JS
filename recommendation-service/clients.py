"""Proxy pattern: each class stands in for a remote microservice so the
rest of the codebase calls a normal Python method instead of knowing
about HTTP, base URLs, or timeouts. This is exactly the "Recommendation
Service calling User Service" synchronous REST pattern from the course
slide -- it just lives behind a clean interface here.
"""
from __future__ import annotations
import requests


class UserServiceClient:
    def __init__(self, base_url: str, timeout: float = 3.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def get_preferences(self, user_id: str) -> set:
        profile = self._get_profile(user_id)
        return {p.lower() for p in profile.get("preferences", [])} if profile else set()

    def get_name(self, user_id: str, fallback: str = "Traveler") -> str:
        profile = self._get_profile(user_id)
        return profile.get("name", fallback) if profile else fallback

    def _get_profile(self, user_id: str) -> dict | None:
        try:
            resp = requests.get(f"{self._base_url}/users/{user_id}", timeout=self._timeout)
            if resp.status_code != 200:
                return None
            return resp.json()
        except requests.RequestException:
            # Recommendation Service degrades gracefully: no profile
            # data just means personalization falls back to popularity.
            return None


class ItineraryServiceClient:
    def __init__(self, base_url: str, timeout: float = 3.0):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def get_visited_destination_ids(self, user_id: str) -> set:
        try:
            resp = requests.get(
                f"{self._base_url}/itineraries/internal/user/{user_id}/stops", timeout=self._timeout
            )
            if resp.status_code != 200:
                return set()
            stops = resp.json().get("stops", [])
            return {s.get("destination_id") for s in stops if s.get("destination_id")}
        except requests.RequestException:
            return set()
