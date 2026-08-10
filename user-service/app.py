"""
GlobeTrotter — User Service (Phase 2: Microservices)
Owns: users.json
Endpoints:
  POST /register
  POST /login
  GET  /profile              (auth)
  PUT  /profile/preferences  (auth)
  GET  /users/<id>           (internal — used by Recommendation Service)
  GET  /health
"""
import os
from flask import Flask, request, jsonify

from base import ServiceError
from repository import UserRepository
from auth import TokenService, token_required
from services import AuthService

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
SECRET_KEY = os.environ.get("GLOBETROTTER_SECRET", "dev-secret-change-in-prod")


def create_app() -> Flask:
    """Application factory pattern — lets tests spin up isolated app
    instances instead of relying on one global Flask object."""
    app = Flask(__name__)

    repository = UserRepository(USERS_FILE)
    token_service = TokenService(SECRET_KEY)
    auth_service = AuthService(repository, token_service)

    @app.after_request
    def add_cors_headers(response):
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        return response

    @app.route("/<path:_any>", methods=["OPTIONS"])
    def cors_preflight(_any):
        return ("", 204)

    @app.errorhandler(ServiceError)
    def handle_service_error(err):
        return jsonify({"error": err.message}), err.status_code

    @app.route("/register", methods=["POST"])
    def register():
        body = request.get_json(silent=True) or {}
        result = auth_service.register(
            body.get("name"), body.get("email"), body.get("password"), body.get("preferences", [])
        )
        return jsonify(result), 201

    @app.route("/login", methods=["POST"])
    def login():
        body = request.get_json(silent=True) or {}
        result = auth_service.login(body.get("email"), body.get("password"))
        return jsonify(result), 200

    @app.route("/profile", methods=["GET"])
    @token_required
    def profile(current_payload):
        return jsonify(auth_service.get_profile(current_payload["sub"])), 200

    @app.route("/profile/preferences", methods=["PUT"])
    @token_required
    def update_preferences(current_payload):
        body = request.get_json(silent=True) or {}
        result = auth_service.update_preferences(current_payload["sub"], body.get("preferences", []))
        return jsonify(result), 200

    @app.route("/users/<user_id>", methods=["GET"])
    def get_user_internal(user_id):
        """Internal, service-to-service lookup (called by Recommendation
        Service to read a user's preferences). Not exposed through the
        API Gateway's public route table."""
        return jsonify(auth_service.get_profile(user_id)), 200

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "user-service"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5005))
    app.run(host="0.0.0.0", port=port, debug=True)
