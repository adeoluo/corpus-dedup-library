"""MinHash signatures over shingled text.

The Jaccard similarity of two documents' shingle sets is expensive to compute
exactly for every pair. MinHash estimates it cheaply: each of ``num_perm`` hash
functions maps the shingle set to its minimum hash value, and the fraction of hash
functions where two signatures agree is an unbiased estimate of their Jaccard
similarity. Hashing uses a fixed 64-bit mix and a family of ``(a*h + b) mod p``
permutations, so everything is deterministic and dependency-free.
"""

from __future__ import annotations

from dataclasses import dataclass

_MASK64 = (1 << 64) - 1
_PRIME = (1 << 61) - 1  # a Mersenne prime for the permutation family


def _mix64(value: int) -> int:
    """A deterministic 64-bit integer hash (splitmix64-style)."""

    value = (value + 0x9E3779B97F4A7C15) & _MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
    return value ^ (value >> 31)


def hash_token(token: str) -> int:
    """Hash a string to a 64-bit integer deterministically."""

    acc = 0
    for ch in token:
        acc = (acc * 1099511628211 + ord(ch)) & _MASK64
    return _mix64(acc)


def shingles(text: str, k: int = 3) -> set[int]:
    """Return the set of hashed word ``k``-shingles of ``text``.

    Word-level shingles capture local order, so two documents that share long runs
    of words have overlapping shingle sets even if edited slightly.
    """

    words = text.lower().split()
    if len(words) < k:
        return {hash_token(" ".join(words))} if words else set()
    return {hash_token(" ".join(words[i : i + k])) for i in range(len(words) - k + 1)}


@dataclass
class MinHasher:
    """Builds MinHash signatures with a fixed family of hash permutations."""

    num_perm: int = 64
    k: int = 3
    seed: int = 0

    def __post_init__(self) -> None:
        rng_state = _mix64(self.seed + 1)
        self._a: list[int] = []
        self._b: list[int] = []
        for _ in range(self.num_perm):
            rng_state = _mix64(rng_state)
            self._a.append(1 + rng_state % (_PRIME - 1))
            rng_state = _mix64(rng_state)
            self._b.append(rng_state % _PRIME)

    def signature(self, text: str) -> list[int]:
        """Return the MinHash signature (one minimum per permutation) for ``text``."""

        shingle_hashes = shingles(text, self.k)
        if not shingle_hashes:
            return [0] * self.num_perm
        signature = []
        for a, b in zip(self._a, self._b, strict=True):
            best = min((a * h + b) % _PRIME for h in shingle_hashes)
            signature.append(best)
        return signature


def estimated_jaccard(sig_a: list[int], sig_b: list[int]) -> float:
    """Estimate Jaccard similarity as the fraction of agreeing signature positions."""

    if not sig_a:
        return 0.0
    agree = sum(1 for x, y in zip(sig_a, sig_b, strict=True) if x == y)
    return agree / len(sig_a)


def exact_jaccard(text_a: str, text_b: str, k: int = 3) -> float:
    """Return the exact Jaccard similarity of two documents' shingle sets."""

    a = shingles(text_a, k)
    b = shingles(text_b, k)
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)
