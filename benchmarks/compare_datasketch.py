"""corpus-dedup-library against datasketch on real web text (C4).

Both libraries look for document pairs whose word-bigram Jaccard similarity is at
least the threshold, with 64 MinHash permutations and LSH banding. Every pair either
library reports is then checked with the exact Jaccard similarity, which gives each
library's precision; recall is measured against the union of truly similar pairs
that either library found (a pair neither found is not counted, so recall is an
upper bound for both).

    uv run --no-sync --with datasketch python benchmarks/compare_datasketch.py \\
        --c4 c4-train.00000-of-01024.json.gz --docs 50000
"""

from __future__ import annotations

import argparse
import gzip
import json
import time
from itertools import islice
from pathlib import Path

from corpus_dedup_library.dedup import deduplicate
from corpus_dedup_library.minhash import shingles

ROOT = Path(__file__).resolve().parent.parent


def c4_texts(path: Path, count: int) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line)["text"] for line in islice(handle, count)]


def exact_jaccard(a: set[int], b: set[int]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def run_datasketch(texts: list[str], threshold: float) -> tuple[float, set[tuple[int, int]]]:
    from datasketch import MinHash, MinHashLSH

    start = time.perf_counter()
    tokens = []
    for text in texts:
        words = text.lower().split()
        grams = {" ".join(words[i : i + 2]).encode() for i in range(max(1, len(words) - 1))}
        tokens.append(list(grams))
    hashes = MinHash.bulk(tokens, num_perm=64, seed=1)
    lsh = MinHashLSH(threshold=threshold, num_perm=64)
    pairs: set[tuple[int, int]] = set()
    for i, mh in enumerate(hashes):
        for j in lsh.query(mh):
            if mh.jaccard(hashes[j]) >= threshold:
                pairs.add((j, i))
        lsh.insert(i, mh)
    return time.perf_counter() - start, pairs


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--c4", required=True, type=Path)
    ap.add_argument("--docs", type=int, default=50000)
    ap.add_argument("--threshold", type=float, default=0.6)
    ap.add_argument(
        "--python-docs",
        type=int,
        default=10000,
        help="the Python backend is timed on this many documents",
    )
    ap.add_argument(
        "--out", type=Path, default=ROOT / "benchmarks" / "results" / "c4_datasketch.json"
    )
    args = ap.parse_args()
    texts = c4_texts(args.c4, args.docs)

    start = time.perf_counter()
    ours = deduplicate(texts, threshold=args.threshold, backend="rust")
    ours_s = time.perf_counter() - start
    ours_pairs = {tuple(p) for p in ours.duplicate_pairs}

    start = time.perf_counter()
    exact = deduplicate(texts, threshold=args.threshold, backend="rust", exact=True)
    exact_s = time.perf_counter() - start
    exact_pairs = {tuple(p) for p in exact.duplicate_pairs}

    ds_s, ds_pairs = run_datasketch(texts, args.threshold)

    sub = texts[: args.python_docs]
    start = time.perf_counter()
    deduplicate(sub, threshold=args.threshold, backend="python")
    py_s = time.perf_counter() - start
    start = time.perf_counter()
    deduplicate(sub, threshold=args.threshold, backend="rust")
    rs_sub_s = time.perf_counter() - start

    sets: dict[int, set[int]] = {}

    def true_pair(pair: tuple[int, int]) -> bool:
        for i in pair:
            if i not in sets:
                sets[i] = shingles(texts[i], 2)
        return exact_jaccard(sets[pair[0]], sets[pair[1]]) >= args.threshold

    truth = {p for p in ours_pairs | exact_pairs | ds_pairs if true_pair(p)}
    rows = []
    for name, seconds, pairs in [
        ("corpus-dedup-library (Rust backend)", ours_s, ours_pairs),
        ("corpus-dedup-library (Rust backend, exact=True)", exact_s, exact_pairs),
        ("datasketch MinHashLSH", ds_s, ds_pairs),
    ]:
        correct = len(pairs & truth)
        rows.append(
            {
                "library": name,
                "seconds": seconds,
                "docs_per_s": len(texts) / seconds,
                "pairs": len(pairs),
                "precision": correct / len(pairs) if pairs else 1.0,
                "recall": correct / len(truth) if truth else 1.0,
            }
        )
    report = {
        "documents": len(texts),
        "threshold": args.threshold,
        "true_pairs_found": len(truth),
        "rows": rows,
        "python_backend": {
            "documents": len(sub),
            "python_s": py_s,
            "rust_s": rs_sub_s,
            "speedup": py_s / rs_sub_s,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")

    print(
        f"{len(texts):,} C4 documents, threshold {args.threshold}, 64 permutations; "
        f"{len(truth):,} truly similar pairs found by either library\n"
    )
    print("| Library | Time | Documents/s | Pairs reported | Precision | Recall |")
    print("|---|---:|---:|---:|---:|---:|")
    for r in rows:
        print(
            f"| {r['library']} | {r['seconds']:.1f} s | {r['docs_per_s']:,.0f} | {r['pairs']:,} | "
            f"{r['precision']:.3f} | {r['recall']:.3f} |"
        )
    print(
        f"\nPython backend on {len(sub):,} documents: {py_s:.1f} s; "
        f"Rust backend {rs_sub_s:.2f} s "
        f"({py_s / rs_sub_s:.0f}x)"
    )


if __name__ == "__main__":
    main()
