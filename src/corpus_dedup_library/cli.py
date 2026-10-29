"""Command line interface for the corpus deduplication library."""

from __future__ import annotations

import argparse

from corpus_dedup_library.data import make_corpus
from corpus_dedup_library.dedup import deduplicate
from corpus_dedup_library.evaluation import evaluate_detection
from corpus_dedup_library.quality import assess, filter_corpus


def _cmd_dedup(args: argparse.Namespace) -> None:
    corpus = make_corpus(unique=args.unique, duplicates=args.duplicates, seed=args.seed)
    result = deduplicate(corpus.documents, threshold=args.threshold)
    print(f"Corpus of {result.total} documents ({args.duplicates} injected near-duplicates).")
    print(f"  kept {len(result.keep)}, dropped {len(result.drop)}")
    print(f"  candidate pairs compared: {result.candidate_pairs}")


def _cmd_report(args: argparse.Namespace) -> None:
    corpus = make_corpus(unique=args.unique, duplicates=args.duplicates, seed=args.seed)
    detection = evaluate_detection(corpus, threshold=args.threshold)
    print("Near-duplicate detection against ground truth:")
    print(f"  {detection.format()}")


def _cmd_quality(args: argparse.Namespace) -> None:
    corpus = make_corpus(unique=args.unique, duplicates=args.duplicates, seed=args.seed)
    noise = ["hi", "!!! @@@ ### $$$", "spam spam spam spam spam spam"]
    documents = corpus.documents + noise
    keep, rejected = filter_corpus(documents)
    print(f"Quality filter over {len(documents)} documents:")
    print(f"  kept {len(keep)}, rejected {len(rejected)}")
    for doc_id, reasons in list(rejected.items())[-3:]:
        print(f"  doc {doc_id}: {', '.join(reasons)}")
    sample = assess(documents[0])
    print(f"  first document passes: {sample.passed}")


def _cmd_serve(args: argparse.Namespace) -> None:
    from corpus_dedup_library.service import serve

    serve(host=args.host, port=args.port)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--unique", type=int, default=50)
    parser.add_argument("--duplicates", type=int, default=40)
    parser.add_argument("--threshold", type=float, default=0.6)
    parser.add_argument("--seed", type=int, default=0)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="corpus-dedup-library", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text, handler in (
        ("dedup", "deduplicate the built-in corpus", _cmd_dedup),
        ("report", "detection precision and recall against ground truth", _cmd_report),
        ("quality", "apply the quality filter to the corpus plus noise", _cmd_quality),
    ):
        p = sub.add_parser(name, help=help_text)
        _add_common(p)
        p.set_defaults(func=handler)

    serve = sub.add_parser("serve", help="start the HTTP service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
