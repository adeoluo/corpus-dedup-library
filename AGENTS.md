# AGENTS.md

Working notes for coding agents and contributors in **Corpus Dedup Library**. The [README](README.md)
explains what the project does and why; this file explains how to change it safely.

## Project

A corpus near-deduplication and quality-filtering library built from scratch in Python with a bit-exact Rust core, using MinHash and locality-sensitive hashing, scored for precision, recall, and the fraction of document pairs compared.

## Layout

- `benchmarks/`: benchmark scripts and recorded results
- `docker-compose.yml`: local container setup
- `docs/`: documentation, architecture diagram source and render, design records
- `rust/`: Rust core compiled into a Python extension with PyO3
- `scripts/`: maintenance scripts (release, assets, data)
- `src/`: library and service source
- `tests/`: test suite

Key modules:

- `rust/src/bin/corpus-dedup.rs`: `corpus-dedup`: stream JSONL on stdin, write the deduplicated lines to stdout.
- `rust/src/cluster.rs`: Union-find clustering of confirmed duplicate pairs; the lowest id in a cluster is kept.
- `rust/src/lib.rs`: Rust core of corpus-dedup-library: MinHash signatures, LSH banding, and clustering.
- `rust/src/lsh.rs`: LSH banding: documents sharing any band bucket become candidate pairs.
- `rust/src/minhash.rs`: MinHash signatures over hashed word shingles.
- `rust/src/python.rs`: PyO3 bindings, built by maturin into the `corpus_dedup_rs` extension module.
- `src/corpus_dedup_library/__init__.py`: Corpus Dedup Library - MinHash and LSH near-deduplication from scratch.
- `src/corpus_dedup_library/backend.py`: Optional Rust backend, used when the ``corpus_dedup_rs`` extension is installed.
- `src/corpus_dedup_library/cli.py`: Command line interface for the corpus deduplication library.
- `src/corpus_dedup_library/data.py`: A deterministic synthetic corpus with injected near-duplicates.
- `src/corpus_dedup_library/dedup.py`: The near-deduplication pipeline: candidates, verification, and clustering.
- `src/corpus_dedup_library/evaluation.py`: Evaluation: near-duplicate detection quality and candidate-pair reduction.
- `src/corpus_dedup_library/lsh.py`: Locality-sensitive hashing over MinHash signatures.
- `src/corpus_dedup_library/minhash.py`: MinHash signatures over shingled text.
- `src/corpus_dedup_library/observability.py`: In-process request metrics for the HTTP service (Prometheus text exposition).
- `src/corpus_dedup_library/quality.py`: Heuristic quality filtering, in the spirit of large-corpus cleaning pipelines.
- `src/corpus_dedup_library/service.py`: A standard-library HTTP service for near-deduplication and quality filtering.

## Commands

| Command | Purpose |
|---|---|
| `make help` | Show this help |
| `make setup` | Install dependencies and pre-commit hooks |
| `make format` | Format automatically |
| `make lint` | Lint (no fixes) |
| `make type` | Type-check |
| `make test` | Run tests |
| `make coverage` | Tests with coverage gate |
| `make rust-check` | Rust core: fmt, clippy (with and without Python), unit tests |
| `make rust-develop` | Build the Rust extension into .venv (opt-in rust group) |
| `make parity` | Rust vs Python parity tests (requires rust-develop) |
| `make bench-compare` | Python vs Rust throughput (requires rust-develop) |
| `make evaluation` | Reproduce the results table |
| `make run` | Run the HTTP service |
| `make diagram` | Render architecture diagram to SVG |
| `make docker-build` | Build the image |
| `make docker-up` | Run via docker compose |
| `make clean` | Remove caches and artifacts |
| `make all` | Full local gate (mirror of continuous integration) |
| `make changelog` | Regenerate CHANGELOG.md from Conventional Commits (git-cliff) |
| `make cut-release` | Cut a release locally: version bump, changelog, tag, GitHub release (RELEASE_VERSION=vX.Y.Z optional) |

Run the full local gate (`make all`) before committing; CI runs the same checks.

## Conventions

- Commits follow Conventional Commits (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, `test:`, `ci:`, `chore:`).
  The changelog and the next version number are derived from them.
- Every number quoted in the README is produced by a command in this repository. When behavior
  changes, rerun that command and update the number in the same commit.
- When a component is added, removed or renamed, update `docs/architecture/architecture.mmd`
  and re-render `architecture.svg` so the diagram matches the code.
- README sections keep their fixed order. Prose avoids em and en dashes and promotional wording.
- Tests accompany behavior changes; a bug fix comes with a test that fails without it.
- Releases are cut by the maintainer with `make cut-release`, never from CI.

## Python notes

- Python is managed with `uv`; run commands through `uv run` so the locked environment is used.
- Lint and format with `ruff`; type-check with `mypy`; tests use `pytest`.
- Public functions carry type hints and a docstring that states the contract, not the steps.

## Rust notes

- `cargo fmt --check` and `cargo clippy --all-targets -- -D warnings` must pass.
- No `unwrap()` in library code paths that can fail at runtime; return a typed error.
- Unsafe code is limited to the places that need a syscall and carries a `SAFETY:` comment.
