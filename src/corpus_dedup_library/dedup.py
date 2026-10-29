"""The near-deduplication pipeline: candidates, verification, and clustering.

LSH produces a shortlist of candidate pairs. Each candidate is verified against a
Jaccard threshold (estimated from the signatures, or exact when requested), the
surviving pairs are grouped into connected components with a union-find structure,
and one representative per component is kept. The result is a set of documents to
keep and a set of near-duplicates to drop.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from corpus_dedup_library.lsh import build_index
from corpus_dedup_library.minhash import MinHasher, estimated_jaccard, exact_jaccard


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, x: int) -> int:
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


@dataclass(frozen=True)
class DedupResult:
    """The outcome of near-deduplication over a corpus."""

    keep: list[int]
    drop: list[int]
    duplicate_pairs: list[tuple[int, int]]
    candidate_pairs: int
    clusters: list[list[int]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.keep) + len(self.drop)


def deduplicate(
    documents: list[str],
    *,
    threshold: float = 0.6,
    bands: int = 16,
    rows: int = 4,
    k: int = 2,
    seed: int = 0,
    exact: bool = False,
) -> DedupResult:
    """Remove near-duplicates above ``threshold`` Jaccard similarity.

    With ``exact`` set, candidate pairs are verified by exact Jaccard over shingle
    sets; otherwise the faster signature estimate is used. The lowest document id
    in each duplicate cluster is kept.
    """

    index, hasher = build_index(documents, bands=bands, rows=rows, k=k, seed=seed)
    signatures = [hasher.signature(text) for text in documents]
    candidates = index.candidate_pairs()
    union = _UnionFind(len(documents))
    confirmed: list[tuple[int, int]] = []
    for a, b in candidates:
        similarity = (
            exact_jaccard(documents[a], documents[b], k)
            if exact
            else estimated_jaccard(signatures[a], signatures[b])
        )
        if similarity >= threshold:
            union.union(a, b)
            confirmed.append((a, b))

    clusters_map: dict[int, list[int]] = {}
    for doc_id in range(len(documents)):
        clusters_map.setdefault(union.find(doc_id), []).append(doc_id)
    keep: list[int] = []
    drop: list[int] = []
    clusters: list[list[int]] = []
    for members in clusters_map.values():
        members.sort()
        keep.append(members[0])
        drop.extend(members[1:])
        if len(members) > 1:
            clusters.append(members)
    keep.sort()
    drop.sort()
    return DedupResult(
        keep=keep,
        drop=drop,
        duplicate_pairs=sorted(confirmed),
        candidate_pairs=len(candidates),
        clusters=clusters,
    )


def all_pairs_count(n: int) -> int:
    """Return the number of unordered pairs in a corpus of ``n`` documents."""

    return n * (n - 1) // 2


def minhasher(bands: int = 16, rows: int = 4, k: int = 3, seed: int = 0) -> MinHasher:
    """Return a hasher matching a band and row configuration."""

    return MinHasher(num_perm=bands * rows, k=k, seed=seed)
