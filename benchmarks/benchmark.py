"""A deterministic micro-benchmark for near-duplicate detection.

Builds a labeled corpus with injected near-duplicates and reports detection
precision and recall against ground truth, plus the reduction in candidate pairs
that LSH achieves over an all-pairs comparison. Deterministic and offline; run
with:

    uv run python benchmarks/benchmark.py
"""

from __future__ import annotations

import time

from corpus_dedup_library.data import make_corpus
from corpus_dedup_library.evaluation import evaluate_detection


def main() -> None:
    for unique, duplicates in ((50, 40), (150, 120)):
        corpus = make_corpus(unique=unique, duplicates=duplicates, seed=0)
        start = time.perf_counter()
        report = evaluate_detection(corpus)
        elapsed = (time.perf_counter() - start) * 1000
        print(f"Corpus of {len(corpus.documents)} documents ({duplicates} near-duplicates):")
        print(f"  {report.format()}  [{elapsed:.0f} ms]")


if __name__ == "__main__":
    main()
