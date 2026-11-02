"""Throughput of the Python and Rust backends on the same synthetic corpus.

Builds a corpus with planted near-duplicates, checks that both backends return the
same result, and prints documents per second for each.
"""

from __future__ import annotations

import os
import random
import time

from corpus_dedup_library.backend import rust_available
from corpus_dedup_library.dedup import deduplicate

WORDS = [f"w{i}" for i in range(5000)]


def corpus(n: int, seed: int = 0) -> list[str]:
    rng = random.Random(seed)
    docs = [" ".join(rng.choice(WORDS) for _ in range(rng.randint(80, 200))) for _ in range(n)]
    for i in range(0, n, 5):
        words = docs[i].split()
        for _ in range(3):
            words[rng.randrange(len(words))] = rng.choice(WORDS)
        docs.append(" ".join(words))
    return docs


def timed(docs: list[str], backend: str) -> tuple[float, object]:
    start = time.perf_counter()
    result = deduplicate(docs, backend=backend)
    return time.perf_counter() - start, result


def main() -> None:
    if not rust_available():
        raise SystemExit("build the Rust core first: uv sync (or make rust-develop)")
    print(f"cpus={os.cpu_count()}")
    print("| documents | python s | rust s | speedup | identical |")
    print("|---:|---:|---:|---:|:---:|")
    for n in (1_000, 5_000, 20_000):
        docs = corpus(n)
        py_s, py = timed(docs, "python")
        rs_s, rs = timed(docs, "rust")
        print(f"| {len(docs):,} | {py_s:.2f} | {rs_s:.3f} | {py_s / rs_s:.0f}x | {py == rs} |")


if __name__ == "__main__":
    main()
