"""Locality-sensitive hashing over MinHash signatures.

Comparing every pair of documents is quadratic. LSH avoids that by splitting each
signature into ``bands`` bands of ``rows`` rows and hashing each band. Two
documents become candidate near-duplicates if any band hashes to the same bucket.
Tuning bands and rows sets the similarity threshold above which pairs are very
likely to collide, so the shortlist of candidate pairs is small and high-recall.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from corpus_dedup_library.minhash import MinHasher

_MASK64 = (1 << 64) - 1


def _hash_band(band: tuple[int, ...]) -> int:
    acc = 1469598103934665603
    for value in band:
        acc = ((acc ^ (value & _MASK64)) * 1099511628211) & _MASK64
    return acc


@dataclass
class LSHIndex:
    """Buckets documents by signature bands to shortlist near-duplicate pairs."""

    bands: int = 16
    rows: int = 4

    def __post_init__(self) -> None:
        self._buckets: list[dict[int, list[int]]] = [defaultdict(list) for _ in range(self.bands)]
        self._signatures: dict[int, list[int]] = {}

    @property
    def num_perm(self) -> int:
        return self.bands * self.rows

    def add(self, doc_id: int, signature: list[int]) -> None:
        """Index ``signature`` for ``doc_id`` across all bands."""

        if len(signature) != self.num_perm:
            raise ValueError(f"signature length {len(signature)} != bands*rows {self.num_perm}")
        self._signatures[doc_id] = signature
        for band_index in range(self.bands):
            start = band_index * self.rows
            band = tuple(signature[start : start + self.rows])
            self._buckets[band_index][_hash_band(band)].append(doc_id)

    def candidate_pairs(self) -> set[tuple[int, int]]:
        """Return the set of candidate near-duplicate id pairs (unordered)."""

        pairs: set[tuple[int, int]] = set()
        for buckets in self._buckets:
            for members in buckets.values():
                if len(members) < 2:
                    continue
                for i in range(len(members)):
                    for j in range(i + 1, len(members)):
                        a, b = members[i], members[j]
                        pairs.add((a, b) if a < b else (b, a))
        return pairs


def build_index(
    documents: list[str], *, bands: int = 16, rows: int = 4, k: int = 3, seed: int = 0
) -> tuple[LSHIndex, MinHasher]:
    """Build an LSH index over ``documents`` and return it with its hasher."""

    hasher = MinHasher(num_perm=bands * rows, k=k, seed=seed)
    index = LSHIndex(bands=bands, rows=rows)
    for doc_id, text in enumerate(documents):
        index.add(doc_id, hasher.signature(text))
    return index, hasher
