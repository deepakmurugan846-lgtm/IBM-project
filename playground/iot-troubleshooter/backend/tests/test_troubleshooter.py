"""
Test suite for the IoT Troubleshooter.

Covers:
  - Ingestion pipeline (chunking, vector store creation)
  - Retrieval engine (query → chunks)
  - LLM layer (mocked Groq calls)
  - FastAPI endpoints (health, chat, ingest, docs-status)

Run with:
    pytest backend/tests/ -v
"""

from __future__ import annotations

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ── Make sure the package root is on the path ──────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Provide required env vars for every test."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("GROQ_MODEL", "llama3-70b-8192")


@pytest.fixture()
def sample_text_file(tmp_path: Path) -> Path:
    doc = tmp_path / "sample.txt"
    doc.write_text(
        "WiFi troubleshooting: if device does not connect, check that your "
        "router uses 2.4 GHz band. Many IoT devices do not support 5 GHz. "
        "Ensure WPA2-PSK security and a simple SSID without special characters. "
        "Factory reset the device if credentials are incorrect.\n\n"
        "Firmware updates: always keep the device powered during an OTA update. "
        "A power cut during flashing can corrupt firmware and brick the device.",
        encoding="utf-8",
    )
    return doc


# ══════════════════════════════════════════════════════════════════════════
# 1.  Ingestion pipeline
# ══════════════════════════════════════════════════════════════════════════

class TestIngestion:
    def test_ingest_single_file_creates_chunks(self, tmp_path, sample_text_file, monkeypatch):
        """Ingesting a text file should produce at least one chunk."""
        vs_dir = tmp_path / "vs"
        monkeypatch.setattr("backend.core.ingestion.VECTORSTORE_DIR", vs_dir)

        from backend.core.ingestion import ingest_documents
        store = ingest_documents(source=sample_text_file, reset=True)
        count = store._collection.count()
        assert count >= 1, f"Expected ≥1 chunk, got {count}"

    def test_ingest_missing_directory_returns_empty_store(self, tmp_path, monkeypatch):
        """Ingesting a non-existent path should return a store with 0 chunks."""
        vs_dir = tmp_path / "vs2"
        monkeypatch.setattr("backend.core.ingestion.VECTORSTORE_DIR", vs_dir)

        from backend.core.ingestion import ingest_documents
        store = ingest_documents(source=tmp_path / "nonexistent", reset=True)
        count = store._collection.count()
        assert count == 0

    def test_stable_doc_id_is_deterministic(self):
        from backend.core.ingestion import _stable_doc_id
        id1 = _stable_doc_id("doc.txt", 3)
        id2 = _stable_doc_id("doc.txt", 3)
        assert id1 == id2

    def test_stable_doc_id_differs_by_index(self):
        from backend.core.ingestion import _stable_doc_id
        assert _stable_doc_id("doc.txt", 0) != _stable_doc_id("doc.txt", 1)


# ══════════════════════════════════════════════════════════════════════════
# 2.  Retrieval engine
# ══════════════════════════════════════════════════════════════════════════

class TestRetrieval:
    def test_retrieve_returns_chunks_when_store_populated(self, tmp_path, sample_text_file, monkeypatch):
        """After ingestion, a relevant query should return ≥1 chunk."""
        vs_dir = tmp_path / "vs3"
        monkeypatch.setattr("backend.core.ingestion.VECTORSTORE_DIR", vs_dir)
        monkeypatch.setattr("backend.core.retrieval.VECTORSTORE_DIR", vs_dir)

        from backend.core.ingestion import ingest_documents
        store = ingest_documents(source=sample_text_file, reset=True)

        from backend.core.retrieval import RetrievalEngine
        engine = RetrievalEngine(vectorstore=store)
        chunks = engine.retrieve("WiFi 2.4 GHz IoT device")
        assert len(chunks) >= 1
        assert all(hasattr(c, "content") for c in chunks)
        assert all(hasattr(c, "score") for c in chunks)

    def test_retrieve_graceful_without_store(self):
        """RetrievalEngine with no store should return [] without raising."""
        from backend.core.retrieval import RetrievalEngine

        engine = RetrievalEngine(vectorstore=None)
        engine._initialised = True  # skip lazy load
        engine._store = None
        chunks = engine.retrieve("any query")
        assert chunks == []

    def test_chunk_source_trimmed_to_filename(self, tmp_path, sample_text_file, monkeypatch):
        """Source metadata should be trimmed to just the filename."""
        vs_dir = tmp_path / "vs4"
        monkeypatch.setattr("backend.core.ingestion.VECTORSTORE_DIR", vs_dir)

        from backend.core.ingestion import ingest_documents
        store = ingest_documents(source=sample_text_file, reset=True)

        from backend.core.retrieval import RetrievalEngine
        engine = RetrievalEngine(vectorstore=store)
        chunks = engine.retrieve("firmware update")
        for chunk in chunks:
            assert "/" not in chunk.source, f"Source not trimmed: {chunk.source}"
            assert "\\" not in chunk.source

    def test_build_context_string_empty(self):
        from backend.core.retrieval import build_context_string
        assert build_context_string([]) == ""

    def test_build_context_string_formats_header(self):
        from backend.core.retrieval import RetrievedChunk, build_context_string
        chunk = RetrievedChunk(content="test content", source="guide.txt", score=0.85)
        result = build_context_string([chunk])
        assert "guide.txt" in result
        assert "0.85" in result
        assert "test content" in result


