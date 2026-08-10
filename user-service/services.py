"""Service layer: business rules live here, not in Flask routes.
Routes stay thin (parse request -> call service -> serialize response);
that's what lets this logic be unit-tested with zero HTTP involved."""
from __future__ import annotations
from werkzeug.security import generate_password_hash, check_password_hash

from base import ServiceError
from models import User
from repository import UserRepository
from auth import TokenService


class AuthService:
    def __init__(self, repository: UserRepository, token_service: TokenService):
        self._repo = repository
        self._tokens = token_service

    def register(self, name: str, email: str, password: str, preferences: list) -> dict:
        name = (name or "").strip()
        email = (email or "").strip().lower()
        if not name or not email or not password:
            raise ServiceError("name, email and password are required", 400)
        if len(password) < 6:
            raise ServiceError("password must be at least 6 characters", 400)
        if self._repo.find_by_email(email):
            raise ServiceError("An account with this email already exists", 409)

        user = User(
            name=name,
            email=email,
            password_hash=generate_password_hash(password),
            preferences=preferences or [],
        )
        self._repo.save_new(user)
        return self._issue_session(user)

    def login(self, email: str, password: str) -> dict:
        email = (email or "").strip().lower()
        user = self._repo.find_by_email(email)
        if not user or not check_password_hash(user.password_hash, password):
            raise ServiceError("Invalid email or password", 401)
        return self._issue_session(user)

    def get_profile(self, user_id: str) -> dict:
        user = self._repo.find_by_id(user_id)
        if not user:
            raise ServiceError("User not found", 404)
        return user.to_public_dict()

    def update_preferences(self, user_id: str, preferences: list) -> dict:
        user = self._repo.update_preferences(user_id, preferences)
        if not user:
            raise ServiceError("User not found", 404)
        return user.to_public_dict()

    def _issue_session(self, user: User) -> dict:
        token = self._tokens.issue(user.id, user.email)
        return {"token": token, "user": user.to_public_dict()}
