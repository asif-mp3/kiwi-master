# Thara.ai

A voice-enabled AI data assistant that lets you query Google Sheets data using natural language (voice or text). Built with Next.js frontend and FastAPI backend.

## What it does

- **Natural Language Queries**: Ask questions about your spreadsheet data in plain English or Tamil
- **Voice Interface**: Speak your questions and hear responses via ElevenLabs TTS
- **Data Visualization**: Automatic charts (bar, line, pie) for analytical queries
- **Smart Analytics**: Supports comparisons, trends, rankings, and aggregations
- **Professional AI Personality**: Friendly, helpful responses without being robotic

## Tech Stack

**Frontend:**
- Next.js 15 + React
- Tailwind CSS
- Recharts (visualizations)
- Framer Motion (animations)

**Backend:**
- FastAPI (Python)
- DuckDB (in-memory analytics)
- ChromaDB (semantic search)
- Google Gemini (LLM for planning & explanations)
- ElevenLabs (voice STT/TTS)

## Prerequisites

- Python 3.11+
- Node.js 18+
- Gemini API Key ([Get here](https://aistudio.google.com/app/apikey))
- ElevenLabs API Key ([Get here](https://elevenlabs.io/))
- Google Service Account JSON (for Sheets access)

## Setup

### Backend

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create `backend/.env`:
```env
GEMINI_API_KEY=your-key-here
ELEVENLABS_API_KEY=your-key-here
```

Place your Google service account JSON at `backend/credentials/service_account.json`

Start backend:
```bash
python -m uvicorn api.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Start frontend:
```bash
npm run dev
```

Open http://localhost:3000

## Usage

1. Paste your Google Sheet URL and connect
2. Ask questions via text or voice:
   - "What were total sales last month?"
   - "Compare Chennai vs Bangalore revenue"
   - "Show me top 5 products"
   - "How is the sales trend?"

## Query Types Supported

| Type | Example |
|------|---------|
| Metric | "Total sales?" |
| Comparison | "August vs December sales?" |
| Trend | "How are sales trending?" |
| Rank | "Top 5 items by revenue?" |
| Filter | "Sales above 10,000?" |
| Lookup | "Sales for product X?" |

## Project Structure

```
Thara-ai/
├── backend/
│   ├── api/              # FastAPI routes & services
│   ├── planning_layer/   # LLM query planning
│   ├── execution_layer/  # SQL execution
│   ├── explanation_layer/# Natural language responses
│   ├── utils/            # Helpers (voice, memory, etc.)
│   └── config/           # Settings
│
└── frontend/
    └── src/
        ├── app/          # Next.js pages
        ├── components/   # React components
        ├── lib/          # Hooks, types, utils
        └── services/     # API client
```

## Share Your Sheet

Your Google Sheet must be shared with the service account email found in your `service_account.json`:
```
your-service@your-project.iam.gserviceaccount.com
```

Give it **Viewer** access.

## License

MIT
