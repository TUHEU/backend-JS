"""
GlobeTrotter — Recommendation Service (Phase 2: Microservices)
Owns: destinations.json
Calls: User Service (preferences), Itinerary Service (visited tags)
Endpoints:
  GET  /destinations
  GET  /destinations/<id>
  POST /destinations/<id>/reviews  (auth)
  GET  /recommendations            (auth)
  GET  /health
"""
import os
from flask import Flask, request, jsonify

from base import ServiceError
from repository import DestinationRepository
from auth import token_required
from clients import UserServiceClient, ItineraryServiceClient
from services import DestinationService, ReviewService, RecommendationService

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DESTINATIONS_FILE = os.path.join(DATA_DIR, "destinations.json")

USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://localhost:5001")
ITINERARY_SERVICE_URL = os.environ.get("ITINERARY_SERVICE_URL", "http://localhost:5002")


def create_app() -> Flask:
    app = Flask(__name__)

    repository = DestinationRepository(DESTINATIONS_FILE)
    destination_service = DestinationService(repository)
    review_service = ReviewService(repository)
    user_client = UserServiceClient(USER_SERVICE_URL)
    recommendation_service = RecommendationService(
        repository,
        user_client,
        ItineraryServiceClient(ITINERARY_SERVICE_URL),
    )

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

    @app.route("/destinations", methods=["GET"])
    def list_destinations():
        results = destination_service.search(request.args.get("q", ""), request.args.get("category", ""))
        return jsonify({"destinations": results}), 200

    @app.route("/destinations/<destination_id>", methods=["GET"])
    def get_destination(destination_id):
        return jsonify(destination_service.get_detail(destination_id)), 200

    @app.route("/destinations/<destination_id>/reviews", methods=["POST"])
    @token_required
    def add_review(current_payload, destination_id):
        body = request.get_json(silent=True) or {}
        user_name = user_client.get_name(current_payload["sub"], fallback=current_payload.get("email", "Traveler"))
        result = review_service.add_review(
            destination_id, current_payload["sub"], user_name,
            body.get("rating"), body.get("comment"),
        )
        return jsonify(result), 201

    @app.route("/recommendations", methods=["GET"])
    @token_required
    def get_recommendations(current_payload):
        results = recommendation_service.recommend_for(current_payload["sub"])
        return jsonify({"recommendations": results}), 200

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "recommendation-service"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port, debug=True)
