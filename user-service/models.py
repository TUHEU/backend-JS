"""Domain model for the User Service."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List
import uuid


@dataclass
class User:
    """Plain data object (DTO). Keeps the shape of a user in one place
    instead of scattering dict keys through the codebase."""

    name: str
    email: str
    password_hash: str
    preferences: List[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    def to_public_dict(self) -> dict:
        """Never leak the password hash outside the service."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "preferences": self.preferences,
        }

    @staticmethod
    def from_dict(data: dict) -> "User":
        return User(
            name=data.get("name", ""),
            email=data.get("email", ""),
            password_hash=data.get("password_hash", ""),
            preferences=data.get("preferences", []),
            id=data.get("id", str(uuid.uuid4())),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )
