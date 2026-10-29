# Evaluation Report - Corpus Dedup Library

> Reproduce with `python -m corpus_dedup_library report` and `benchmarks/benchmark.py`. The corpus
> and all hashing are deterministic.

## Setup

- **Corpus:** distinct documents built from random word sequences, plus injected near-duplicates
  (exact copies, an appended clause, a changed first word).
- **Metrics:** precision and recall of removing the injected near-duplicates, and the number of
  candidate pairs LSH compares versus the all-pairs count.
- **Configuration:** MinHash with 64 permutations, LSH with 16 bands of 4 rows, 2-word shingles,
  Jaccard threshold 0.6.
- **Hardware / cost:** CPU only; a report runs in a fraction of a second. No external services.

## Detection quality and candidate reduction

| Corpus size | Precision | Recall | F1 | Candidate pairs | All pairs | Reduction |
|---|---:|---:|---:|---:|---:|---:|
| 90 | 1.000 | 1.000 | 1.000 | 52 | 4,005 | 77x |
| 270 | 1.000 | 1.000 | 1.000 | 174 | 36,315 | 209x |

Detection is exact on this corpus. The candidate-pair count grows far more slowly than the quadratic
all-pairs count, so the reduction grows with corpus size: from 77x at 90 documents to 209x at 270.

## Correctness of the pieces

- MinHash signature agreement estimates Jaccard similarity to within about 0.2 of the exact value on
  a hand-checked pair, and signatures are deterministic.
- LSH shortlists a similar pair and excludes an unrelated one in a dedicated test.
- The estimated and exact verification modes drop the same documents on the benchmark corpus.

## Quality filtering

The heuristic filters accept natural prose and reject degenerate text: too few words, too few stop
words, too many symbols, heavy repetition, and empty strings each trigger a named reason, and the
thresholds are configurable.

## Service performance

Each `/dedup` request rebuilds signatures for its batch, so throughput reflects pure-Python hashing;
a small-batch stress benchmark sustains tens of requests per second with p50 near 30 ms. The
algorithmic win is in the number of pairwise comparisons avoided, not in the speed of each hash.

## Reproducibility

- Deterministic given a seed: corpus generation, hashing, and detection all reproduce.
- No network access, no external data.
- Regenerate every number with the CLI and `benchmarks/benchmark.py`.
