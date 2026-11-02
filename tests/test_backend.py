"""Backend selection works with and without the Rust extension."""

from __future__ import annotations

import pytest

from corpus_dedup_library import backend
from corpus_dedup_library.dedup import deduplicate


def test_unknown_backend_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown backend"):
        backend.resolve_backend("gpu")


def test_python_backend_is_always_available() -> None:
    assert backend.resolve_backend("python") == "python"
    result = deduplicate(["a b c d", "a b c d", "x y z w"], backend="python")
    assert result.keep == [0, 2]


def test_missing_extension(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backend, "_EXTENSION", None)
    assert backend.resolve_backend("auto") == "python"
    with pytest.raises(RuntimeError, match="not installed"):
        backend.resolve_backend("rust")
