"""
Document ingestion pipeline.

Supports:
  - Plain-text files (.txt)
  - PDF files (.pdf)          — via pypdf
  - Markdown files (.md)
  - HTML / web exports (.html)

Each document is split into overlapping chunks, embedded with a
sentence-transformers model, and stored in a persistent Chroma collection.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    PyPDFLoader,
    UnstructuredHTMLLoader,
)
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from backend.core.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DOCS_DIR,
    EMBEDDING_MODEL,
    VECTORSTORE_DIR,
)

logger = logging.getLogger(__name__)

COLLECTION_NAME = "iot_docs"


# ── Embedding singleton ────────────────────────────────────────────────────

def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a cached HuggingFace embeddings instance."""
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


# ── Loader helpers ─────────────────────────────────────────────────────────

def _load_directory(directory: Path) -> list:
    """Load all supported files from a directory tree."""
    docs = []

    loaders = [
        DirectoryLoader(str(directory), glob="**/*.txt", loader_cls=TextLoader,
                        loader_kwargs={"encoding": "utf-8"}, silent_errors=True),
        DirectoryLoader(str(directory), glob="**/*.md", loader_cls=TextLoader,
                        loader_kwargs={"encoding": "utf-8"}, silent_errors=True),
        DirectoryLoader(str(directory), glob="**/*.pdf", loader_cls=PyPDFLoader,
                        silent_errors=True),
        DirectoryLoader(str(directory), glob="**/*.html",
                        loader_cls=UnstructuredHTMLLoader, silent_errors=True),
    ]

    for loader in loaders:
        try:
            loaded = loader.load()
            docs.extend(loaded)
            logger.debug("Loaded %d docs from %s", len(loaded), loader)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Loader error (skipped): %s", exc)

    return docs


def _load_single_file(file_path: Path) -> list:
    """Load a single file by extension."""
    ext = file_path.suffix.lower()
    try:
        if ext == ".pdf":
            return PyPDFLoader(str(file_path)).load()
        elif ext == ".html":
            return UnstructuredHTMLLoader(str(file_path)).load()
        else:  # .txt, .md, anything text-like
            return TextLoader(str(file_path), encoding="utf-8").load()
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load %s: %s", file_path, exc)
        return []


def _stable_doc_id(source: str, chunk_index: int) -> str:
    """Deterministic chunk ID so re-ingestion is idempotent."""
    raw = f"{source}::{chunk_index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Public API ─────────────────────────────────────────────────────────────

def ingest_documents(
    source: Path | None = None,
    reset: bool = False,
) -> Chroma:
    """
    Ingest documents into the Chroma vector store.

    Parameters
    ----------
    source:
        A file or directory path.  Defaults to DOCS_DIR.
    reset:
        If True, wipe the existing collection before ingesting.

    Returns
    -------
    Chroma
        The populated (or existing) vector store.
    """
    source = source or DOCS_DIR
    source = Path(source)

    embeddings = get_embeddings()
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
    )

    if reset:
        logger.info("Resetting vector store collection '%s'", COLLECTION_NAME)
        vectorstore.delete_collection()
        vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(VECTORSTORE_DIR),
        )

    # Load raw documents
    logger.info("Loading documents from %s", source)
    if source.is_dir():
        raw_docs = _load_directory(source)
    elif source.is_file():
        raw_docs = _load_single_file(source)
    else:
        logger.warning("Source path does not exist: %s", source)
        return vectorstore

    if not raw_docs:
        logger.warning("No documents found at %s", source)
        return vectorstore

    logger.info("Loaded %d raw document pages/sections", len(raw_docs))

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(raw_docs)

    # Attach stable IDs
    ids = [
        _stable_doc_id(chunk.metadata.get("source", "unknown"), i)
        for i, chunk in enumerate(chunks)
    ]

    logger.info("Adding %d chunks to vector store", len(chunks))
    vectorstore.add_documents(documents=chunks, ids=ids)

    logger.info("Ingestion complete — %d chunks indexed", len(chunks))
    return vectorstore


def load_vectorstore() -> Chroma:
    """
    Load the existing persisted vector store without ingesting new docs.
    Raises FileNotFoundError if the store has not been initialised yet.
    """
    if not VECTORSTORE_DIR.exists():
        raise FileNotFoundError(
            f"Vector store not found at {VECTORSTORE_DIR}. "
            "Run scripts/ingest.py first."
        )
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=get_embeddings(),
        persist_directory=str(VECTORSTORE_DIR),
    )
