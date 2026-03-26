from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Dict, Optional


class _HealthHandler(BaseHTTPRequestHandler):
    health_provider: Optional[Callable[[], Dict[str, object]]] = None
    metrics_provider: Optional[Callable[[], str]] = None

    def do_GET(self) -> None:  # noqa: N802
        if self.path not in ("/health", "/metrics"):
            self.send_response(404)
            self.end_headers()
            return
        if self.path == "/health":
            provider = type(self).health_provider
            payload = (provider() if provider is not None else {"ok": False})
            raw = json.dumps(payload, ensure_ascii=True).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        provider = type(self).metrics_provider
        payload = provider() if provider is not None else ""
        raw = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; version=0.0.4")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


class HealthHttpServer:
    def __init__(
        self,
        host: str,
        port: int,
        health_provider: Callable[[], Dict[str, object]],
        metrics_provider: Optional[Callable[[], str]] = None,
    ) -> None:
        _HealthHandler.health_provider = staticmethod(health_provider)  # type: ignore[assignment]
        _HealthHandler.metrics_provider = staticmethod(metrics_provider or (lambda: ""))  # type: ignore[assignment]
        self._server = ThreadingHTTPServer((host, port), _HealthHandler)
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

