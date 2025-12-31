# Kiwi-RAG: AI-Powered Analytics for Google Sheets

**Current Version:** 1.0.0
**Architecture:** FastAPI (Backend) + Next.js 15 (Frontend) + DuckDB (In-Memory Analytics) + Gemini (LLM)

Kiwi-RAG is a specialized RAG (Retrieval-Augmented Generation) system designed to perform structured analytics on Google Sheets data using natural language. Unlike generic RAG systems that chunk text, Kiwi-RAG treats spreadsheets as relational databases, performing deterministic SQL execution for accuracy while using LLMs for planning, translation, and explanation.

---

## 🏗️ System Architecture

The system is split into two distinct services:

### 1. Backend (`kiwi-rag`)
A **FastAPI** application that serves as the brain of the operation. It does NOT use LangChain or LlamaIndex orchestrators; instead, it uses a custom functional pipeline defined in `api/services.py`.

**Core Components:**
*   **Orchestrator (`api/services.py`)**: The central nervous system. It manages the linear pipeline: `Ingest -> Translate -> Plan -> Validate -> Execute -> Explain`.
*   **Data Engine (`data_sources/gsheet/`)**:
    *   **Connector**: Uses `gspread` to fetch raw data.
    *   **Table Detector**: Custom logic (`table_detection.py`) to verify and split single sheets into multiple logical tables based on empty rows/headers.
    *   **Type Inference**: Aggressive logic (`connector.py`) that forces columns to Numeric if >30% of values are numbers, to enable SQL aggregation.
    *   **Storage**: **DuckDB** (In-Memory). Data is not persisted to disk across restarts (except for optional snapshots).
*   **Planner (`planning_layer/`)**: Uses **Gemini 1.5 Flash** to convert Natural Language -> JSON Query Plan.
*   **Executor (`execution_layer/`)**: Compiles JSON Plans -> SQL and runs them against DuckDB. *This is where the math happens.*
*   **Translation (`utils/translation.py`)**: Dedicated layer for Tamil <-> English conversion. Enforces **Strict Number-to-Words** formatting for TTS.

### 2. Frontend (`frontend`)
A **Next.js 15** (App Router) application serving the Chat UI.
*   **State Management**: `useAppState` global hook.
*   **Protocol**: REST API communication with Backend (`api.ts`).
*   **Voice**: Captures audio (Web Audio API) -> Sends Blob to Backend -> Plays returned MP3.

---

## 🔄 End-to-End Workflows

### 1. Data Ingestion Flow
**Endpoint:** `POST /api/load-dataset`
1.  **Fetch**: Backend pulls ALL cells from the Google Sheet.
2.  **Hash**: Computes SHA-256 of the raw sheet content to detect changes.
3.  **Detect**: Splits the sheet into logical tables (handling multiple tables per sheet).
4.  **Infer**: Converts string data to proper types (Int, Float, Date). *Critical for SQL math.*
5.  **Index**: Generates embeddings for Table Schemas (Column Names, Descriptions) and stores in **ChromaDB**.
6.  **Load**: Inserts cleaned data into **DuckDB** tables.

### 2. Query Execution Flow (Text)
**Endpoint:** `POST /api/query`
1.  **Pre-Process**:
    *   Checks for "Greetings" (regex).
    *   **Translate**: If Tamil detected, translates to English (`utils/translation.py`).
2.  **Retrieve Schema**: Fetches top-50 relevant table schemas from ChromaDB (`top_k=50` hardcoded for high recall).
3.  **Plan**: LLM (Gemini) generates a **JSON Query Plan** (Intent, Table, Columns, Filters).
4.  **Validate**: `plan_validator.py` checks if tables/columns actually exist and if the query type is valid.
5.  **Execute**: `sql_compiler.py` converts JSON -> SQL. DuckDB executes it.
6.  **Explain**: LLM generates a natural language answer based on the SQL result.
7.  **Post-Process**:
    *   If original query was Tamil, translate explanation to Tamil.
    *   **Strict Rule**: Convert "6450" -> "six thousand..." (or Tamil equivalent) for TTS.

### 3. Voice Workflow
**Endpoint:** `POST /api/transcribe` & `POST /api/text-to-speech`
1.  **ASR**: Frontend sends WAV blob -> Backend uses **ElevenLabs Scribe v2** -> Returns Text.
2.  **Query**: Frontend sends Text -> Backend processes (see above).
3.  **TTS**: Frontend sends Response Text -> Backend uses **ElevenLabs** (Turbo v2.5 for English, Multilingual v2 for Tamil) -> Returns MP3.

---

## 🛠️ Configuration & Setup

### Environment Variables
Required in `kiwi-rag/.env`:
```bash
GOOGLE_API_KEY=...          # For Gemini
ELEVENLABS_API_KEY=...      # For Voice
```
Required in `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Credentials
*   **Service Account**: Google Cloud Service Account JSON must be placed at `kiwi-rag/credentials/service_account.json`. *This file is git-ignored.*

### Running the System
1.  **Backend**:
    ```bash
    cd kiwi-rag
    pip install -r requirements.txt
    python -m uvicorn api.main:app --reload --port 8000
    ```
2.  **Frontend**:
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

---

## ⚠️ Limitations & Known Constraints

1.  **In-Memory Database**: DuckDB runs in-memory. If the backend restarts, data must be re-fetched from Google Sheets.
2.  **Single Tenant**: The `app_state` singleton in `services.py` means all users share the same loaded dataset. Not multi-user safe.
3.  **High Latency (Initial)**: The first load of a large sheet takes time due to embedding generation.
4.  **Paranoid Refresh Disabled**: Auto-refresh on every query is currently **DISABLED** in `services.py` to improve query latency. You must manually reload the dataset to see sheet updates.
5.  **Hardcoded Models**:
    *   Translation: `gemini-1.5-flash`
    *   Planner: `gemini-1.5-flash` (via `settings.yaml` default)
6.  **Tamil Support**:
    *   Relies on Translation Layer. SQL queries run in English.
    *   Entity matching (e.g., matching a Tamil name to an English DB record) is probabilistic and depends on the LLM's translation accuracy.

## 🛑 Anti-Patterns (Do Not Do This)

*   **Do NOT push `service_account.json`**: It is ignored for a reason.
*   **Do NOT use `gemini-pro`**: It is deprecated/404. Use `gemini-1.5-flash`.
*   **Do NOT expect persistent sessions**: Refreshing the browser resets the chat UI State (though backend might keep data).
*   **Do NOT modify `plan_schema.json`**: This breaks the strict validation contract between Planner and Executor.

## 🔌 Integration Points

*   **Adding a Metric**: Update `analytics_engine/metric_registry.py`.
*   **New Sheet Logic**: Update `data_sources/gsheet/table_detection.py`.
*   **Voice Config**: `utils/voice_utils.py` contains the hardcoded Voice IDs.
