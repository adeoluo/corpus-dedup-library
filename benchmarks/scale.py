"""A large-scale scaling benchmark for near-duplicate detection.

Runs deduplication on synthetic corpora of increasing size and reports wall-clock
time, throughput, peak memory, candidate-pair reduction, and precision/recall
against the injected ground truth. This is synthetic data, so it measures
throughput and memory behavior, not accuracy on real web text. Deterministic and
offline; run with:

    uv run python benchmarks/scale.py
"""

from __future__ import annotations

from corpus_dedup_library.evaluation import scale_report


def main() -> None:
    print("Deduplication at scale (synthetic corpora; two thirds unique, one third near-copies):")
    for unique in (700, 2000, 4000, 7000):
        duplicates = unique // 2
        print(f"  {scale_report(unique=unique, duplicates=duplicates).format()}")


if __name__ == "__main__":
    main()
