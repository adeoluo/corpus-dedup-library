"""The Rust backend, compiled into the package on install and used by default.

The Rust core in ``rust/`` reproduces the Python MinHash, LSH banding, and clustering bit
for bit, computes signatures in parallel, and releases the GIL. The Python implementation
is always available and is the reference; ``tests/test_rust_parity.py`` checks agreement.
"""

from __future__ import annotations

import importlib
from typing import Any, Literal

Backend = Literal["python", "rust"]
BACKENDS: tuple[str, ...] = ("auto", "python", "rust")


def _load_extension() -> Any:
    # Inside the package for normal installs; top level for an older `maturin develop`.
    for name in ("corpus_dedup_library.corpus_dedup_rs", "corpus_dedup_rs"):
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    return None


_EXTENSION: Any = _load_extension()


def rust_available() -> bool:
    """Return whether the Rust extension is importable."""

    return _EXTENSION is not None


def resolve_backend(backend: str) -> Backend:
    """Map ``auto`` to the fastest available backend and validate explicit choices."""

    if backend not in BACKENDS:
        raise ValueError(f"unknown backend {backend!r}; expected one of {BACKENDS}")
    if backend == "auto":
        return "rust" if rust_available() else "python"
    if backend == "rust" and not rust_available():
        raise RuntimeError(
            "the Rust backend is not built; run `uv sync` or `make rust-develop`, "
            "or use backend='python'"
        )
    return "rust" if backend == "rust" else "python"


def extension() -> Any:
    """Return the loaded extension module (only valid when ``rust_available()``)."""

    return _EXTENSION
