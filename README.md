# 🥝 Kiwi - Integrated Frontend & Backend

**AI-Powered Google Sheets Analytics with Natural Language Interface**

This is the integrated version combining:
- **Frontend**: Next.js 15 + React 19 (Kiwi-frontend)
- **Backend**: Python RAG system with FastAPI (kiwi-rag)

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+**
- **Node.js 18+** (or Bun)
- **Google Cloud Project** with Sheets API enabled
- **Gemini API Key**
- **ElevenLabs API Key** (optional, for voice features)

### 1. Backend Setup

```bash
cd kiwi-rag

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your API keys:
#   GEMINI_API_KEY=your_key
#   ELEVENLABS_API_KEY=your_key (optional)

# Add Google Sheets credentials
# Place your service_account.json in credentials/

# Start the API server
uvicorn api.main:app --reload --port 8000
```

The backend API will be available at `http://localhost:8000`

### 2. Frontend Setup

```bash
cd Kiwi-frontend

# Install dependencies
bun install  # or npm install

# Start the development server
bun run dev  # or npm run dev
```

The frontend will be available at `http://localhost:3000`

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                      │
│                   http://localhost:3000                     │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Chat Screen  │  │ Voice Input  │  │ Data Display │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                 │              │
│         └─────────────────┴─────────────────┘              │
│                           │                                │
│                    src/services/api.ts                     │
│                           │                                │
└───────────────────────────┼────────────────────────────────┘
                            │ HTTP/REST
                            │
┌───────────────────────────┼────────────────────────────────┐
│                           ▼                                │
│                  FastAPI Server                            │
│                http://localhost:8000                       │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Endpoints                           │  │
│  │  POST /api/load-dataset                              │  │
│  │  POST /api/query                                     │  │
│  │  POST /api/transcribe                                │  │
│  │  GET  /api/auth/check                                │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                          │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │           Service Layer (api/services.py)            │  │
│  └──────────────┬───────────────────────────────────────┘  │
│                 │                                          │
│  ┌──────────────▼───────────────────────────────────────┐  │
│  │          Core RAG Pipeline (Preserved)               │  │
│  │                                                       │  │
│  │  Schema Retrieval → Planning → Validation →          │  │
│  │  Execution → Explanation                             │  │
│  │                                                       │  │
│  │  ┌─────────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │  ChromaDB   │  │ DuckDB   │  │  Gemini  │        │  │
│  │  │  (Schemas)  │  │ (Data)   │  │  (AI)    │        │  │
│  │  └─────────────┘  └──────────┘  └──────────┘        │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│                  Backend (kiwi-rag)                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔌 API Endpoints

### 1. Load Dataset
**POST** `/api/load-dataset`

```json
// Request
{
  "url": "https://docs.google.com/spreadsheets/d/YOUR_ID/edit"
}

// Response
{
  "success": true,
  "stats": {
    "totalTables": 25,
    "totalRecords": 1305,
    "sheetCount": 5,
    "sheets": ["Sheet1", "Sheet2"],
    "detectedTables": [...]
  }
}
```

### 2. Process Query
**POST** `/api/query`

```json
// Request
{
  "text": "What is the total sales?"
}

// Response
{
  "success": true,
  "explanation": "The total sales is $45,230...",
  "data": [...],
  "plan": {...},
  "schema_context": [...],
  "data_refreshed": false
}
```

### 3. Transcribe Audio
**POST** `/api/transcribe`

```
Content-Type: multipart/form-data
audio: <audio file blob>

// Response
{
  "success": true,
  "text": "What is the total sales?"
}
```

### 4. Check Authentication
**GET** `/api/auth/check`

```json
// Response
{
  "authenticated": true
}
```

---

## 🎯 Features

### Core Capabilities
- ✅ **Natural Language Queries** - Ask questions in plain English, Tamil, Hindi, etc.
- ✅ **Google Sheets Integration** - Direct connection with automatic change detection
- ✅ **Voice Input/Output** - Speech-to-text and text-to-speech
- ✅ **Multilingual Support** - Works with any language
- ✅ **Smart Analytics** - Aggregations, filters, lookups, rankings
- ✅ **Real-time Updates** - Automatic data refresh on sheet changes

