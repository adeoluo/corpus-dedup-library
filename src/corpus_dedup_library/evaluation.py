"""Evaluation: near-duplicate detection quality and candidate-pair reduction."""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass

from corpus_dedup_library.data import Corpus, make_corpus
from corpus_dedup_library.dedup import all_pairs_count, deduplicate


@dataclass(frozen=True)
class DetectionReport:
    """Precision and recall of near-duplicate detection against ground truth."""

    precision: float
    recall: float
    true_positives: int
    false_positives: int
    false_negatives: int
    candidate_pairs: int
    all_pairs: int

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)

    @property
    def candidate_reduction(self) -> float:
        if self.candidate_pairs == 0:
            return float(self.all_pairs)
        return self.all_pairs / self.candidate_pairs

    def format(self) -> str:
        return (
            f"precision={self.precision:.3f}, recall={self.recall:.3f}, f1={self.f1:.3f}; "
            f"{self.candidate_pairs}/{self.all_pairs} pairs compared "
            f"({self.candidate_reduction:.0f}x fewer)"
        )


def evaluate_detection(
    corpus: Corpus,
    *,
    threshold: float = 0.6,
    bands: int = 16,
    rows: int = 4,
    k: int = 2,
    seed: int = 0,
) -> DetectionReport:
    """Return precision and recall of dropping near-duplicates in ``corpus``.

    A dropped document is a true positive if it was an injected near-duplicate.
    """

    result = deduplicate(
        corpus.documents, threshold=threshold, bands=bands, rows=rows, k=k, seed=seed
    )
    true_dups = set(corpus.duplicate_of.keys())
    dropped = set(result.drop)
    true_positives = len(true_dups & dropped)
    false_positives = len(dropped - true_dups)
    false_negatives = len(true_dups - dropped)
    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 1.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 1.0
    )
    return DetectionReport(
        precision=precision,
        recall=recall,
        true_positives=true_positives,
        false_positives=false_positives,
        false_negatives=false_negatives,
        candidate_pairs=result.candidate_pairs,
        all_pairs=all_pairs_count(len(corpus.documents)),
    )


@dataclass(frozen=True)
class ScaleReport:
    """Throughput, memory, and quality for one corpus size under a scale run."""

    documents: int
    seconds: float
    peak_mebibytes: float
    candidate_pairs: int
    all_pairs: int
    precision: float
    recall: float

    @property
    def docs_per_second(self) -> float:
        return self.documents / self.seconds if self.seconds else 0.0

    @property
    def candidate_reduction(self) -> float:
        if self.candidate_pairs == 0:
            return float(self.all_pairs)
        return self.all_pairs / self.candidate_pairs

    def format(self) -> str:
        return (
            f"n={self.documents:>6}: {self.seconds:7.2f}s "
            f"({self.docs_per_second:8.0f} docs/s), peak {self.peak_mebibytes:6.1f} MiB, "
            f"{self.candidate_pairs} candidate pairs ({self.candidate_reduction:.0f}x fewer), "
            f"precision={self.precision:.3f}, recall={self.recall:.3f}"
        )


def scale_report(
    *,
    unique: int,
    duplicates: int,
    threshold: float = 0.6,
    bands: int = 16,
    rows: int = 4,
    k: int = 2,
    seed: int = 0,
) -> ScaleReport:
    """Run deduplication on a freshly generated corpus and measure cost at scale.

    Reports wall-clock time, peak allocated memory (via ``tracemalloc``), the
    candidate-pair reduction over an all-pairs comparison, and precision/recall
    against the injected ground truth. This is synthetic data, so it measures
    throughput and memory behavior, not accuracy on real web text.
    """

    corpus = make_corpus(unique=unique, duplicates=duplicates, seed=seed)
    tracemalloc.start()
    start = time.perf_counter()
    result = deduplicate(
        corpus.documents, threshold=threshold, bands=bands, rows=rows, k=k, seed=seed
    )
    seconds = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    true_dups = set(corpus.duplicate_of.keys())
    dropped = set(result.drop)
    true_positives = len(true_dups & dropped)
    false_positives = len(dropped - true_dups)
    false_negatives = len(true_dups - dropped)
    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 1.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 1.0
    )
    return ScaleReport(
        documents=len(corpus.documents),
        seconds=seconds,
        peak_mebibytes=peak / (1024 * 1024),
        candidate_pairs=result.candidate_pairs,
        all_pairs=all_pairs_count(len(corpus.documents)),
        precision=precision,
        recall=recall,
    )
