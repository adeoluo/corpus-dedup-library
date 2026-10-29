"""A deterministic synthetic corpus with injected near-duplicates.

The corpus is built from a set of base sentences. Some documents are exact or
near copies of others (a word changed, a clause appended), which gives a known
ground truth for near-duplicate detection. Unique documents are distinct base
sentences. Generation is seeded and offline.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

_WORDS = (
    "report revenue growth region quarter research method training model efficient "
    "council budget transit downtown diet exercise health outcome software release "
    "performance settings investor bank interest rate museum exhibit artist farmer "
    "irrigation water season market product customer revenue forecast strategy team "
    "project deadline analysis dataset pipeline service latency throughput memory cache "
    "network protocol security policy incident response audit compliance review summary"
).split()

_EDITS: tuple[Callable[[str], str], ...] = (
    lambda s: s,  # exact duplicate
    lambda s: s + " please read the attached summary for details",
    lambda s: s.replace(s.split()[0], "updated", 1),
    lambda s: "in summary " + s,
)


@dataclass(frozen=True)
class Corpus:
    """A labeled corpus: documents plus which are near-duplicates of which."""

    documents: list[str]
    duplicate_of: dict[int, int]  # doc id -> the base document id it duplicates

    @property
    def true_duplicate_pairs(self) -> set[tuple[int, int]]:
        pairs: set[tuple[int, int]] = set()
        for dup, base in self.duplicate_of.items():
            pairs.add((base, dup) if base < dup else (dup, base))
        return pairs


def make_corpus(unique: int = 40, duplicates: int = 30, *, seed: int = 0) -> Corpus:
    """Return a corpus of ``unique`` distinct documents plus ``duplicates`` near copies."""

    rng = random.Random(seed)
    documents: list[str] = []
    base_ids: list[int] = []
    for _ in range(unique):
        length = rng.randint(14, 20)
        words = [rng.choice(_WORDS) for _ in range(length)]
        documents.append(" ".join(words))
        base_ids.append(len(documents) - 1)

    duplicate_of: dict[int, int] = {}
    for _ in range(duplicates):
        source = rng.choice(base_ids)
        edit = rng.choice(_EDITS)
        documents.append(edit(documents[source]))
        duplicate_of[len(documents) - 1] = source

    return Corpus(documents=documents, duplicate_of=duplicate_of)
