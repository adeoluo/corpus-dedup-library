"""Heuristic quality filtering, in the spirit of large-corpus cleaning pipelines.

Low-quality web text has recognizable signatures: too short or too long, very long
or very short mean word length, few stop words (so not natural prose), a high ratio
of symbols to words, or heavy word repetition. Each filter is a simple, inspectable
rule; a document passes only if it clears all of them. The thresholds are
configurable and default to conservative values.
"""

from __future__ import annotations

from dataclasses import dataclass

_STOPWORDS = frozenset(
    "the a an and or but of to in on for with at by from as is are was were be this that".split()
)


@dataclass(frozen=True)
class QualityConfig:
    """Thresholds for the quality filters."""

    min_words: int = 5
    max_words: int = 100000
    min_mean_word_length: float = 2.0
    max_mean_word_length: float = 12.0
    min_stopword_ratio: float = 0.05
    max_symbol_ratio: float = 0.2
    max_duplicate_word_fraction: float = 0.5


@dataclass(frozen=True)
class QualityReport:
    """Whether a document passed and, if not, which rules it failed."""

    passed: bool
    reasons: tuple[str, ...]


def assess(text: str, config: QualityConfig | None = None) -> QualityReport:
    """Return a quality assessment for ``text`` against ``config``."""

    config = config or QualityConfig()
    words = text.split()
    reasons: list[str] = []

    if len(words) < config.min_words:
        reasons.append("too_few_words")
    if len(words) > config.max_words:
        reasons.append("too_many_words")

    if words:
        mean_len = sum(len(w) for w in words) / len(words)
        if mean_len < config.min_mean_word_length:
            reasons.append("mean_word_length_too_low")
        if mean_len > config.max_mean_word_length:
            reasons.append("mean_word_length_too_high")

        stopwords = sum(1 for w in words if w.lower() in _STOPWORDS)
        if stopwords / len(words) < config.min_stopword_ratio:
            reasons.append("too_few_stopwords")

        unique_ratio = len(set(words)) / len(words)
        if 1.0 - unique_ratio > config.max_duplicate_word_fraction:
            reasons.append("too_repetitive")

    if text:
        symbols = sum(1 for ch in text if not ch.isalnum() and not ch.isspace())
        if symbols / len(text) > config.max_symbol_ratio:
            reasons.append("too_many_symbols")
    else:
        reasons.append("empty")

    return QualityReport(passed=not reasons, reasons=tuple(reasons))


def filter_corpus(
    documents: list[str], config: QualityConfig | None = None
) -> tuple[list[int], dict[int, tuple[str, ...]]]:
    """Return the ids that pass and a map from failing id to its reasons."""

    keep: list[int] = []
    rejected: dict[int, tuple[str, ...]] = {}
    for doc_id, text in enumerate(documents):
        report = assess(text, config)
        if report.passed:
            keep.append(doc_id)
        else:
            rejected[doc_id] = report.reasons
    return keep, rejected
