# GlobeTrotter — Phase 2: Microservices

Your Phase 1 monolith (`backend/`) has been decomposed into four
independently-runnable Flask services under `backend-phase2/`, matching
the course slide's architecture exactly. The Flutter app (`frontend/`)
needed **no endpoint changes** — it still talks to one base URL — because
the API Gateway is a transparent facade.

## Services

| Service | Port | Owns | Responsibility |
|---|---|---|---|
| `api-gateway` | 5004 | — | Single entry point for the app; forwards every request to the right service |
| `user-service` | 5005 | `users.json` | Register, login, profile, preferences |
| `itinerary-service` | 5006 | `itineraries.json` | Create/view/update/delete/share itineraries |
| `recommendation-service` | 5007 | `destinations.json` | Destinations, reviews, personalized recommendations |

`recommendation-service` calls `user-service` (for preferences) and
`itinerary-service` (for visited-destination tags) over REST — this is
the "Recommendation Service calling User Service" synchronous pattern
from the slide, implemented in `clients.py` in that service.

## OOP / design patterns used

- **Repository pattern** (`base.py` → `JsonRepository`) — the only
  class in each service allowed to touch the filesystem. Everything
  above it speaks in domain objects, not raw dicts.
- **Service layer** (`services.py` in each service) — business rules
  (validation, ownership checks, scoring) live here, separate from
  Flask routes, which stay thin (parse → call service → serialize).
- **Application Factory** (`create_app()` in every `app.py`) — lets
  each service be instantiated fresh (useful for tests, and keeps
  configuration explicit instead of relying on a global object).
- **DTO / domain models** (`models.py`, dataclasses) — `User`,
  `Itinerary`, `Destination`, `Review` each know how to serialize
  themselves (`to_dict`, `to_public_dict`, ...) instead of that logic
  being scattered across routes.
- **Strategy + Composite** (`recommendation-service/strategies.py`) —
  each scoring rule (preference match, visited-tag similarity,
  popularity, rating) is its own class implementing
  `score(destination, context)`. `RecommendationScorer` composes them.
  Adding a new ranking signal later means adding one class, not
  editing a formula.
- **Proxy / Adapter** (`recommendation-service/clients.py`) —
  `UserServiceClient` and `ItineraryServiceClient` wrap the HTTP calls
  to other services behind plain Python methods, and fail soft
  (empty set) if a service is unreachable, so recommendations degrade
  gracefully instead of crashing.
- **Facade + routing table** (`api-gateway/router.py`) —
  `GatewayRouter` maps path prefixes to `ServiceProxy` objects;
  `ServiceProxy.forward()` is the only place that knows how to talk
  HTTP to a backend service.
- **Custom exception hierarchy** (`ServiceError`) — business-rule
  failures carry their own HTTP status and are translated to JSON in
  one `@app.errorhandler`, instead of every route hand-rolling
  `jsonify({"error": ...}), 4xx`.

## What's new besides the split

- **Real route on the map** — `frontend/lib/services/routing_service.dart`
  is a small OOP wrapper around OSRM (`router.project-osrm.org`), a
  free routing engine built on OpenStreetMap data — no API key. The
  map widget (`destination_map.dart`) now draws the actual road path
  from wherever the user is to the destination, with a distance/time
  chip, instead of just two disconnected pins.
- **Gateway health aggregation** — `GET /health` on the gateway pings
  all three services and reports their status together, useful as a
  visible proof of the distributed architecture for your demo.
- **Graceful degradation** — if User Service or Itinerary Service is
  down, Recommendation Service still responds (falls back to
  popularity/rating only) instead of failing the whole request.

## Running it

**For quick local testing** (each service in its own terminal):
```bash
cd backend-phase2/user-service           && pip install -r requirements.txt && python app.py
cd backend-phase2/itinerary-service      && pip install -r requirements.txt && python app.py
cd backend-phase2/recommendation-service && pip install -r requirements.txt && python app.py
cd backend-phase2/api-gateway            && pip install -r requirements.txt && python app.py
```

**On the VPS, with PM2** (production — this is what's actually deployed):
```bash
cd backend-phase2
./update.sh          # first run: creates venv, installs deps, starts PM2
```
`update.sh` is also what you re-run after every `git pull` — it updates
dependencies and reloads all four services with zero downtime.

Each service runs under `gunicorn` (via `wsgi.py`), managed by PM2
per `ecosystem.config.js`. Only `gt-api-gateway` binds to `0.0.0.0`
(publicly reachable, port 5004) — the other three bind to
`127.0.0.1` only, so they're reachable from the gateway and each
other but not from outside the machine. That's the same "single
externally-reachable port" property Docker's network isolation gave
us, enforced here by bind address instead.

Useful PM2 commands:
```bash
pm2 status                    # see all 4 processes
pm2 logs gt-api-gateway       # tail one service's logs
pm2 restart gt-user-service   # restart a single service
pm2 startup && pm2 save       # make PM2 survive a VPS reboot
```

**With Docker instead**, if you prefer containers:
```bash
cd backend-phase2 && docker compose up --build -d
```
(Also gateway-only on the host — see `docker-compose.yml`.)

The Flutter app's `ApiService.baseUrl` and the web app's
`GLOBETROTTER_API_BASE_URL` should point at the gateway
(`http://<your-vps-ip>:5004`) — same as it did for the monolith, no
other code change needed.

All four services were smoke-tested end-to-end during this session:
register → login → browse destinations → create itinerary → get
recommendations (cross-service call) → post a review — all through
the gateway, all green. The `wsgi.py`/gunicorn wiring was also
verified to serve correctly (via a WSGI test server standing in for
gunicorn, which needs real internet access to install).
