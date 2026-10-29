<h1 align="center">Corpus Dedup Library</h1>

<p align="center">
  <em>A corpus near-deduplication and quality-filtering library built from scratch in pure Python, using MinHash and locality-sensitive hashing. It finds near-duplicates with high precision and recall while comparing a tiny fraction of all document pairs.</em>
</p>

<p align="center">
  <a href="https://github.com/adeoluo/corpus-dedup-library/actions/workflows/ci.yml"><img alt="Continuous integration" src="https://github.com/adeoluo/corpus-dedup-library/actions/workflows/ci.yml/badge.svg"></a>
  <img alt="Coverage" src="https://img.shields.io/badge/coverage-93%25-brightgreen">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%20%7C%203.12-blue">
  <img alt="Type checked" src="https://img.shields.io/badge/mypy-strict-blue">
  <img alt="Runtime dependencies" src="https://img.shields.io/badge/runtime%20deps-0-brightgreen">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

---

## Motivation

The quality of a language model is bounded by the quality of its training data, and two of the most
important cleaning steps are **near-deduplication** (removing documents that are near-copies of
each other) and **quality filtering** (dropping degenerate text). Exact deduplication by comparing
every pair is quadratic and misses near-copies that differ by an edit. This library implements the
standard scalable approach from scratch, with **zero runtime dependencies**: **MinHash** estimates
Jaccard similarity cheaply, and **locality-sensitive hashing** shortlists only the pairs likely to
be similar, so the work stays close to linear.

The headline is that it works and that it is cheap: on a labeled corpus it removes near-duplicates
with **perfect precision and recall** while comparing a small fraction of all pairs, and the saving
grows with corpus size.

## Architecture

<p align="center">
  <img src="docs/architecture/architecture.svg" alt="System architecture" width="900">
</p>

Each document is shingled into hashed word k-grams; MinHash reduces the shingle set to a compact
signature; LSH bands the signatures and buckets them so that similar documents collide; candidate
pairs are verified against a Jaccard threshold; and a union-find groups confirmed duplicates so one
representative per cluster is kept. See the [ADRs](docs/adr/) for the key decisions.

## What it implements

- **MinHash** with a deterministic 64-bit hash and a family of ``(a*h + b) mod p`` permutations, so
  signature agreement is an unbiased estimate of Jaccard similarity.
- **LSH banding** with tunable bands and rows to set the similarity threshold for collision.
- **A deduplication pipeline**: candidate generation, threshold verification (estimated or exact),
  union-find clustering, and representative selection.
- **Heuristic quality filters**: length, mean word length, stop-word ratio, symbol ratio, and word
  repetition, each an inspectable rule.

## Results

> Reproduce with `python -m corpus_dedup_library report`. A labeled corpus injects known
> near-duplicates (exact copies, an appended clause, a changed word) so detection can be scored.

| Corpus size | Precision | Recall | Pairs compared | Fewer than all-pairs |
|---|---:|---:|---:|---:|
| 90 documents | 1.000 | 1.000 | 52 / 4,005 | **77x** |
| 270 documents | 1.000 | 1.000 | 174 / 36,315 | **209x** |

Detection is exact on this corpus (**precision and recall 1.000**), and LSH compares only a tiny
fraction of all pairs. Because the number of candidate pairs grows far more slowly than the
quadratic all-pairs count, the reduction **grows with corpus size**, from 77x at 90 documents to
209x at 270.

### Scale, throughput, and memory

> Reproduce with `python -m corpus_dedup_library` then `uv run python benchmarks/scale.py`.
> Synthetic corpora (two thirds unique, one third near-copies). Peak memory is measured with
> `tracemalloc`.

| Documents | Runtime | Throughput | Peak memory | Candidate pairs | Fewer than all-pairs | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1,050 | 3.6 s | ~288 docs/s | 8.1 MiB | 442 | 1,246x | 1.000 | 0.997 |
| 3,000 | 10.5 s | ~285 docs/s | 22.9 MiB | 1,310 | 3,434x | 1.000 | 0.988 |
| 6,000 | 21.1 s | ~284 docs/s | 45.7 MiB | 2,634 | 6,833x | 1.000 | 0.992 |
| 10,500 | 37.5 s | ~280 docs/s | 80.4 MiB | 4,900 | 11,249x | 1.000 | 0.995 |

