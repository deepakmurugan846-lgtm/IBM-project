#!/usr/bin/env python3
"""
Quick smoke-test for the full RAG pipeline without a real Groq key.
Ingests a tiny document, retrieves from it, and prints results.

Usage:
    python scripts/validate_rag.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


SAMPLE_TEXT = """\
WiFi troubleshooting for IoT devices.
If your smart device cannot connect to WiFi, check the following:
1. Ensure your router broadcasts a 2.4 GHz network (most IoT devices do not support 5 GHz).
2. Verify your WiFi password has no special characters.
3. Confirm the router uses WPA2-PSK security, not WPA3-only.
4. Factory reset the device and retry pairing.

Firmware update procedure:
1. Open the companion app and go to Settings > Firmware Update.
2. Keep the device plugged in during the entire update.
3. Do not power off the device while the LED is flashing.
"""

QUERIES = [
    "WiFi not connecting IoT device",
    "how to update firmware safely",
    "factory reset device",
]


def main() -> None:
    import os

    # Provide a dummy API key so config.validate() passes
    os.environ.setdefault("GROQ_API_KEY", "dummy-key-for-rag-validation")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        doc_path = tmpdir_path / "sample.txt"
        doc_path.write_text(SAMPLE_TEXT, encoding="utf-8")

        vs_path = tmpdir_path / "vs"

        # Patch paths
        import backend.core.ingestion as ing
        import backend.core.retrieval as ret
        ing.VECTORSTORE_DIR = vs_path
        ret.VECTORSTORE_DIR = vs_path

        print("📥  Ingesting sample document…")
        store = ing.ingest_documents(source=doc_path, reset=True)
        count = store._collection.count()
        print(f"    → {count} chunks indexed\n")

        from backend.core.retrieval import RetrievalEngine, build_context_string
        engine = RetrievalEngine(vectorstore=store)

        all_passed = True
        for query in QUERIES:
            chunks = engine.retrieve(query, top_k=3)
            if chunks:
                print(f"✅  Query: '{query}'")
                print(f"    Top chunk (score={chunks[0].score:.3f}):")
                print(f"    {chunks[0].content[:120]}…\n")
            else:
                print(f"❌  No results for query: '{query}'\n")
                all_passed = False

        if all_passed:
            print("🎉  RAG validation passed — pipeline is working correctly.")
        else:
            print("⚠️   Some queries returned no results. Review your documents or chunk settings.")
            sys.exit(1)


if __name__ == "__main__":
    main()
