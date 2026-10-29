"""Tests for MinHash, LSH, deduplication, and quality filtering."""

from __future__ import annotations

from corpus_dedup_library.data import make_corpus
from corpus_dedup_library.dedup import all_pairs_count, deduplicate
from corpus_dedup_library.evaluation import evaluate_detection
from corpus_dedup_library.lsh import LSHIndex, build_index
from corpus_dedup_library.minhash import (
    MinHasher,
    estimated_jaccard,
    exact_jaccard,
    shingles,
)
from corpus_dedup_library.quality import QualityConfig, assess, filter_corpus


def test_shingles_capture_overlap() -> None:
    a = shingles("the quick brown fox jumps", k=2)
    b = shingles("the quick brown fox leaps", k=2)
    assert a & b  # share "the quick", "quick brown", "brown fox"
    assert shingles("", k=2) == set()


def test_exact_jaccard_bounds() -> None:
    assert exact_jaccard("a b c", "a b c") == 1.0
    assert exact_jaccard("a b c d", "w x y z", k=2) == 0.0
    assert 0.0 < exact_jaccard("the cat sat here", "the cat ran here", k=2) < 1.0


def test_minhash_estimates_jaccard() -> None:
    hasher = MinHasher(num_perm=128, k=2, seed=0)
    a = "the research team shipped a new model for text this quarter again"
    b = "the research team shipped a new model for text this quarter now"
    estimate = estimated_jaccard(hasher.signature(a), hasher.signature(b))
    exact = exact_jaccard(a, b, k=2)
    assert abs(estimate - exact) < 0.2


def test_minhash_is_deterministic() -> None:
    hasher = MinHasher(num_perm=64, seed=0)
    assert hasher.signature("hello world foo bar") == hasher.signature("hello world foo bar")


def test_lsh_shortlists_similar_documents() -> None:
    docs = [
        "the cat sat on the mat today",
        "the cat sat on the mat today please note",
        "a totally different sentence about finance markets",
    ]
    index, _ = build_index(docs, bands=16, rows=4, k=2, seed=0)
    pairs = index.candidate_pairs()
    assert (0, 1) in pairs
    assert (0, 2) not in pairs


def test_lsh_rejects_wrong_signature_length() -> None:
    index = LSHIndex(bands=4, rows=4)
    try:
        index.add(0, [1, 2, 3])
    except ValueError as exc:
        assert "signature length" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_deduplicate_removes_near_duplicates() -> None:
    corpus = make_corpus(unique=40, duplicates=30, seed=0)
    result = deduplicate(corpus.documents)
    assert len(result.keep) == 40
    assert len(result.drop) == 30
    assert result.candidate_pairs < all_pairs_count(len(corpus.documents))


def test_deduplicate_exact_mode_agrees() -> None:
    corpus = make_corpus(unique=30, duplicates=20, seed=1)
    estimated = deduplicate(corpus.documents, exact=False)
    exact = deduplicate(corpus.documents, exact=True)
    assert set(estimated.drop) == set(exact.drop)


def test_detection_precision_and_recall_are_high() -> None:
    report = evaluate_detection(make_corpus(unique=50, duplicates=40, seed=0))
    assert report.precision >= 0.95
    assert report.recall >= 0.95
    assert report.candidate_reduction > 10


def test_quality_accepts_natural_prose() -> None:
    good = "the research team published a new method for training models efficiently this quarter"
    assert assess(good).passed


def test_quality_rejects_degenerate_text() -> None:
    assert (
        "too_few_words" in assess("hi there").reasons or "too_few_stopwords" in assess("hi").reasons
    )
    assert "too_many_symbols" in assess("!!! @@@ ### $$$ %%% ^^^").reasons
    assert "too_repetitive" in assess("spam spam spam spam spam spam spam spam").reasons
    assert "empty" in assess("").reasons


def test_filter_corpus_partitions_documents() -> None:
    docs = [
        "the team shipped a new feature for the product this week with care",
        "aaaa",
        "the team shipped a new feature for the product this week with care",
    ]
    keep, rejected = filter_corpus(docs)
    assert 0 in keep
    assert 1 in rejected


def test_quality_config_is_tunable() -> None:
    strict = QualityConfig(min_words=50)
    report = assess("short but otherwise fine sentence here", strict)
    assert not report.passed
