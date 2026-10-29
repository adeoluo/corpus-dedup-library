"""Tests for the HTTP service routing and the CLI."""

from __future__ import annotations

from corpus_dedup_library.cli import main
from corpus_dedup_library.service import DedupService, handle

_SERVICE = DedupService()


def test_health_and_ready() -> None:
    status, payload = handle("GET", "/health", {}, _SERVICE)
    assert status == 200 and payload["status"] == "ok"
    status, payload = handle("GET", "/ready", {}, _SERVICE)
    assert status == 200 and payload["status"] == "ready"


def test_dedup_route() -> None:
    docs = [
        "the cat sat on the mat today in the warm afternoon sun",
        "the cat sat on the mat today in the warm afternoon sun please note",
        "an entirely different document about markets and finance and economics here",
    ]
    status, payload = handle("POST", "/dedup", {"documents": docs, "threshold": 0.5}, _SERVICE)
    assert status == 200
    assert len(payload["keep"]) + len(payload["drop"]) == 3
    assert payload["drop"] == [1]


def test_dedup_validation() -> None:
    for body in ({"documents": []}, {"documents": [1, 2]}, {"documents": ["x"], "threshold": 2.0}):
        status, _ = handle("POST", "/dedup", body, _SERVICE)
        assert status == 400


def test_quality_route() -> None:
    good = "the research team published a new method for training models efficiently this quarter"
    status, payload = handle("POST", "/quality", {"text": good}, _SERVICE)
    assert status == 200 and payload["passed"] is True
    status, payload = handle("POST", "/quality", {"text": "!!! @@@ ###"}, _SERVICE)
    assert status == 200 and payload["passed"] is False
    status, _ = handle("POST", "/quality", {"text": 5}, _SERVICE)
    assert status == 400


def test_report_route() -> None:
    status, payload = handle("GET", "/report", {}, _SERVICE)
    assert status == 200
    assert payload["precision"] >= 0.95 and payload["recall"] >= 0.95
    assert payload["candidate_reduction"] > 10


def test_unknown_route_and_metrics() -> None:
    status, _ = handle("GET", "/nope", {}, _SERVICE)
    assert status == 404
    handle("GET", "/report", {}, _SERVICE)
    assert "service_requests_total" in _SERVICE.metrics.render_prometheus()


def test_cli_commands(capsys) -> None:  # type: ignore[no-untyped-def]
    common = ["--unique", "30", "--duplicates", "20"]
    main(["dedup", *common])
    main(["report", *common])
    main(["quality", *common])
    out = capsys.readouterr().out
    assert "candidate pairs compared" in out
    assert "precision=" in out
    assert "Quality filter" in out
