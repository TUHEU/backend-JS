"""
GlobeTrotter Travel Assistant — Phase 1: The Monolith
A single Flask server handling all requests, with data stored in JSON files.
Scope: Yaoundé, Cameroon destinations only.

Endpoints implemented:
  POST /register              - Register a new user
  POST /login                 - Authenticate a user, returns JWT
  GET  /destinations          - Search destinations (?q=, ?category=)
  GET  /destinations/<id>     - Get a single destination
  GET  /recommendations       - Get personalized recommendations (auth required)
  POST /itineraries           - Create a new itinerary (auth required)
  GET  /itineraries           - Get current user's itineraries (auth required)
  GET  /itineraries/<id>      - Get one itinerary (auth required, owner or shared)
  PUT  /itineraries/<id>      - Update an itinerary (auth required, owner only)
  DELETE /itineraries/<id>    - Delete an itinerary (auth required, owner only)
  POST /itineraries/<id>/share- Share an itinerary with another user by email
  POST /destinations/<id>/reviews - Add a review/rating for a destination (auth required)
"""

from flask import Flask, request, jsonify
from functools import wraps
from datetime import datetime, timedelta, timezone
import jwt
import json
import os
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)


@app.after_request
def add_cors_headers(response):
    """Allow requests from any origin (needed for Flutter web builds; mobile/
    desktop builds aren't affected by CORS but this makes the API usable from
    a browser too, e.g. for quick manual testing)."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    return response


@app.route("/<path:_any>", methods=["OPTIONS"])
def cors_preflight(_any):
    return ("", 204)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("GLOBETROTTER_SECRET", "dev-secret-change-in-prod")
TOKEN_EXPIRY_HOURS = 24

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
DESTINATIONS_FILE = os.path.join(DATA_DIR, "destinations.json")
ITINERARIES_FILE = os.path.join(DATA_DIR, "itineraries.json")

_lock_files = {}


# ---------------------------------------------------------------------------
# JSON "data access" layer (Phase 1 requirement: JSON file storage, no DB)
# ---------------------------------------------------------------------------
def _read_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return json.loads(content) if content else []


def _write_json(path, data):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def get_users():
    return _read_json(USERS_FILE)


def save_users(users):
    _write_json(USERS_FILE, users)


def get_destinations():
    return _read_json(DESTINATIONS_FILE)


def save_destinations(destinations):
    _write_json(DESTINATIONS_FILE, destinations)


def get_itineraries():
    return _read_json(ITINERARIES_FILE)


def save_itineraries(itineraries):
    _write_json(ITINERARIES_FILE, itineraries)


# ---------------------------------------------------------------------------
# Auth helpers (Simple JWT-based authentication)
# ---------------------------------------------------------------------------
def generate_token(user_id, email):
    payload = {
        "sub": user_id,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token):
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or malformed Authorization header"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        users = get_users()
        current_user = next((u for u in users if u["id"] == payload["sub"]), None)
        if not current_user:
            return jsonify({"error": "User not found"}), 401
        return f(current_user, *args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------
@app.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "password must be at least 6 characters"}), 400

    users = get_users()
    if any(u["email"] == email for u in users):
        return jsonify({"error": "An account with this email already exists"}), 409

    user = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "preferences": body.get("preferences", []),  # e.g. ["nature", "history", "nightlife"]
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users.append(user)
    save_users(users)

    token = generate_token(user["id"], user["email"])
    return jsonify({
        "token": token,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"],
                  "preferences": user["preferences"]},
    }), 201


@app.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    users = get_users()
    user = next((u for u in users if u["email"] == email), None)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = generate_token(user["id"], user["email"])
    return jsonify({
        "token": token,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"],
                  "preferences": user.get("preferences", [])},
    }), 200


# ---------------------------------------------------------------------------
# Destinations endpoints (scope: Yaoundé)
# ---------------------------------------------------------------------------
@app.route("/destinations", methods=["GET"])
def list_destinations():
    q = (request.args.get("q") or "").strip().lower()
    category = (request.args.get("category") or "").strip().lower()

    destinations = get_destinations()

    if q:
        destinations = [
            d for d in destinations
            if q in d["name"].lower()
            or q in d.get("neighborhood", "").lower()
            or q in d.get("description", "").lower()
            or any(q in tag.lower() for tag in d.get("tags", []))
        ]
    if category:
        destinations = [d for d in destinations if d.get("category", "").lower() == category]

    # lightweight response: don't send full review bodies in list view
    summary = [
        {
            "id": d["id"],
            "name": d["name"],
            "neighborhood": d.get("neighborhood"),
            "category": d.get("category"),
            "description": d.get("description"),
            "tags": d.get("tags", []),
            "popularity_score": d.get("popularity_score", 0),
            "avg_rating": _avg_rating(d),
            "image": d.get("image"),
            "location": d.get("location"),
            "price_fcfa": d.get("price_fcfa"),
        }
        for d in destinations
    ]
    return jsonify({"count": len(summary), "destinations": summary}), 200


@app.route("/destinations/<destination_id>", methods=["GET"])
def get_destination(destination_id):
    destinations = get_destinations()
    destination = next((d for d in destinations if d["id"] == destination_id), None)
    if not destination:
        return jsonify({"error": "Destination not found"}), 404
    out = dict(destination)
    out["avg_rating"] = _avg_rating(destination)
    return jsonify(out), 200


@app.route("/destinations/<destination_id>/reviews", methods=["POST"])
@token_required
def add_review(current_user, destination_id):
    body = request.get_json(silent=True) or {}
    rating = body.get("rating")
    comment = (body.get("comment") or "").strip()

    if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        return jsonify({"error": "rating must be a number between 1 and 5"}), 400

    destinations = get_destinations()
    destination = next((d for d in destinations if d["id"] == destination_id), None)
    if not destination:
        return jsonify({"error": "Destination not found"}), 404

    review = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "user_name": current_user["name"],
        "rating": rating,
        "comment": comment,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    destination.setdefault("reviews", []).append(review)
    save_destinations(destinations)

    return jsonify({"review": review, "avg_rating": _avg_rating(destination)}), 201


def _avg_rating(destination):
    reviews = destination.get("reviews", [])
    if not reviews:
        return None
    return round(sum(r["rating"] for r in reviews) / len(reviews), 1)


# ---------------------------------------------------------------------------
# Recommendations (based on user preferences, past trips, and popularity)
# ---------------------------------------------------------------------------
@app.route("/recommendations", methods=["GET"])
@token_required
def get_recommendations(current_user):
    destinations = get_destinations()
    itineraries = get_itineraries()

    user_preferences = set(t.lower() for t in current_user.get("preferences", []))

    visited_tags = set()
    for itinerary in itineraries:
        if itinerary["user_id"] == current_user["id"]:
            for stop in itinerary.get("stops", []):
                dest = next((d for d in destinations if d["id"] == stop.get("destination_id")), None)
                if dest:
                    visited_tags.update(tag.lower() for tag in dest.get("tags", []))

    scored = []
    for d in destinations:
        tags = set(tag.lower() for tag in d.get("tags", []))
        score = 0.0
        score += 3 * len(tags & user_preferences)
        score += 1.5 * len(tags & visited_tags)
        score += (d.get("popularity_score", 0) or 0) * 0.1
        avg = _avg_rating(d)
        if avg:
            score += avg * 0.5
        scored.append((score, d))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    top = [
        {
            "id": d["id"],
            "name": d["name"],
            "neighborhood": d.get("neighborhood"),
            "category": d.get("category"),
            "description": d.get("description"),
            "tags": d.get("tags", []),
            "avg_rating": _avg_rating(d),
            "match_score": round(score, 2),
            "image": d.get("image"),
        }
        for score, d in scored[:10]
    ]
    return jsonify({"recommendations": top}), 200


# ---------------------------------------------------------------------------
# Itineraries endpoints
# ---------------------------------------------------------------------------
@app.route("/itineraries", methods=["POST"])
@token_required
def create_itinerary(current_user):
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    stops = body.get("stops", [])

    if not title:
        return jsonify({"error": "title is required"}), 400
    if not isinstance(stops, list):
        return jsonify({"error": "stops must be a list"}), 400

    itinerary = {
        "id": str(uuid.uuid4()),
        "user_id": current_user["id"],
        "title": title,
        "notes": body.get("notes", ""),
        "start_date": body.get("start_date"),
        "end_date": body.get("end_date"),
        "stops": stops,  # [{destination_id, day, note}]
        "shared_with": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    itineraries = get_itineraries()
    itineraries.append(itinerary)
    save_itineraries(itineraries)
    return jsonify(itinerary), 201


@app.route("/itineraries", methods=["GET"])
@token_required
def list_itineraries(current_user):
    itineraries = get_itineraries()
    mine = [i for i in itineraries if i["user_id"] == current_user["id"]]
    shared = [i for i in itineraries if current_user["email"] in i.get("shared_with", [])]
    return jsonify({"itineraries": mine, "shared_with_me": shared}), 200


@app.route("/itineraries/<itinerary_id>", methods=["GET"])
@token_required
def get_itinerary(current_user, itinerary_id):
    itineraries = get_itineraries()
    itinerary = next((i for i in itineraries if i["id"] == itinerary_id), None)
    if not itinerary:
        return jsonify({"error": "Itinerary not found"}), 404
    if itinerary["user_id"] != current_user["id"] and current_user["email"] not in itinerary.get("shared_with", []):
        return jsonify({"error": "You do not have access to this itinerary"}), 403
    return jsonify(itinerary), 200


@app.route("/itineraries/<itinerary_id>", methods=["PUT"])
@token_required
def update_itinerary(current_user, itinerary_id):
    body = request.get_json(silent=True) or {}
    itineraries = get_itineraries()
    itinerary = next((i for i in itineraries if i["id"] == itinerary_id), None)
    if not itinerary:
        return jsonify({"error": "Itinerary not found"}), 404
    if itinerary["user_id"] != current_user["id"]:
        return jsonify({"error": "Only the owner can edit this itinerary"}), 403

    for field in ["title", "notes", "start_date", "end_date", "stops"]:
        if field in body:
            itinerary[field] = body[field]
    itinerary["updated_at"] = datetime.now(timezone.utc).isoformat()
    save_itineraries(itineraries)
    return jsonify(itinerary), 200


@app.route("/itineraries/<itinerary_id>", methods=["DELETE"])
@token_required
def delete_itinerary(current_user, itinerary_id):
    itineraries = get_itineraries()
    itinerary = next((i for i in itineraries if i["id"] == itinerary_id), None)
    if not itinerary:
        return jsonify({"error": "Itinerary not found"}), 404
    if itinerary["user_id"] != current_user["id"]:
        return jsonify({"error": "Only the owner can delete this itinerary"}), 403

    itineraries = [i for i in itineraries if i["id"] != itinerary_id]
    save_itineraries(itineraries)
    return jsonify({"message": "Itinerary deleted"}), 200


@app.route("/itineraries/<itinerary_id>/share", methods=["POST"])
@token_required
def share_itinerary(current_user, itinerary_id):
    body = request.get_json(silent=True) or {}
    share_email = (body.get("email") or "").strip().lower()
    if not share_email:
        return jsonify({"error": "email is required"}), 400

    itineraries = get_itineraries()
    itinerary = next((i for i in itineraries if i["id"] == itinerary_id), None)
    if not itinerary:
        return jsonify({"error": "Itinerary not found"}), 404
    if itinerary["user_id"] != current_user["id"]:
        return jsonify({"error": "Only the owner can share this itinerary"}), 403

    if share_email not in itinerary.get("shared_with", []):
        itinerary.setdefault("shared_with", []).append(share_email)
        itinerary["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_itineraries(itineraries)

    return jsonify(itinerary), 200


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "GlobeTrotter Monolith", "scope": "Yaoundé"}), 200


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    for path in [USERS_FILE, ITINERARIES_FILE]:
        if not os.path.exists(path):
            _write_json(path, [])
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
