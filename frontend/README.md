# 🥝 Kiwi Frontend - Backend Integration Manual

This repository contains the **Production-Ready Frontend** for the Kiwi-RAG system.
It is designed as a "Socket" that strictly adheres to your Python backend's data structures.

---

## 🚀 Quick Start for Backend Engineers

1.  **Clone & Install**:
    ```bash
    git clone https://github.com/asif-mp3/Kiwi-frontend.git
    cd Kiwi-frontend
    bun install  # or npm install
    ```
2.  **Run Locally**:
    ```bash
    bun run dev  # or npm run dev
    ```
    Access at `http://localhost:3000`.

---

## ⚙️ Environment Configuration

Create a `.env` file in your **backend** root (not here) with the following standard configuration:

```ini
# ==========================================
# API Configuration
# ==========================================
API_PORT=8000
API_HOST=0.0.0.0
API_ENV=development

# ==========================================
# Google Cloud Services
# ==========================================
GOOGLE_CREDENTIALS_PATH=../credentials/service_account.json
GOOGLE_SHEET_ID=your_sheet_id_here

# ==========================================
# AI Services
# ==========================================
GEMINI_API_KEY=your_gemini_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# ==========================================
# Database Configuration
# ==========================================
DUCKDB_PATH=./data_sources/snapshots/latest.duckdb
CHROMADB_PATH=./chroma_db
```

---

## 🔌 Integration Guide (Critical)

**You only need to edit ONE file to connect your backend:**
👉 **`src/services/api.ts`**

This file contains 4 Client-Side Stubs. Currently, they return mock data using `setTimeout`.
**Your Job:** Replace the `setTimeout` blocks with `fetch()` calls to your Python API.

### 1. `loadDataset(url: string)`
*   **Trigger**: User clicks "Analyze Dataset".
*   **Input**: Google Sheet URL.
*   **Expected Output**: `LoadDataResponse` object.
    *   **Crucial Logic**: The frontend expects a list of `DetectedTable` objects.
    *   **Schema**: Matches `connector.py` output (`source_id`, `sheet_hash`, `row_range`).
    *   *See `src/lib/types.ts` for exact interface.*

### 2. `sendMessage(text: string)`
*   **Trigger**: User types a question or finishes speaking.
*   **Input**: User query string.
*   **Expected Output**: `ProcessQueryResponse` object.
    *   **Crucial Logic**:
        *   `explanation`: Text response (Markdown supported).
        *   `plan`: **Raw JSON** matching `plan_schema.json`. The UI renders this automatically.
        *   `data`: Array of objects (for Table/Chart visualization).

### 3. `transcribeAudio(audioBlob: Blob)`
*   **Trigger**: User clicks Microphone -> Speaks -> Stops.
*   **Input**: Binary `Blob` (audio/wav).
*   **Expected Output**: Transcribed text string.
*   **REQUIRED MODELS**:
    *   **STT**: Use `scribe_v1` (ElevenLabs) for transcription.
    *   **TTS**: Use `multilingual_v2` (ElevenLabs) for voice output.
    *   **Voice Profile**: **Female Voice** (English + Tamil supported).

### 4. `checkAuth()`
*   **Status**: **DISABLED** (Always returns true).
*   **Note**: The user has requested to skip authentication for this version. Ensure your backend allows open access or handles its own stateless checks.

---

## 📐 Data Contracts (Strict)

The frontend Types are **hard-synced** to your Backend structs.
Do not change these shapes on the backend without updating `src/lib/types.ts`.

| Frontend Type | Backend Equivalent | File Source |
| :--- | :--- | :--- |
| `QueryPlan` | `QueryPlan` Schema | `planning_layer/plan_schema.json` |
| `DetectedTable` | `DetectedTable` Class | `data_sources/gsheet/connector.py` |
| `ProcessQueryResponse` | `process_query()` Return | `app/streamlit_app.py` |

**If your API returns these exact JSON shapes, the UI will just work.**

---

## 🛠 Tech Stack (FYI)
*   **Framework**: Next.js 15 + React 19
*   **Styling**: Tailwind CSS 4
*   **Voice**: Native Web Audio API + Canvas Visualization

*No further frontend context is required for integration.*
