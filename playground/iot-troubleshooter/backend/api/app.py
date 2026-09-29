"""
FastAPI backend — IoT Troubleshooter API

Endpoints
---------
GET  /health            — liveness check
POST /chat              — send a message, receive a diagnosis/guidance reply
POST /chat/reset        — clear the current session's conversation history
POST /ingest            — trigger document ingestion (optionally a single file)
GET  /docs-status       — report how many chunks are indexed
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.core.config import validate
from backend.core.ingestion import ingest_documents
from backend.core.llm import TroubleshootingEngine
from backend.core.retrieval import get_retrieval_engine

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── App setup ──────────────────────────────────────────────────────────────
validate()

app = FastAPI(
    title="IoT Troubleshooter API",
    description="RAG-powered IoT device troubleshooting chatbot backed by Groq AI.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session store (in-memory; replace with Redis for multi-worker prod) ────
_sessions: Dict[str, TroubleshootingEngine] = {}


def _get_or_create_engine(session_id: str) -> TroubleshootingEngine:
    if session_id not in _sessions:
        _sessions[session_id] = TroubleshootingEngine()
        logger.info("Created new session: %s", session_id)
    return _sessions[session_id]


# ── Request / Response models ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096,
                         description="User's message or problem description")
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for multi-turn conversation. "
                    "Omit to start a new session.",
    )


class ChatResponseModel(BaseModel):
    session_id: str
    answer: str
    sources: list[str]
    retrieval_used: bool
    model: str
    usage: dict
    turn: int


class ResetRequest(BaseModel):
    session_id: str


class IngestRequest(BaseModel):
    reset: bool = Field(
        default=False,
        description="Wipe existing vector store before ingesting",
    )


class DocsStatusResponse(BaseModel):
    collection_count: int
    vectorstore_path: str


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Utility"])
def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponseModel, tags=["Chat"])
def chat(request: ChatRequest) -> ChatResponseModel:
    """
    Send a message and receive troubleshooting guidance.

    If no `session_id` is provided a new one is created and returned —
    include it in subsequent requests to continue the conversation.
    """
    session_id = request.session_id or str(uuid.uuid4())
    engine = _get_or_create_engine(session_id)

    try:
        result = engine.chat(request.message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat error in session %s", session_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponseModel(
        session_id=session_id,
        answer=result.answer,
        sources=result.sources,
        retrieval_used=result.retrieval_used,
        model=result.model,
        usage=result.usage,
        turn=engine.turn_count,
    )


@app.post("/chat/reset", tags=["Chat"])
def reset_chat(request: ResetRequest) -> dict:
    """Clear the conversation history for a session."""
    engine = _sessions.get(request.session_id)
    if engine:
        engine.reset()
    return {"status": "reset", "session_id": request.session_id}


@app.post("/ingest", tags=["Knowledge Base"])
def ingest(request: IngestRequest) -> dict:
    """
    Re-ingest all documents from the docs/ directory.
    Pass reset=true to rebuild the vector store from scratch.
    """
    try:
        store = ingest_documents(reset=request.reset)
        count = store._collection.count()
        # Invalidate the retrieval engine singleton so it picks up new docs
        import backend.core.retrieval as _retrieval_module
        _retrieval_module._engine = None
        return {"status": "ok", "chunks_indexed": count}
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/ingest/upload", tags=["Knowledge Base"])
async def ingest_upload(file: UploadFile = File(...)) -> dict:
    """
    Upload a single document file (PDF, TXT, MD, HTML) and ingest it.
    """
    from backend.core.config import DOCS_DIR
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    dest = DOCS_DIR / (file.filename or "uploaded_doc.txt")
    content = await file.read()
    dest.write_bytes(content)
    logger.info("Uploaded file saved to %s (%d bytes)", dest, len(content))

    try:
        store = ingest_documents(source=dest)
        count = store._collection.count()
        import backend.core.retrieval as _retrieval_module
        _retrieval_module._engine = None
        return {"status": "ok", "file": dest.name, "chunks_indexed": count}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/docs-status", response_model=DocsStatusResponse, tags=["Knowledge Base"])
def docs_status() -> DocsStatusResponse:
    """Return the number of chunks currently indexed."""
    from backend.core.config import VECTORSTORE_DIR
    try:
        store = get_retrieval_engine()._store
        if store is None:
            get_retrieval_engine()._ensure_loaded()
            store = get_retrieval_engine()._store
        count = store._collection.count() if store else 0
    except Exception:  # noqa: BLE001
        count = 0
    return DocsStatusResponse(
        collection_count=count,
        vectorstore_path=str(VECTORSTORE_DIR),
    )
