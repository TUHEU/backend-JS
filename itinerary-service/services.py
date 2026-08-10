from __future__ import annotations
from datetime import datetime, timezone

from base import ServiceError
from models import Itinerary
from repository import ItineraryRepository


class ItineraryService:
    def __init__(self, repository: ItineraryRepository):
        self._repo = repository

    def create(self, user_id: str, title: str, notes: str, start_date, end_date, stops) -> dict:
        title = (title or "").strip()
        if not title:
            raise ServiceError("title is required", 400)
        if not isinstance(stops, list):
            raise ServiceError("stops must be a list", 400)
        itinerary = Itinerary(
            user_id=user_id, title=title, notes=notes or "",
            start_date=start_date, end_date=end_date, stops=stops,
        )
        self._repo.save_new(itinerary)
        return itinerary.to_dict()

    def list_for_user(self, user_id: str, email: str) -> dict:
        mine = [i.to_dict() for i in self._repo.find_owned_by(user_id)]
        shared = [i.to_dict() for i in self._repo.find_shared_with(email)]
        return {"itineraries": mine, "shared_with_me": shared}

    def get(self, itinerary_id: str, user_id: str, email: str) -> dict:
        itinerary = self._require(itinerary_id)
        self._require_access(itinerary, user_id, email)
        return itinerary.to_dict()

    def update(self, itinerary_id: str, user_id: str, changes: dict) -> dict:
        itinerary = self._require(itinerary_id)
        self._require_owner(itinerary, user_id)
        allowed = {k: v for k, v in changes.items() if k in
                   {"title", "notes", "start_date", "end_date", "stops"}}
        allowed["updated_at"] = datetime.now(timezone.utc).isoformat()
        updated = self._repo.update_fields(itinerary_id, allowed)
        return updated.to_dict()

    def delete(self, itinerary_id: str, user_id: str) -> None:
        itinerary = self._require(itinerary_id)
        self._require_owner(itinerary, user_id)
        self._repo.delete(itinerary_id)

    def share(self, itinerary_id: str, user_id: str, share_email: str) -> dict:
        itinerary = self._require(itinerary_id)
        self._require_owner(itinerary, user_id)
        if not share_email:
            raise ServiceError("email is required", 400)
        shared_with = set(itinerary.shared_with)
        shared_with.add(share_email)
        updated = self._repo.update_fields(itinerary_id, {
            "shared_with": sorted(shared_with),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return updated.to_dict()

    def list_stops_for_user(self, user_id: str) -> list:
        """Internal helper used by Recommendation Service: flattened list
        of destination ids this user has already put in an itinerary."""
        stops = []
        for itinerary in self._repo.find_owned_by(user_id):
            stops.extend(itinerary.stops)
        return stops

    # -- guards --------------------------------------------------------
    def _require(self, itinerary_id: str) -> Itinerary:
        itinerary = self._repo.find_by_id(itinerary_id)
        if not itinerary:
            raise ServiceError("Itinerary not found", 404)
        return itinerary

    def _require_owner(self, itinerary: Itinerary, user_id: str):
        if itinerary.user_id != user_id:
            raise ServiceError("Only the owner can modify this itinerary", 403)

    def _require_access(self, itinerary: Itinerary, user_id: str, email: str):
        if itinerary.user_id != user_id and email not in itinerary.shared_with:
            raise ServiceError("You do not have access to this itinerary", 403)