# ══════════════════════════════════════════════════════════════════════════
# 3.  LLM layer (Groq mocked)
# ══════════════════════════════════════════════════════════════════════════

class TestLLMLayer:
    def _make_groq_mock(self, answer: str = "Check your WiFi band."):
        mock_client = MagicMock()
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 100
        mock_usage.completion_tokens = 50
        mock_usage.total_tokens = 150
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = answer
        mock_resp.usage = mock_usage
        mock_client.chat.completions.create.return_value = mock_resp
        return mock_client

    def test_chat_returns_structured_response(self):
        from backend.core.llm import GroqLLM, TroubleshootingEngine
        from backend.core.retrieval import RetrievalEngine

        mock_groq_client = self._make_groq_mock("Step 1: Check your 2.4 GHz band.")

        with patch("backend.core.llm.Groq", return_value=mock_groq_client):
            llm = GroqLLM()

        retriever = RetrievalEngine()
        retriever._initialised = True
        retriever._store = None  # no RAG store

        engine = TroubleshootingEngine(retrieval_engine=retriever, llm=llm)
        response = engine.chat("My smart plug won't connect to WiFi")

        assert "2.4 GHz" in response.answer
        assert isinstance(response.sources, list)
        assert isinstance(response.retrieval_used, bool)

    def test_conversation_history_grows(self):
        from backend.core.llm import ConversationManager
        mgr = ConversationManager()
        mgr.add("user", "Hello")
        mgr.add("assistant", "Hi there")
        mgr.add("user", "My device is offline")
        assert mgr.turn_count == 1  # 2 user + 1 partial = floor(3/2) = 1

    def test_conversation_history_capped(self):
        from backend.core.llm import ConversationManager
        from backend.core.config import MAX_HISTORY_TURNS
        mgr = ConversationManager()
        for i in range(MAX_HISTORY_TURNS + 5):
            mgr.add("user", f"msg {i}")
            mgr.add("assistant", f"reply {i}")
        msgs = mgr.to_groq_messages("sys prompt")
        # system + capped messages
        assert len(msgs) <= (MAX_HISTORY_TURNS * 2) + 1

    def test_reset_clears_history(self):
        from backend.core.llm import TroubleshootingEngine
        from backend.core.retrieval import RetrievalEngine

        mock_groq_client = self._make_groq_mock()
        with patch("backend.core.llm.Groq", return_value=mock_groq_client):
            from backend.core.llm import GroqLLM
            llm = GroqLLM()

        retriever = RetrievalEngine()
        retriever._initialised = True
        retriever._store = None

        engine = TroubleshootingEngine(retrieval_engine=retriever, llm=llm)
        engine.chat("test message")
        assert engine.turn_count >= 1
        engine.reset()
        assert engine.turn_count == 0


# ══════════════════════════════════════════════════════════════════════════
# 4.  FastAPI endpoints
# ══════════════════════════════════════════════════════════════════════════

class TestAPI:
    @pytest.fixture()
    def client(self):
        from fastapi.testclient import TestClient
        mock_groq = MagicMock()
        mock_usage = MagicMock(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Check your WiFi settings."
        mock_resp.usage = mock_usage
        mock_groq.chat.completions.create.return_value = mock_resp

        with patch("backend.core.llm.Groq", return_value=mock_groq):
            from backend.api.app import app
            yield TestClient(app)

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_chat_new_session(self, client):
        resp = client.post("/chat", json={"message": "My device keeps dropping WiFi."})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_chat_continue_session(self, client):
        resp1 = client.post("/chat", json={"message": "Device offline."})
        session_id = resp1.json()["session_id"]

        resp2 = client.post(
            "/chat",
            json={"message": "Can you give more detail?", "session_id": session_id},
        )
        assert resp2.status_code == 200
        assert resp2.json()["session_id"] == session_id

    def test_reset_session(self, client):
        resp = client.post("/chat", json={"message": "Hello"})
        sid = resp.json()["session_id"]
        reset = client.post("/chat/reset", json={"session_id": sid})
        assert reset.status_code == 200
        assert reset.json()["status"] == "reset"

    def test_docs_status_returns_count(self, client):
        resp = client.get("/docs-status")
        assert resp.status_code == 200
        assert "collection_count" in resp.json()

    def test_chat_empty_message_rejected(self, client):
        resp = client.post("/chat", json={"message": ""})
        assert resp.status_code == 422  # validation error
