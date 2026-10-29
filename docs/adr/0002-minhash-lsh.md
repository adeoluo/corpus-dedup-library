# ADR-0002: MinHash and LSH for scalable near-deduplication

- **Status:** Accepted
- **Date:** 2026-01-01

## Context
Removing near-duplicate documents from a corpus requires a similarity measure and a way to apply it
without comparing every pair. Exact Jaccard over shingle sets is accurate but comparing all pairs is
quadratic, which does not scale.

## Decision
Estimate Jaccard similarity with MinHash: each of several hash permutations maps a document's
shingle set to its minimum value, and the fraction of permutations where two signatures agree is an
unbiased estimate of their Jaccard similarity. Shortlist candidate pairs with locality-sensitive
hashing: split each signature into bands, hash each band, and treat documents that share any band
bucket as candidates. The number of bands and rows sets the similarity above which pairs are very
likely to collide.

## Consequences
- The comparison cost is close to linear in practice, because only documents that collide in some
  band are compared, not all pairs.
- Accuracy is tunable: more permutations tighten the estimate, and bands and rows set the threshold.
- The method finds near-copies that differ by edits, which exact-hash deduplication misses.
