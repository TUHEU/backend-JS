"""Domain model for the Recommendation Service."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional
import uuid


@dataclass
class Review:
    user_id: str
    user_name: str
    rating: float
    comment: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


class Destination:
    """Wraps a destination JSON record and adds behaviour (average
    rating, review handling) instead of leaving that logic loose in
    route functions -- a thin domain object, not just a dict bag."""

    def __init__(self, data: dict):
        self._data = data

    @property
    def id(self) -> str:
        return self._data["id"]

    @property
    def tags(self) -> set:
        return {t.lower() for t in self._data.get("tags", [])}

    @property
    def popularity_score(self) -> float:
        return self._data.get("popularity_score", 0) or 0

    @property
    def reviews(self) -> list:
        return self._data.get("reviews", [])

    def average_rating(self) -> Optional[float]:
        reviews = self.reviews
        if not reviews:
            return None
        return round(sum(r["rating"] for r in reviews) / len(reviews), 1)

    def add_review(self, review: Review) -> None:
        self._data.setdefault("reviews", []).append(review.to_dict())

    def raw(self) -> dict:
        return self._data

    def to_detail_dict(self) -> dict:
        out = dict(self._data)
        out["avg_rating"] = self.average_rating()
        return out

    def to_summary_dict(self, match_score: float = None) -> dict:
        summary = {
            "id": self._data["id"],
            "name": self._data.get("name"),
            "neighborhood": self._data.get("neighborhood"),
            "category": self._data.get("category"),
            "description": self._data.get("description"),
            "tags": self._data.get("tags", []),
            "avg_rating": self.average_rating(),
            "image": self._data.get("image"),
            "location": self._data.get("location"),
        }
        if match_score is not None:
            summary["match_score"] = round(match_score, 2)
        return summary
