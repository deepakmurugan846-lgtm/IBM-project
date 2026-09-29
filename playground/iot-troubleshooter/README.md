# 🔧 IoT Troubleshooter

A fully deployable, RAG-powered IoT device troubleshooting chatbot.  
**Stack:** Groq AI · FastAPI · Streamlit · LangChain · Chroma · sentence-transformers

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Streamlit Chat UI  :8501                    │
│  (chat bubbles · source badges · document upload · session mgmt)│
└──────────────────────────────┬──────────────────────────────────┘
                               │  HTTP (REST JSON)
┌──────────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend  :8000                        │
│  POST /chat  ·  POST /chat/reset  ·  POST /ingest               │
│  POST /ingest/upload  ·  GET /docs-status  ·  GET /health       │
└───────────┬────────────────────────────────┬────────────────────┘
            │                                │
┌───────────▼──────────┐       ┌─────────────▼──────────────────┐
│  Retrieval Engine    │       │  Groq LLM (llama3-70b-8192)    │
│  Chroma vector store │       │  · System prompt (role + rules)│
│  sentence-transformers│      │  · RAG context injection       │
│  Top-K similarity    │       │  · Conversation history        │
└───────────┬──────────┘       └────────────────────────────────┘
            │
┌───────────▼───────────────────────────────────────────────────┐
│  Document Ingestion Pipeline                                   │
│  PDF · TXT · MD · HTML  →  chunking (512/64)  →  embedding    │
│  →  Chroma persistent store  (vectorstore/)                    │
└───────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
iot-troubleshooter/
├── backend/
│   ├── core/
│   │   ├── config.py          # All settings from env vars
│   │   ├── ingestion.py       # Document loading, chunking, embedding
│   │   ├── retrieval.py       # Chroma query engine, RetrievedChunk dataclass
│   │   └── llm.py             # Groq client, TroubleshootingEngine, ConversationManager
│   ├── api/
│   │   └── app.py             # FastAPI routes and session management
│   └── tests/
│       └── test_troubleshooter.py   # pytest suite (ingestion, retrieval, LLM, API)
├── frontend/
│   └── app.py                 # Streamlit chat UI
├── docs/
│   └── sample_docs/           # Drop your IoT manuals/guides here
│       ├── wifi_troubleshooting.txt
│       ├── firmware_update_guide.txt
│       ├── sensor_troubleshooting.txt
│       └── device_compatibility_pairing.txt
├── scripts/
│   ├── ingest.py              # CLI ingestion script
│   └── validate_rag.py        # RAG smoke-test (no Groq key needed)
├── vectorstore/               # Auto-created — Chroma persistent store
├── .env.example               # Copy to .env and fill in secrets
├── .gitignore
├── pytest.ini
└── requirements.txt
```

---

## Quick Start

### 1 — Prerequisites

- Python 3.10+
- A [Groq API key](https://console.groq.com/) (free tier available)

### 2 — Install

```bash
cd iot-troubleshooter
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **First run:** `sentence-transformers` downloads the embedding model (~90 MB)
> automatically. It is cached locally after the first download.

### 3 — Configure

```bash
cp .env.example .env
# Open .env and set GROQ_API_KEY=<your key>
```

### 4 — Ingest documents

```bash
# Index the bundled sample docs (WiFi, firmware, sensors, pairing guides)
python scripts/ingest.py

# Or add your own manuals first, then ingest:
cp /path/to/your/manual.pdf docs/sample_docs/
python scripts/ingest.py --reset
```

### 5 — Start the backend API

```bash
uvicorn backend.api.app:app --host 0.0.0.0 --port 8000 --reload
```

### 6 — Start the frontend UI (separate terminal)

```bash
streamlit run frontend/app.py
```

Open **http://localhost:8501** in your browser.

---

## Using the Chatbot

1. **Describe your problem** — type in plain language what your device is doing.  
   *"My Zigbee door sensor stopped reporting after I moved it to a new room."*

2. **Follow the guided steps** — the bot will ask one clarifying question at a
   time if it needs more information, then provide a structured response:
   - **Diagnosis** — what is most likely wrong
   - **Evidence** — the documentation source it's drawing from
   - **Steps** — numbered, actionable instructions

