"""Corpus Dedup Library - MinHash and LSH near-deduplication from scratch."""

from __future__ import annotations

from corpus_dedup_library.data import Corpus, make_corpus
from corpus_dedup_library.dedup import DedupResult, all_pairs_count, deduplicate
from corpus_dedup_library.evaluation import DetectionReport, evaluate_detection
from corpus_dedup_library.lsh import LSHIndex, build_index
from corpus_dedup_library.minhash import (
    MinHasher,
    estimated_jaccard,
    exact_jaccard,
    shingles,
)
from corpus_dedup_library.quality import QualityConfig, QualityReport, assess, filter_corpus

__version__ = "0.1.0"

__all__ = [
    "Corpus",
    "DedupResult",
    "DetectionReport",
    "LSHIndex",
    "MinHasher",
    "QualityConfig",
    "QualityReport",
    "__version__",
    "all_pairs_count",
    "assess",
    "build_index",
    "deduplicate",
    "estimated_jaccard",
    "evaluate_detection",
    "exact_jaccard",
    "filter_corpus",
    "make_corpus",
    "shingles",
]
