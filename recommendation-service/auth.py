"""Authentication concerns, isolated from business logic.

TokenService is a small Strategy: today it's HS256 JWTs, but any
class with the same encode()/decode() interface could replace it
without touching a single route.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from functools import wraps
import os
import jwt
from flask import request, jsonify


class TokenService:
    def __init__(self, secret: str, expiry_hours: int = 24):
        self._secret = secret
        self._expiry_hours = expiry_hours

    def issue(self, user_id: str, email: str) -> str:
        payload = {
            "sub": user_id,
            "email": email,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=self._expiry_hours),
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def decode(self, token: str) -> dict:
        return jwt.decode(token, self._secret, algorithms=["HS256"])


token_service = TokenService(os.environ.get("GLOBETROTTER_SECRET", "dev-secret-change-in-prod"))


def token_required(f):
    """Route decorator: verifies the JWT issued by this same service
    and injects the decoded payload (sub, email) as `current_payload`.
    Each service decodes the token itself (shared secret) rather than
    calling back into User Service on every request -- keeps auth
    stateless and avoids a network hop per call."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = token_service.decode(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(payload, *args, **kwargs)

    return decorated
