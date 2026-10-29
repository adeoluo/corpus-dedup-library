# Model / System Card - Corpus Dedup Library

## Overview
- **What it is:** a from-scratch near-deduplication and quality-filtering library using MinHash and
  LSH, in pure Python with no third-party dependencies.
- **Base model:** none. It is an algorithmic data-cleaning pipeline.
- **Version and date:** 0.1.0, 2026.

## Intended use
- **Primary use case:** removing near-duplicate documents and filtering degenerate text from a
  corpus, and a readable reference implementation of MinHash and LSH.
- **Primary users:** engineers building training-data pipelines.

## Out-of-scope / prohibited use
- Not an optimized production deduplicator; pure-Python hashing is slow per document.
- The quality filters are heuristic and language-agnostic; they do not replace model-based filters.

## Performance
- Precision and recall of 1.000 on a labeled corpus, comparing 77x to 209x fewer pairs than all-pairs.
- Full method and tables: [`EVALUATION_REPORT.md`](EVALUATION_REPORT.md).

## Limitations and failure modes
- Bands, rows, and threshold set the operating point and may need tuning for other distributions.
- Heuristic quality rules can reject unusual but legitimate text; thresholds are configurable.

## Ethical considerations
- No personal data, no network access. The corpus is synthetic and generated in-process. Removing
  duplicates changes a dataset's composition; the kept representative is the lowest id in a cluster.