Throughput holds roughly constant per document and memory grows linearly with corpus size, while
the candidate-pair reduction keeps widening (over 11,000x at 10,500 documents). Adversarial duplicate
shapes (exact, odd whitespace, repeated text, and near-copies with appended non-ASCII text) are
detected; a low-overlap semantic paraphrase is **not** detected, which is the expected boundary of
word-shingle MinHash (it measures lexical overlap, not meaning), not an implementation defect. These
remain synthetic corpora: they measure throughput and memory behavior, not accuracy on real web text
at pretraining scale.

## Demonstration

```text
$ python -m corpus_dedup_library report
Near-duplicate detection against ground truth:
  precision=1.000, recall=1.000, f1=1.000; 52/4005 pairs compared (77x fewer)

$ python -m corpus_dedup_library quality
Quality filter over 93 documents:
  kept 90, rejected 3
  doc 90: too_few_words, too_few_stopwords
  doc 91: too_few_stopwords, too_many_symbols
  doc 92: too_repetitive
```

## Quickstart

```bash
git clone https://github.com/adeoluo/corpus-dedup-library.git && cd corpus-dedup-library
make setup                      # install dev tooling + pre-commit hooks
make all                        # lint + type-check + test

python -m corpus_dedup_library report      # detection precision and recall
python -m corpus_dedup_library dedup        # deduplicate the built-in corpus
python -m corpus_dedup_library quality       # apply the quality filter
python -m corpus_dedup_library serve         # start the HTTP service on :8000
```

```python
from corpus_dedup_library import deduplicate, assess

result = deduplicate(["the cat sat here", "the cat sat here too", "unrelated finance text"])
print(result.keep, result.drop)
print(assess("!!! @@@ ###").reasons)  # ('too_few_stopwords', 'too_many_symbols')
```

## HTTP service

A standard-library HTTP service holds no corpus state; each request carries its own documents. The
routing logic is a pure function, tested without a socket.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | liveness |
| GET | `/ready` | readiness |
| GET | `/metrics` | per-route request, error, and latency metrics (Prometheus text) |
| POST | `/dedup` | body `{"documents": [str], "threshold": float?}`; keep and drop ids |
| POST | `/quality` | body `{"text": str}`; whether the text passes and why not |
| GET | `/report` | near-duplicate detection precision and recall on the built-in corpus |

## Design decisions

- **MinHash plus LSH over exact all-pairs** - exact pairwise Jaccard is quadratic; MinHash and LSH
  make the cost close to linear while estimating similarity accurately. See
  [ADR 0002](docs/adr/0002-minhash-lsh.md).
- **A verification step after LSH** - LSH produces candidates, not decisions; verifying each against
  a threshold controls precision. See [ADR 0003](docs/adr/0003-verify-candidates.md).

## Evaluation

The labeled corpus and all hashing are deterministic, so every number reproduces offline. Full
method and tables: [`docs/EVALUATION_REPORT.md`](docs/EVALUATION_REPORT.md).

## Responsible AI

- **Model card:** [`docs/MODEL_CARD.md`](docs/MODEL_CARD.md)
- **Data card:** [`docs/DATA_CARD.md`](docs/DATA_CARD.md)
- **Threat model:** [`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md)

## Comparison scope

The reported precision, recall, and candidate-pair reduction are measured on a small synthetic
corpus (90 to 270 documents) with injected near-duplicates, against an exhaustive all-pairs
baseline, not against an established deduplication pipeline at scale. Perfect accuracy on injected
duplicates is not evidence of the same accuracy on diverse web text, and this corpus is far below
pretraining scale. This project has **not** been benchmarked against
[datatrove](https://github.com/huggingface/datatrove) or
[text-dedup](https://github.com/ChenghaoMou/text-dedup), and it does not claim to beat them. What
the result establishes is the correctness of the MinHash and LSH mechanics and the sublinear growth
of candidate pairs. A large-scale evaluation with memory and throughput measurements is the natural
next step.

## Limitations

- Pure-Python hashing is slow per document; the win is algorithmic (far fewer comparisons), not raw
  speed. An optimized hash would lower absolute latency.
- Bands, rows, and the threshold set the operating point; the defaults suit the bundled corpus and
  may need tuning for other similarity distributions.
- The quality filters are heuristic and language-agnostic by design; a production pipeline would add
  language identification and model-based filters.

## Roadmap

- [ ] Evaluate on a real large corpus with memory and throughput measurements, compared against datatrove or text-dedup.
- [ ] Add a streaming mode that indexes documents without holding them all in memory.
- [ ] Add a learned quality classifier alongside the heuristics.
- [ ] Add exact sub-document (span) overlap detection.

## License

[MIT](LICENSE)
