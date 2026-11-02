"""The Rust core must reproduce the Python implementation exactly.

Skipped when the ``corpus_dedup_rs`` extension is not built, unless
``DEDUP_REQUIRE_RUST=1`` (set in CI), in which case a missing extension fails.
"""

from __future__ import annotations

import os
import random

import pytest

from corpus_dedup_library.backend import extension, resolve_backend, rust_available
from corpus_dedup_library.dedup import deduplicate
from corpus_dedup_library.lsh import LSHIndex
from corpus_dedup_library.minhash import MinHasher

if os.environ.get("DEDUP_REQUIRE_RUST") == "1":
    assert rust_available(), "DEDUP_REQUIRE_RUST=1 but corpus_dedup_rs is not importable"
pytestmark = pytest.mark.skipif(not rust_available(), reason="Rust extension not built")

ALPHABET = "abcdefgh ÉéßΣσςİi"  # noqa: RUF001
ALPHABET += "\u00a0\u1680\u2003\u001c\u001d\t\n\u3000日本語😀"
ADVERSARIAL = [
    "",
    "   ",
    "one",
    "One two",
    "ΑΣ ΟΔΟΣ ΣΑΣ",
    "İstanbul ISTANBUL",
    "Straße STRASSE",
    "a\u001cb\u001dc\u001ed\u001ff",
    "tab\tnew\nline\u00a0nbsp\u2028sep",
    "emoji 😀 😀 family 👨‍👩‍👧",
]


def random_texts(n: int, seed: int) -> list[str]:
    rng = random.Random(seed)
    base = ["".join(rng.choice(ALPHABET) for _ in range(rng.randint(0, 60))) for _ in range(n)]
    # Near-duplicates: copies with a few words edited.
    for i in range(0, n, 3):
        words = base[i].split()
        if words:
            words[rng.randrange(len(words))] = "edited"
        base.append(" ".join(words))
    return base


@pytest.mark.parametrize("k", [1, 2, 3, 5])
@pytest.mark.parametrize("seed", [0, 7, 2**40])
def test_signatures_match(k: int, seed: int) -> None:
    texts = ADVERSARIAL + random_texts(150, seed=k * 1000 + seed % 997)
    hasher = MinHasher(num_perm=64, k=k, seed=seed)
    expected = [hasher.signature(t) for t in texts]
    assert extension().signatures(texts, 64, k, seed) == expected


@pytest.mark.parametrize(("bands", "rows"), [(16, 4), (32, 2), (8, 8), (1, 64)])
def test_candidate_pairs_match(bands: int, rows: int) -> None:
    texts = random_texts(200, seed=bands)
    hasher = MinHasher(num_perm=bands * rows, k=2, seed=0)
    signatures = [hasher.signature(t) for t in texts]
    index = LSHIndex(bands=bands, rows=rows)
    for doc_id, signature in enumerate(signatures):
        index.add(doc_id, signature)
    rust_pairs = extension().candidate_pairs(signatures, bands, rows)
    assert rust_pairs == sorted(rust_pairs)
    assert set(rust_pairs) == index.candidate_pairs()


def test_candidate_pairs_rejects_wrong_width() -> None:
    with pytest.raises(ValueError, match="bands\\*rows"):
        extension().candidate_pairs([[1, 2, 3]], 2, 2)


@pytest.mark.parametrize("threshold", [0.3, 0.6, 0.9])
def test_deduplicate_results_match(threshold: float) -> None:
    texts = ADVERSARIAL + random_texts(300, seed=int(threshold * 10))
    python = deduplicate(texts, threshold=threshold, backend="python")
    rust = deduplicate(texts, threshold=threshold, backend="rust")
    assert rust == python
    assert python.drop  # the corpus really contains near-duplicates


def test_exact_mode_uses_rust_signatures_with_python_verification() -> None:
    texts = random_texts(120, seed=3)
    assert deduplicate(texts, exact=True, backend="rust") == deduplicate(
        texts, exact=True, backend="python"
    )


def test_auto_prefers_rust() -> None:
    assert resolve_backend("auto") == "rust"
