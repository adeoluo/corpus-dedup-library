"""Write a synthetic JSONL corpus with planted near-duplicates to stdout.

Usage: python benchmarks/make_jsonl.py [documents]   (used by docs/demo/dedup.tape)
"""

from __future__ import annotations

import json
import sys

from compare_backends import corpus


def main() -> None:
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 20_000
    for doc_id, text in enumerate(corpus(count)):
        print(json.dumps({"id": doc_id, "text": text}))


if __name__ == "__main__":
    main()
