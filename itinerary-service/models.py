"""Domain model for the Itinerary Service."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional
import uuid


@dataclass
class Itinerary:
    user_id: str
    title: str
    notes: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    stops: List[dict] = field(default_factory=list)  # [{destination_id, day, note}]
    shared_with: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Itinerary":
        return Itinerary(
            user_id=data.get("user_id", ""),
            title=data.get("title", ""),
            notes=data.get("notes", ""),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            stops=data.get("stops", []),
            shared_with=data.get("shared_with", []),
            id=data.get("id", str(uuid.uuid4())),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
        )
