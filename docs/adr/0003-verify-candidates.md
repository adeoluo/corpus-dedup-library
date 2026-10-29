# ADR-0003: Verify LSH candidates against a threshold

- **Status:** Accepted
- **Date:** 2026-01-01

## Context
Locality-sensitive hashing is tuned for recall: it shortlists pairs that are probably similar, but
some candidates fall below the intended similarity. Treating every candidate as a duplicate would
hurt precision.

## Decision
Verify each candidate pair against an explicit Jaccard threshold before declaring it a duplicate.
By default the faster signature estimate is used; an exact mode recomputes Jaccard over shingle sets
when precision matters more than speed. Confirmed pairs are unioned, and one representative per
cluster is kept.

## Consequences
- Precision is controlled by the threshold rather than left to the hashing parameters alone, which
  is why detection reaches precision and recall of 1.0 on the labeled corpus.
- The estimated and exact verification modes agree on the benchmark corpus, so the cheaper estimate
  is the default.
- A document is only removed when it is confirmed similar to a kept representative, never on a bucket
  collision alone.
