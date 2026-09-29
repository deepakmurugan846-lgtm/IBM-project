#!/usr/bin/env python3
"""
Ingestion script — run once to build the vector store before starting the app.

Usage:
    python scripts/ingest.py                   # ingest docs/ directory
    python scripts/ingest.py --reset           # rebuild from scratch
    python scripts/ingest.py --source path/to/file.pdf
    python scripts/ingest.py --source path/to/docs/ --reset
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure the project root is on the path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest IoT documents into the vector store")
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="File or directory to ingest (defaults to docs/sample_docs/)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Wipe the existing vector store before ingesting",
    )
    args = parser.parse_args()

    from backend.core.ingestion import ingest_documents

    logger.info("Starting ingestion%s…", " (reset)" if args.reset else "")
    store = ingest_documents(source=args.source, reset=args.reset)
    count = store._collection.count()
    logger.info("✅  Ingestion complete — %d chunks indexed", count)


if __name__ == "__main__":
    main()
