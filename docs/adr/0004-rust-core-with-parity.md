# ADR 0004: A Rust core that is bit-exact with the Python reference

## Status

Accepted

## Context

Shingling and MinHash dominate runtime: for every document, every shingle is hashed under
every permutation. In Python this runs at about 280 documents per second, which is fine for
the evaluation corpus and far too slow for real corpora. The work is CPU bound and
independent per document.

## Decision

Port shingling, MinHash, LSH banding, and union-find clustering to a Rust crate in `rust/`:

* The Rust code reproduces the Python results bit for bit: the same splitmix64 mix, FNV-style
  token and band hashes, `(a*h + b) mod (2^61 - 1)` permutations computed with 128-bit
  products, Python's `str.lower()` (including final sigma) and Python's `str.split()`
  separators (Unicode White_Space plus U+001C to U+001F).
* Signatures are computed in parallel with rayon, with the GIL released.
* The crate builds a PyO3 extension (`corpus_dedup_rs`, opt-in through maturin) and a
  standalone `corpus-dedup` binary for JSONL streams.
* `deduplicate(..., backend="auto")` uses Rust when the extension is installed; Python stays
  the reference and the default when it is not.

## Consequences

* About 150 to 175 times faster end to end on synthetic corpora, with identical results.
* Two implementations must stay in step. `tests/test_rust_parity.py` compares them in CI
  with the extension required, so any divergence fails the build.
* Installing the Rust backend needs a Rust toolchain; the pure Python install is unchanged.

## Update: the Rust core is the default, including exact verification

The package now builds with maturin, so every install compiles the Rust core into it and
`backend="auto"` always finds it. `exact=True` also runs in Rust: shingle sets are built in
parallel for the documents that appear in a candidate pair, and each pair's exact Jaccard is
computed by merging the two sorted sets. It returns the same result as the Python path, which
the parity tests check, and costs about the same time as the estimate mode.