3. **Upload your device's manual** — use the sidebar "Upload Document" to add
   a PDF or text file. It will be chunked, embedded, and immediately available
   for retrieval.

4. **New conversation** — click "New Conversation" in the sidebar to start fresh.

---

## API Reference

### `POST /chat`
```json
{
  "message": "My smart plug won't connect to WiFi",
  "session_id": null
}
```
Response:
```json
{
  "session_id": "abc123...",
  "answer": "**Diagnosis**: ...\n**Evidence**: ...\n**Steps**: ...",
  "sources": ["wifi_troubleshooting.txt"],
  "retrieval_used": true,
  "model": "llama3-70b-8192",
  "usage": {"prompt_tokens": 512, "completion_tokens": 380, "total_tokens": 892},
  "turn": 1
}
```

### `POST /chat/reset`
```json
{ "session_id": "abc123..." }
```

### `POST /ingest`
```json
{ "reset": false }
```

### `POST /ingest/upload`
Multipart form: `file=<binary>` (PDF, TXT, MD, HTML)

### `GET /docs-status`
Returns the number of chunks currently indexed.

### `GET /health`
Liveness check.

Interactive API docs are available at **http://localhost:8000/docs**.

---

## Adding Your Own Documentation

Drop any of the following into `docs/sample_docs/` (or any subdirectory) and
re-run `python scripts/ingest.py`:

| Format | Notes |
|--------|-------|
| `.txt` | Plain text, markdown-style text |
| `.md`  | Markdown files |
| `.pdf` | Searchable PDFs (scanned PDFs without OCR won't work well) |
| `.html`| Web page exports |

Or use the **Upload Document** button in the UI to add files at runtime.

---

## Running Tests

```bash
pytest backend/tests/ -v
```

The test suite mocks Groq API calls so no real API key is consumed.

### RAG Smoke-Test (no Groq key required)

```bash
python scripts/validate_rag.py
```

This ingests a tiny in-memory document, runs retrieval queries, and confirms
the full pipeline (chunking → embedding → similarity search) is working.

---

## Configuration Reference

All settings are environment variables. See `.env.example` for the full list.

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | — | **Required.** Your Groq API key. |
| `GROQ_MODEL` | `llama3-70b-8192` | Groq model to use. |
| `GROQ_MAX_TOKENS` | `1024` | Max tokens per response. |
| `GROQ_TEMPERATURE` | `0.2` | Lower = more deterministic answers. |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model. |
| `CHUNK_SIZE` | `512` | Characters per document chunk. |
| `CHUNK_OVERLAP` | `64` | Overlap between adjacent chunks. |
| `RETRIEVAL_TOP_K` | `5` | Number of chunks retrieved per query. |
| `MAX_HISTORY_TURNS` | `10` | Conversation turns kept in context. |
| `API_PORT` | `8000` | FastAPI server port. |
| `API_BASE_URL` | `http://localhost:8000` | URL Streamlit uses to reach the API. |

---

## Extending the Bot

| Goal | Where to change |
|------|----------------|
| Change the LLM system prompt / persona | `backend/core/llm.py` → `_BASE_SYSTEM_PROMPT` |
| Add a new retrieval strategy (MMR, hybrid) | `backend/core/retrieval.py` → `RetrievalEngine.retrieve()` |
| Persist sessions to disk / Redis | `backend/api/app.py` → `_sessions` dict |
| Add authentication to the API | FastAPI dependency injection in `backend/api/app.py` |
| Deploy to production | Use `gunicorn` + `uvicorn` workers for the API; deploy Streamlit via Streamlit Community Cloud or Docker |

---

## Security Notes

- **GROQ_API_KEY** is loaded exclusively from environment variables — never
  hardcoded.
- The RAG documentation context is treated as data only — the system prompt
  explicitly instructs the model never to follow instructions embedded in
  retrieved documents.
- For production: restrict `allow_origins` in the CORS middleware, add API
  key authentication, and use HTTPS.

---

## License

MIT — free to use, modify, and distribute.
