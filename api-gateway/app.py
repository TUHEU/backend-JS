"""
GlobeTrotter — API Gateway (Phase 2: Microservices)
The single entry point the Flutter app talks to. Routes each request
to the right backend service and returns its response unchanged.
Flutter's api_service.dart needs only ONE base URL: this gateway's.

Route table:
  /register, /login, /profile*         -> user-service
  /itineraries*                        -> itinerary-service
  /destinations*, /recommendations     -> recommendation-service
"""
import os
from flask import Flask, request, jsonify

from router import GatewayRouter, ServiceProxy

USER_SERVICE_URL = os.environ.get("USER_SERVICE_URL", "http://localhost:5005")
ITINERARY_SERVICE_URL = os.environ.get("ITINERARY_SERVICE_URL", "http://localhost:5006")
RECOMMENDATION_SERVICE_URL = os.environ.get("RECOMMENDATION_SERVICE_URL", "http://localhost:5007")


def create_app() -> Flask:
    app = Flask(__name__)

    user_proxy = ServiceProxy("user-service", USER_SERVICE_URL)
    itinerary_proxy = ServiceProxy("itinerary-service", ITINERARY_SERVICE_URL)
    recommendation_proxy = ServiceProxy("recommendation-service", RECOMMENDATION_SERVICE_URL)

    router = (
        GatewayRouter()
        .register("/register", user_proxy)
        .register("/login", user_proxy)
        .register("/profile", user_proxy)
        .register("/itineraries", itinerary_proxy)
        .register("/destinations", recommendation_proxy)
        .register("/recommendations", recommendation_proxy)
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

    @app.route("/health", methods=["GET"])
    def gateway_health():
        """Aggregate health of every service — handy single call for a
        demo screen showing the distributed system is actually up."""
        statuses = {}
        for name, proxy in (
            ("user-service", user_proxy),
            ("itinerary-service", itinerary_proxy),
            ("recommendation-service", recommendation_proxy),
        ):
            try:
                import requests
                r = requests.get(f"{proxy._base_url}/health", timeout=2.0)
                statuses[name] = "up" if r.status_code == 200 else "degraded"
            except Exception:
                statuses[name] = "down"
        overall = "ok" if all(s == "up" for s in statuses.values()) else "degraded"
        return jsonify({"status": overall, "services": statuses}), 200

    @app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
    def gateway(path):
        proxy = router.resolve(path)
        if proxy is None:
            return jsonify({"error": f"No service registered for /{path}"}), 404
        return proxy.forward(request)

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5004))
    app.run(host="0.0.0.0", port=port, debug=True)
