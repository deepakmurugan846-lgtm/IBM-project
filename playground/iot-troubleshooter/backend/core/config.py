"""
Central configuration — all values come from environment variables.
Copy .env.example to .env and fill in your secrets before running.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parents[2]
DOCS_DIR = BASE_DIR / "docs" / "sample_docs"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

# ── Groq ──────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_MAX_TOKENS: int = int(os.environ.get("GROQ_MAX_TOKENS", "1024"))
GROQ_TEMPERATURE: float = float(os.environ.get("GROQ_TEMPERATURE", "0.2"))

# ── Embedding ──────────────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

# ── Retrieval ──────────────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", "512"))
CHUNK_OVERLAP: int = int(os.environ.get("CHUNK_OVERLAP", "64"))
RETRIEVAL_TOP_K: int = int(os.environ.get("RETRIEVAL_TOP_K", "5"))

# ── Conversation ───────────────────────────────────────────────────────────
MAX_HISTORY_TURNS: int = int(os.environ.get("MAX_HISTORY_TURNS", "10"))

# ── API ────────────────────────────────────────────────────────────────────
API_HOST: str = os.environ.get("API_HOST", "0.0.0.0")
API_PORT: int = int(os.environ.get("API_PORT", "8000"))
API_RELOAD: bool = os.environ.get("API_RELOAD", "true").lower() == "true"

# ── Validation ─────────────────────────────────────────────────────────────
def validate() -> None:
    """Raise early if critical secrets are missing."""
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. "
            "Export it or add it to your .env file."
        )
