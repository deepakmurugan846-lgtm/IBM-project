"""
Retrieval engine — wraps the Chroma vector store with a ranked,
source-cited retriever.

Each call to `retrieve()` returns the top-K most relevant chunks
with their source filename and relevance score, ready to be injected
into the prompt as grounding evidence.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from langchain_community.vectorstores import Chroma

from backend.core.config import RETRIEVAL_TOP_K
from backend.core.ingestion import load_vectorstore

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A single retrieved document chunk with metadata."""
    content: str
    source: str
    score: float
    page: Optional[int] = None
    extra_meta: dict = field(default_factory=dict)

    def as_context_block(self) -> str:
        """Format for injection into the LLM prompt."""
        header = f"[Source: {self.source}"
        if self.page is not None:
            header += f", p.{self.page}"
        header += f", relevance: {self.score:.2f}]"
        return f"{header}\n{self.content}"


class RetrievalEngine:
    """
    Wraps a Chroma vector store and exposes a `retrieve()` method.

    Usage
    -----
    engine = RetrievalEngine()
    chunks = engine.retrieve("WiFi not connecting after firmware update")
    """

    def __init__(self, vectorstore: Optional[Chroma] = None) -> None:
        self._store: Optional[Chroma] = vectorstore
        self._initialised = vectorstore is not None

    def _ensure_loaded(self) -> None:
        if not self._initialised:
            try:
                self._store = load_vectorstore()
                self._initialised = True
            except FileNotFoundError as exc:
                logger.warning("Vector store not available: %s", exc)
                self._store = None

    def retrieve(
        self,
        query: str,
        top_k: int = RETRIEVAL_TOP_K,
    ) -> List[RetrievedChunk]:
        """
        Retrieve the most relevant document chunks for a query.

        Returns an empty list (gracefully) when the store is unavailable
        so the LLM can still respond without RAG context.
        """
        self._ensure_loaded()
        if self._store is None:
            logger.info("No vector store available — skipping retrieval")
            return []

        try:
            results = self._store.similarity_search_with_relevance_scores(
                query, k=top_k
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Retrieval error: %s", exc)
            return []

        chunks: List[RetrievedChunk] = []
        for doc, score in results:
            meta = doc.metadata or {}
            source = meta.get("source", "unknown")
            # Trim to just the filename for readability
            if "/" in source or "\\" in source:
                from pathlib import Path
                source = Path(source).name

            chunks.append(
                RetrievedChunk(
                    content=doc.page_content.strip(),
                    source=source,
                    score=float(score),
                    page=meta.get("page"),
                    extra_meta={k: v for k, v in meta.items()
                                if k not in ("source", "page")},
                )
            )

        # Sort descending by score
        chunks.sort(key=lambda c: c.score, reverse=True)

        logger.debug(
            "Retrieved %d chunks for query: %s…", len(chunks), query[:60]
        )
        return chunks


def build_context_string(chunks: List[RetrievedChunk]) -> str:
    """
    Concatenate retrieved chunks into a single context block
    for insertion into the system/user prompt.
    """
    if not chunks:
        return ""
    parts = [c.as_context_block() for c in chunks]
    return "\n\n---\n\n".join(parts)


# Module-level singleton — lazy-initialised on first use
_engine: Optional[RetrievalEngine] = None


def get_retrieval_engine() -> RetrievalEngine:
    """Return (or create) the module-level RetrievalEngine singleton."""
    global _engine
    if _engine is None:
        _engine = RetrievalEngine()
    return _engine
