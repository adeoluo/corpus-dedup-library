"""A dependency-free HTTP service for near-deduplication and quality filtering.

The service holds no corpus state; each request carries its own documents. It
deduplicates a batch, assesses one document's quality, and reports detection
quality on the built-in labeled corpus. The routing logic is a pure function
tested without a socket.

Endpoints
---------
``GET  /health``    liveness.
``GET  /ready``     readiness.
``GET  /metrics``   per-route request, error, and latency metrics (Prometheus text).
``POST /dedup``     body ``{"documents": [str], "threshold": float?}``; keep and drop ids.
``POST /quality``   body ``{"text": str}``; whether the text passes and why not.
``GET  /report``    near-duplicate detection precision and recall on the built-in corpus.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from corpus_dedup_library.data import make_corpus
from corpus_dedup_library.dedup import deduplicate
from corpus_dedup_library.evaluation import evaluate_detection
from corpus_dedup_library.observability import ServiceMetrics
from corpus_dedup_library.quality import assess

JsonObject = dict[str, Any]
_MAX_DOCS = 2000
_MAX_DOC_CHARS = 20000


@dataclass(frozen=True)
class DedupService:
    """Answers dedup, quality, and report requests. Holds no persistent corpus."""

    metrics: ServiceMetrics = field(default_factory=ServiceMetrics)

    def dedup(self, documents: list[str], threshold: float) -> JsonObject:
        result = deduplicate(documents, threshold=threshold)
        return {
            "keep": result.keep,
            "drop": result.drop,
            "duplicate_pairs": [list(pair) for pair in result.duplicate_pairs],
            "candidate_pairs": result.candidate_pairs,
            "total": result.total,
        }

    def quality(self, text: str) -> JsonObject:
        report = assess(text)
        return {"passed": report.passed, "reasons": list(report.reasons)}

    def report(self) -> JsonObject:
        detection = evaluate_detection(make_corpus(seed=0))
        return {
            "precision": round(detection.precision, 6),
            "recall": round(detection.recall, 6),
            "f1": round(detection.f1, 6),
            "candidate_pairs": detection.candidate_pairs,
            "all_pairs": detection.all_pairs,
            "candidate_reduction": round(detection.candidate_reduction, 3),
        }


def _valid_documents(value: Any) -> list[str] | str:
    if not isinstance(value, list) or not value:
        return "must be a non-empty list of strings"
    if len(value) > _MAX_DOCS:
        return f"at most {_MAX_DOCS} documents"
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or len(item) > _MAX_DOC_CHARS:
            return f"each document must be a string of at most {_MAX_DOC_CHARS} characters"
        out.append(item)
    return out


def _route(
    method: str, path: str, body: Mapping[str, Any], service: DedupService
) -> tuple[int, JsonObject]:
    if method == "GET" and path == "/health":
        return 200, {"status": "ok"}
    if method == "GET" and path == "/report":
        return 200, service.report()
    if method == "POST" and path == "/dedup":
        documents = _valid_documents(body.get("documents"))
        if isinstance(documents, str):
            return 400, {"error": f"'documents' {documents}"}
        threshold = body.get("threshold", 0.6)
        if (
            not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not (0.0 < threshold <= 1.0)
        ):
            return 400, {"error": "'threshold' must be a number in (0, 1]"}
        return 200, service.dedup(documents, float(threshold))
    if method == "POST" and path == "/quality":
        text = body.get("text")
        if not isinstance(text, str) or len(text) > _MAX_DOC_CHARS:
            return 400, {"error": f"'text' must be a string of at most {_MAX_DOC_CHARS} characters"}
        return 200, service.quality(text)
    return 404, {"error": f"no route for {method} {path}"}


def handle(
    method: str, path: str, body: Mapping[str, Any], service: DedupService
) -> tuple[int, JsonObject]:
    """Route a request, recording per-route metrics, and return status and payload."""

    if method == "GET" and path == "/ready":
        return 200, {"status": "ready"}
    start = time.perf_counter()
    status, payload = _route(method, path, body, service)
    service.metrics.observe(
        f"{method} {path}", (time.perf_counter() - start) * 1000.0, error=status >= 400
    )
    return status, payload


class _Handler(BaseHTTPRequestHandler):  # pragma: no cover - exercised over sockets
    service: DedupService

    def _respond(self, status: int, payload: JsonObject) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/metrics":
            body = self.service.metrics.render_prometheus().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        status, payload = handle("GET", self.path, {}, self.service)
        self._respond(status, payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._respond(400, {"error": "request body is not valid JSON"})
            return
        status, payload = handle("POST", self.path, body, self.service)
        self._respond(status, payload)

    def log_message(self, *_: Any) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:  # pragma: no cover
    """Start the HTTP service (blocking)."""

    handler = type("_BoundHandler", (_Handler,), {"service": DedupService()})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"corpus-dedup-library service listening on http://{host}:{port}")
    server.serve_forever()
