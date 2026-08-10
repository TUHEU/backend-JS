"""
GlobeTrotter — Itinerary Service (Phase 2: Microservices)
Owns: itineraries.json
Endpoints:
  POST   /itineraries
  GET    /itineraries
  GET    /itineraries/<id>
  PUT    /itineraries/<id>
  DELETE /itineraries/<id>
  POST   /itineraries/<id>/share
  GET    /itineraries/internal/user/<user_id>/stops  (internal — Recommendation Service)
  GET    /health
"""
import os
from flask import Flask, request, jsonify

from base import ServiceError
from repository import ItineraryRepository
from auth import token_required
from services import ItineraryService

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ITINERARIES_FILE = os.path.join(DATA_DIR, "itineraries.json")


def create_app() -> Flask:
    app = Flask(__name__)

    repository = ItineraryRepository(ITINERARIES_FILE)
    itinerary_service = ItineraryService(repository)

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

    @app.route("/itineraries", methods=["POST"])
    @token_required
    def create_itinerary(current_payload):
        body = request.get_json(silent=True) or {}
        result = itinerary_service.create(
            current_payload["sub"], body.get("title"), body.get("notes"),
            body.get("start_date"), body.get("end_date"), body.get("stops", []),
        )
        return jsonify(result), 201

    @app.route("/itineraries", methods=["GET"])
    @token_required
    def list_itineraries(current_payload):
        result = itinerary_service.list_for_user(current_payload["sub"], current_payload["email"])
        return jsonify(result), 200

    @app.route("/itineraries/<itinerary_id>", methods=["GET"])
    @token_required
    def get_itinerary(current_payload, itinerary_id):
        result = itinerary_service.get(itinerary_id, current_payload["sub"], current_payload["email"])
        return jsonify(result), 200

    @app.route("/itineraries/<itinerary_id>", methods=["PUT"])
    @token_required
    def update_itinerary(current_payload, itinerary_id):
        body = request.get_json(silent=True) or {}
        result = itinerary_service.update(itinerary_id, current_payload["sub"], body)
        return jsonify(result), 200

    @app.route("/itineraries/<itinerary_id>", methods=["DELETE"])
    @token_required
    def delete_itinerary(current_payload, itinerary_id):
        itinerary_service.delete(itinerary_id, current_payload["sub"])
        return jsonify({"message": "Itinerary deleted"}), 200

    @app.route("/itineraries/<itinerary_id>/share", methods=["POST"])
    @token_required
    def share_itinerary(current_payload, itinerary_id):
        body = request.get_json(silent=True) or {}
        result = itinerary_service.share(itinerary_id, current_payload["sub"], (body.get("email") or "").strip().lower())
        return jsonify(result), 200

    @app.route("/itineraries/internal/user/<user_id>/stops", methods=["GET"])
    def internal_user_stops(user_id):
        """Internal, service-to-service endpoint — Recommendation Service
        calls this instead of reading itineraries.json directly."""
        return jsonify({"stops": itinerary_service.list_stops_for_user(user_id)}), 200

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "itinerary-service"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port, debug=True)