### Technical Features
- ⚡ **FastAPI Backend** - High-performance REST API
- 🎯 **RAG Pipeline** - Retrieval-Augmented Generation for accurate answers
- 🤖 **AI Planning** - Gemini 2.5 Pro for query understanding
- 💾 **DuckDB** - Fast in-memory analytics
- 🧠 **ChromaDB** - Vector store for semantic schema search
- 🎤 **ElevenLabs** - Professional voice transcription

---

## 🛠️ Development

### Backend Development

```bash
cd kiwi-rag

# Run API server with auto-reload
uvicorn api.main:app --reload --port 8000

# Run original Streamlit app (optional)
streamlit run app/streamlit_app.py

# Run CLI query tool
python run_query.py
```

### Frontend Development

```bash
cd Kiwi-frontend

# Development server
bun run dev

# Build for production
bun run build

# Start production server
bun run start
```

---

## 📝 Environment Variables

### Backend (.env in kiwi-rag/)
```env
GEMINI_API_KEY=your_gemini_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key  # Optional
SUPABASE_URL=your_supabase_url  # Optional
SUPABASE_KEY=your_supabase_key  # Optional
```

### Frontend (.env.local in Kiwi-frontend/)
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 🧪 Testing

### Test Backend API
```bash
# Health check
curl http://localhost:8000

# Test load dataset
curl -X POST http://localhost:8000/api/load-dataset \
  -H "Content-Type: application/json" \
  -d '{"url": "YOUR_GOOGLE_SHEETS_URL"}'

# Test query
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the total sales?"}'
```

### Test Frontend
1. Open http://localhost:3000
2. Paste Google Sheets URL
3. Click "Analyze Dataset"
4. Ask questions in the chat

---

## 📂 Project Structure

```
kiwio/
├── kiwi-rag/                    # Backend
│   ├── api/                     # FastAPI server (NEW)
│   │   ├── main.py             # API application
│   │   ├── models.py           # Pydantic models
│   │   └── services.py         # Service layer
│   ├── app/                     # Streamlit app (original)
│   ├── data_sources/            # Google Sheets connector
│   ├── schema_intelligence/     # RAG schema retrieval
│   ├── planning_layer/          # Query planning
│   ├── execution_layer/         # SQL execution
│   ├── explanation_layer/       # Natural language generation
│   └── requirements.txt
│
└── Kiwi-frontend/               # Frontend
    ├── src/
    │   ├── app/                # Next.js pages
    │   ├── components/         # React components
    │   ├── services/           # API integration
    │   └── lib/                # Types and utilities
    └── package.json
```

---

## 🔒 Security Notes

- API keys stored in `.env` (not committed to git)
- Google credentials in separate JSON file (not committed)
- Read-only access to Google Sheets
- CORS configured for localhost only
- Optional Supabase authentication

---

## 🐛 Troubleshooting

### Backend won't start
- Check Python version (3.9+)
- Verify all dependencies installed: `pip install -r requirements.txt`
- Check `.env` file exists with API keys
- Verify Google credentials file exists

### Frontend can't connect to backend
- Ensure backend is running on port 8000
- Check `.env.local` has correct `NEXT_PUBLIC_API_BASE_URL`
- Verify CORS is configured correctly in `api/main.py`

### Voice features not working
- Add `ELEVENLABS_API_KEY` to backend `.env`
- System falls back to gTTS if ElevenLabs unavailable
- Check browser microphone permissions

---

## 📚 Documentation

- [Frontend README](Kiwi-frontend/README.md) - Frontend-specific docs
- [Backend README](kiwi-rag/README.md) - Backend-specific docs
- [Implementation Plan](implementation_plan.md) - Integration details

---

## 🙏 Credits

- **Gemini AI** - Query planning and explanation
- **ElevenLabs** - Voice input/output
- **ChromaDB** - Vector storage
- **DuckDB** - Fast analytics
- **FastAPI** - API framework
- **Next.js** - Frontend framework

---

**Built with ❤️ for multilingual data analytics**
