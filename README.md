# Kiwi Master - Voice-Enabled Analytics Assistant

A Next.js + FastAPI application that enables natural language querying of Google Sheets data with voice interaction powered by ElevenLabs.

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+**
- **Node.js 18+** 
- **Google Cloud Service Account** (for Sheets access)
- **ElevenLabs API Key** (for voice features)
- **Gemini API Key** (for AI processing)

### 1. Clone the Repository
```bash
git clone https://github.com/asif-mp3/kiwi-master.git
cd kiwi-master
```

### 2. Backend Setup

#### Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### Configure Environment Variables
Create `backend/.env`:
```env
# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
API_ENV=development

# Google Cloud Services
GOOGLE_CREDENTIALS_PATH=../credentials/service_account.json

# AI Services
GEMINI_API_KEY=your_gemini_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Database Configuration
DUCKDB_PATH=./data_sources/snapshots/latest.duckdb
CHROMADB_PATH=./chroma_db
```

#### Add Google Service Account Credentials
1. Create a Google Cloud Service Account with Sheets API access
2. Download the JSON credentials file
3. Place it at `credentials/service_account.json`

### 3. API Server Setup

```bash
cd ../api
pip install -r requirements.txt
```

### 4. Frontend Setup

```bash
cd ../frontend
npm install
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 5. Run the Application

**Terminal 1 - Backend API:**
```bash
cd api
python main.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Access the app:** http://localhost:3000

## 📋 First-Time Setup

1. **Login** with any username (no authentication required)
2. **Connect Google Sheet:**
   - Click "Connect Dataset"
   - Paste your Google Sheets URL
   - Wait for the sheet to load (first time may take 30-60 seconds)
3. **Start Chatting:**
   - Use voice (microphone button) or text input
   - Ask questions about your data in natural language

## 🔑 API Keys Setup

### Google Cloud Service Account
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select existing
3. Enable **Google Sheets API**
4. Create Service Account → Download JSON key
5. Share your Google Sheet with the service account email

### ElevenLabs API Key
1. Sign up at [ElevenLabs](https://elevenlabs.io)
2. Get API key from Settings
3. Add to `backend/.env`

### Gemini API Key
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create API key
3. Add to `backend/.env`

## 🛠️ Troubleshooting

### Import Errors
```bash
# Reinstall dependencies
cd backend && pip install -r requirements.txt
cd ../api && pip install -r requirements.txt
cd ../frontend && npm install
```

### Voice Not Working
- Check ElevenLabs API key in `backend/.env`
- Ensure microphone permissions are granted
- Free tier may have usage limits

### Sheet Connection Fails
- Verify service account JSON is in `credentials/` folder
- Ensure Google Sheet is shared with service account email
- Check `GOOGLE_CREDENTIALS_PATH` in `.env`

### Backend Errors
- Check `api/main.py` is running on port 8000
- Verify `NEXT_PUBLIC_API_URL` in `frontend/.env.local`

## 📁 Project Structure

```
kiwi-master/
├── api/                    # FastAPI server
│   ├── routers/           # API endpoints
│   └── main.py            # Entry point
├── backend/               # Core analytics engine
│   ├── analytics_engine/  # Query processing
│   ├── planning_layer/    # Query planning
│   ├── schema_intelligence/ # Schema extraction
│   └── core_engine.py     # Main engine
├── frontend/              # Next.js app
│   └── src/
│       ├── components/    # React components
│       └── lib/           # Utilities & API client
└── credentials/           # Service account keys (gitignored)
```

## 🔒 Security Notes

- **Never commit** `.env` files or `credentials/*.json`
- Service account should have **read-only** access to sheets
- Use environment variables for all sensitive data

## 📝 Features

- ✅ Natural language querying of Google Sheets
- ✅ Voice input/output (STT/TTS)
- ✅ Multi-chat sessions
- ✅ Real-time sheet loading with progress
- ✅ Automatic schema detection
- ✅ Query planning and validation

## 🤝 Contributing

Issues and PRs welcome!

## 📄 License

MIT
