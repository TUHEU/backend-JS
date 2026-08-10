"""Facade + Proxy pattern: the gateway exposes ONE surface to the
Flutter app and hides three independent services behind it. A route
table maps a path prefix to a `ServiceProxy`; each proxy knows how to
forward a Flask request to its backend and hand the response straight
back, byte for byte.
"""
from __future__ import annotations
import requests
from flask import Response


class ServiceProxy:
    """Forwards one inbound request to one backend microservice."""

    def __init__(self, name: str, base_url: str, timeout: float = 10.0):
        self.name = name
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def forward(self, request) -> Response:
        target_url = f"{self._base_url}{request.full_path}".rstrip("?")
        headers = {k: v for k, v in request.headers if k.lower() != "host"}
        try:
            upstream = requests.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=request.get_data(),
                timeout=self._timeout,
                allow_redirects=False,
            )
        except requests.RequestException:
            return Response(
                '{"error": "%s is unavailable"}' % self.name,
                status=503,
                mimetype="application/json",
            )

        excluded = {"content-encoding", "content-length", "transfer-encoding", "connection"}
        response_headers = [(k, v) for k, v in upstream.raw.headers.items() if k.lower() not in excluded]
        return Response(upstream.content, status=upstream.status_code, headers=response_headers)


class GatewayRouter:
    """Holds the (prefix -> ServiceProxy) table and picks the right
    proxy for an incoming path. Ordered so the most specific prefixes
    are matched first (e.g. '/itineraries' before a catch-all)."""

    def __init__(self):
        self._routes: list[tuple[str, ServiceProxy]] = []

    def register(self, prefix: str, proxy: ServiceProxy) -> "GatewayRouter":
        self._routes.append((prefix, proxy))
        return self

    def resolve(self, path: str) -> ServiceProxy | None:
        for prefix, proxy in self._routes:
            if path == prefix.lstrip("/") or path.startswith(prefix.lstrip("/") + "/"):
                return proxy
        return None
