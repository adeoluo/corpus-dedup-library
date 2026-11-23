"""The detection table in the README is what the library measures today."""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus_dedup_library.data import make_corpus
from corpus_dedup_library.evaluation import evaluate_detection

README = (Path(__file__).resolve().parent.parent / "README.md").read_text()


@pytest.mark.parametrize(("unique", "duplicates"), [(50, 40), (150, 120)])
def test_readme_detection_row_matches_a_fresh_run(unique: int, duplicates: int) -> None:
    corpus = make_corpus(unique=unique, duplicates=duplicates, seed=0)
    line = evaluate_detection(corpus).format()
    precision = line.split("precision=")[1].split(",")[0]
    recall = line.split("recall=")[1].split(",")[0]
    compared, total = line.split("; ")[1].split(" pairs")[0].split("/")
    factor = line.split("(")[1].split("x")[0]
    row = (
        f"| {len(corpus.documents)} documents | {precision} | {recall} | "
        f"{int(compared):,} / {int(total):,} | **{factor}x** |"
    )
    assert row in README, (row, line)
