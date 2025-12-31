# Kiwi-RAG: Voice-Enabled Google Sheets Analytics

An AI-powered conversational analytics system that transforms Google Sheets into a queryable database through natural language (voice or text) using a Retrieval-Augmented Generation (RAG) architecture.

## What This System Does

Kiwi-RAG enables users to ask questions about Google Sheets data using natural language—either by typing or speaking. The system automatically detects tables within sheets, builds semantic indexes, generates SQL queries from natural language, executes them, and explains results in plain language. It supports multi-language queries (English and Tamil), voice interaction via ElevenLabs, and maintains conversation history across multiple chat sessions.

---

## System Architecture

### High-Level Architecture

```
┌─────────────┐         ┌──────────────────────────────────────┐
│   Frontend  │◄───────►│            Backend API               │
│  (Next.js)  │  HTTP   │          (FastAPI)                   │
└─────────────┘         └──────────────────────────────────────┘
                                      │
                        ┌─────────────┼─────────────┐
                        │             │             │
                   ┌────▼───┐   ┌────▼────┐   ┌────▼────┐
                   │ Google │   │ DuckDB  │   │ChromaDB │
                   │ Sheets │   │(Analytics)  │(Vectors)│
                   └────────┘   └─────────┘   └─────────┘
```

The system consists of two independent processes:
1. **Backend** (`kiwi-rag/`): Python FastAPI server (port 8000)
2. **Frontend** (`frontend/`): Next.js development server (port 3000)

---

## Backend Architecture (kiwi-rag/)

### Directory Structure and Component Responsibilities

```
kiwi-rag/
├── api/                    # REST API layer
│   ├── main.py            # FastAPI app, CORS, endpoints
│   ├── models.py          # Pydantic request/response schemas
│   └── services.py        # Business logic, RAG orchestration
├── planning_layer/         # LLM query planning
│   ├── planner_client.py  # Gemini API client
│   ├── planner_prompt.py  # System prompts
│   └── plan_schema.json   # Query plan JSON schema
├── validation_layer/       # Plan validation
│   ├── plan_validator.py  # Schema/type/rule validation
│   └── rejection_handler.py
├── execution_layer/        # SQL generation and execution
│   ├── sql_compiler.py    # Plan → SQL compilation
│   └── executor.py        # DuckDB query execution
├── explanation_layer/      # Natural language generation
│   ├── explainer_client.py # Gemini explanation generation
│   └── explanation_prompt.py
├── schema_intelligence/    # Semantic schema retrieval
│   ├── chromadb_client.py # Vector store management
│   ├── embedding_builder.py # Schema document creation
│   └── hybrid_retriever.py # Semantic search
├── data_sources/gsheet/    # Google Sheets integration
│   ├── connector.py       # Sheet fetching, type inference
│   ├── table_detection.py # Multi-table detection
│   ├── change_detector.py # Hash-based change tracking
│   ├── snapshot_loader.py # DuckDB snapshot creation
│   └── sheet_hasher.py    # SHA-256 hashing
├── analytics_engine/       # SQL analytics
│   ├── duckdb_manager.py  # DuckDB connection manager
│   ├── metric_registry.py # Pre-defined metrics
│   └── sanity_checks.py   # Result validation
├── utils/                  # Cross-cutting utilities
│   ├── translation.py     # Tamil ↔ English (Gemini)
│   ├── voice_utils.py     # ElevenLabs STT/TTS
│   ├── permanent_memory.py # JSON-based user preferences
│   ├── greeting_detector.py # Casual chat detection
│   └── memory_detector.py # Memory intent parsing
└── config/
    └── settings.yaml      # Configuration (LLM, DB, Sheets)
```

### Request Flow: End-to-End

#### 1. Dataset Loading (`POST /api/load-dataset`)

**Entry Point**: `api/main.py:load_dataset()` → `api/services.py:load_dataset_service()`

**Execution Flow**:
```
1. Extract spreadsheet ID from URL (regex pattern matching)
2. Update config/settings.yaml with new spreadsheet_id
3. Initialize ChromaDB vector store (HuggingFace embeddings)
4. Fetch sheets via data_sources/gsheet/connector.py:fetch_sheets_with_tables()
   ├── Authenticate with Google Sheets API (service account OAuth2)
   ├── Fetch all worksheets from spreadsheet
   ├── For each sheet:
   │   ├── Compute SHA-256 hash of raw data (for change detection)
   │   ├── Detect multiple tables using custom_detector.py
   │   ├── Apply intelligent type inference:
   │   │   ├── Numeric: >30% of values are numbers → INT64/FLOAT
   │   │   ├── Boolean: True/False/Yes/No/1/0 → BOOL
   │   │   ├── Date: >50% parseable as dates → DATETIME
   │   │   └── String: Default fallback
   │   ├── Combine Date + Time columns into single timestamp
   │   └── Return DetectedTable objects with metadata
5. Clear ChromaDB collection (delete all previous embeddings)
6. Load snapshot into DuckDB via snapshot_loader.py
   ├── Create in-memory DuckDB connection
   ├── Register each table as DuckDB table (table_id as name)
   ├── Persist to data_sources/snapshots/latest.duckdb
7. Rebuild ChromaDB vector store
   ├── Generate schema documents (table/column descriptions)
   ├── Embed using sentence-transformers/all-MiniLM-L6-v2
   ├── Store in schema_store/ directory with metadata
8. Build and return LoadDataResponse with statistics
```

**Key Data Structures**:
- **DetectedTable**: `{table_id, title, sheet_name, source_id, sheet_hash, row_range, col_range, total_rows, columns, dataframe}`
- **DuckDB Tables**: Named by `table_id`, stored in-memory at `data_sources/snapshots/latest.duckdb`
- **ChromaDB Documents**: Schema descriptions with `{type, table, metric, source_id}` metadata

#### 2. Query Processing (`POST /api/query`)

**Entry Point**: `api/main.py:process_query()` → `api/services.py:process_query_service()`

**Complete Pipeline**:
```
1. Pre-Processing Layer
   ├── Phonetic corrections (hardcoded: "fresh geese" → "Freshggies")
   ├── Greeting detection (greeting_detector.py)
   │   └── If greeting: return canned response, skip RAG pipeline
   ├── Memory intent detection (memory_detector.py)
   │   └── If memory storage: update permanent_memory.json, skip RAG
   └── Translation (if Tamil Unicode detected)
       └── Call Gemini 1.5 Flash to translate Tamil → English

2. Schema Retrieval (schema_intelligence/hybrid_retriever.py)
   ├── Query ChromaDB with top_k=50 (force full context for ~25 tables)
   ├── Retrieve schema documents using semantic similarity
   ├── Return list of {text, metadata} with table/column descriptions

3. Planning Layer (planning_layer/planner_client.py)
   ├── Load permanent memory from persistent_memory.json
   ├── Inject memory constraints into system prompt
   ├── Call Gemini 1.5 Flash with:
   │   ├── System prompt + memory constraints
   │   ├── Schema context (formatted as text)
   │   ├── User question (in English)
   │   └── Response format: JSON (response_mime_type="application/json")
   ├── Parse JSON response into QueryPlan dict
   ├── Retry up to 3 times on JSON parse errors
   └── Return plan with {query_type, table, filters, columns, etc.}

4. Validation Layer (validation_layer/plan_validator.py)
   ├── Validate JSON structure against plan_schema.json (jsonschema)
   ├── Check table exists in DuckDB (list_tables())
   ├── Normalize column names (case-insensitive matching)
   ├── Validate all columns exist in table schema
   ├── Validate filter values match column types (numeric vs string)
   ├── Enforce query type-specific rules:
   │   ├── lookup: must have LIMIT 1, must have filters
   │   ├── extrema_lookup: must have order_by, LIMIT 1
   │   ├── rank: must have order_by
   │   ├── aggregation_on_subset: must have aggregation_function + column
   └── Raise ValueError if any validation fails

5. Execution Layer
   ├── SQL Compilation (execution_layer/sql_compiler.py)
   │   ├── Template-based compilation (no LLM)
   │   ├── Build SELECT clause (columns or metrics)
   │   ├── Build WHERE clause with flexible name matching:
   │   │   └── Handles spelling variations (ksh↔kch, sh↔ch)
   │   ├── Build GROUP BY, ORDER BY, LIMIT clauses
   │   └── Return SQL string
   ├── Execution (execution_layer/executor.py)
   │   ├── Create DuckDBManager (connects to latest.duckdb)
   │   ├── Execute SQL query
   │   ├── Run sanity checks (empty results allowed for filter/lookup)
   │   └── Return pandas DataFrame with results

6. Explanation Layer (explanation_layer/explainer_client.py)
   ├── Detect language of original question (Tamil Unicode check)
   ├── Load permanent memory and inject into system prompt
   ├── Call Gemini 2.0 Flash Exp with:
   │   ├── Result context (row_count, columns, data_sample)
   │   ├── Query plan metadata (query_type, table, filters)
   │   ├── Original question
   │   └── Language instruction (respond in detected language)
   ├── Generate natural language explanation
   └── Fallback to simple explanation if LLM fails

7. Post-Processing Layer
   ├── If Tamil query: translate explanation English → Tamil
   │   └── Gemini enforces number-to-words conversion for TTS
   ├── Convert DataFrame to list of dicts (JSON serializable)
   └── Build ProcessQueryResponse

8. Return Response
   └── {success, explanation, data, plan, schema_context, data_refreshed}
```

**Query Plan Schema**: Supports 7 query types:
- `metric`: Aggregations (SUM, AVG, COUNT) with optional GROUP BY
- `lookup`: Find single row by filters (LIMIT 1)
- `filter`: Multiple rows matching criteria
- `extrema_lookup`: MIN/MAX with ordering (LIMIT 1)
- `rank`: Ordered list of results
- `list`: Show all rows (with LIMIT)
- `aggregation_on_subset`: Aggregate over filtered/ordered subset (e.g., AVG of top 5)

#### 3. Audio Transcription (`POST /api/transcribe`)

**Flow**:
```
1. Receive audio blob (WebM/Opus from browser MediaRecorder)
2. Save to temporary file (.wav extension)
3. Call utils/voice_utils.py:transcribe_audio()
   ├── Initialize ElevenLabs client with API key
   ├── Call speech_to_text.convert() with:
   │   ├── Model: scribe_v2 (latest, most accurate)
   │   └── Language: en (English)
   └── Extract transcribed text from response
4. Delete temporary file
5. Return TranscribeResponse {success, text}
```

#### 4. Text-to-Speech (`POST /api/text-to-speech`)

**Flow**:
```
1. Receive JSON {text, voice_id}
2. Call utils/voice_utils.py:text_to_speech()
   ├── Detect if Tamil text (Unicode range \u0B80-\u0BFF)
   ├── Select model based on language:
   │   ├── Tamil: eleven_multilingual_v2 (better pronunciation)
   │   └── English: eleven_turbo_v2_5 (lower latency)
   ├── Call ElevenLabs text_to_speech.convert()
   ├── Collect audio chunks from stream
   └── Return audio bytes (MP3 format)
3. Return audio as HTTP Response with media_type="audio/mpeg"
```

### Data Storage and Persistence

#### DuckDB (data_sources/snapshots/latest.duckdb)
- **Purpose**: In-memory SQL analytics engine
- **Schema**: Each DetectedTable becomes a DuckDB table
- **Persistence**: Snapshot saved to disk, loaded on startup
- **Rebuild Triggers**: Dataset load, sheet hash changes
- **Connection**: Singleton per request via DuckDBManager

#### ChromaDB (schema_store/)
- **Purpose**: Semantic search over schema descriptions
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (HuggingFace, local)
- **Documents**: Table schemas, column descriptions, metric definitions
- **Metadata**: `{type: "table"|"metric", table, metric, source_id}`
- **Rebuild Triggers**: Dataset load, sheet changes
- **Persistence**: PersistentClient with disk storage

#### Permanent Memory (data_sources/persistent_memory.json)
- **Purpose**: Store user preferences and bot identity
- **Schema**: `{user_preferences: {address_as}, bot_identity: {name}, meta: {created_at, last_updated}}`
- **Access**: Loaded on every query, injected into LLM system prompts
- **Updates**: Explicit user commands detected by memory_detector.py
- **Atomic Writes**: Temp file + rename for safety

#### Sheet Registry (data_sources/snapshots/sheet_state.json)
- **Purpose**: Track sheet-level hashes for change detection
- **Schema**: `{spreadsheet_id, sheets: {sheet_name: {hash, last_synced, table_count, source_id}}}`
- **Updates**: After successful dataset load
- **Change Detection**: SHA-256 hash comparison

### Change Detection Mechanism

**File**: `data_sources/gsheet/change_detector.py`

**Strategy**: Sheet-level atomic hash comparison

**Algorithm**:
```
1. Compute SHA-256 hash of raw sheet data (before table detection)
2. Load previous hashes from sheet_state.json
3. Compare hashes for each sheet:
   ├── New sheet → mark as changed
   ├── Hash mismatch → mark as changed
   ├── Hash match → unchanged
   └── Missing hash → mark as changed (first run)
4. Determine rebuild strategy:
   ├── Spreadsheet ID changed → full reset
   ├── First run (no registry) → full reset
   └── Some sheets changed → incremental rebuild
5. Return (needs_refresh: bool, full_reset: bool, changed_sheets: List[str])
6. If changes detected:
   ├── Full reset: Clear all ChromaDB, rebuild all DuckDB
   └── Incremental: Delete changed sheets from ChromaDB, rebuild only those
7. Update sheet_state.json with new hashes after successful rebuild
```

**Atomic Unit**: Sheet (not table). Any change to a sheet triggers rebuild of all tables from that sheet.

**Hash Versioning**: Hash includes version suffix (e.g., `_v3_force_numeric`) to force rebuilds when type inference logic changes.

### Translation Layer

**File**: `utils/translation.py`

**Model**: Gemini 1.5 Flash

**Pre-Process (Tamil → English)**:
```
1. Detect Tamil Unicode characters (\u0B80-\u0BFF)
2. Call Gemini with translation prompt:
   "Translate Tamil query to English for data analysis.
    Map months to English names. Output ONLY English translation."
3. Process query in English through RAG pipeline
```

**Post-Process (English → Tamil)**:
```
1. Generate explanation in English
2. Call Gemini with translation prompt:
   "Translate to Tamil. STRICT RULE: Convert ALL numbers to Tamil words.
    NO DIGITS ALLOWED."
3. Return Tamil explanation to user
```

**Special Handling**: Numbers converted to Tamil words (e.g., 6450 → ஆறாயிரத்து நானூற்று ஐம்பது) for better TTS pronunciation.

---

## Frontend Architecture (frontend/)

### Directory Structure

```
frontend/
├── src/
│   ├── app/                # Next.js App Router
│   │   ├── layout.tsx     # Root layout, theme provider
│   │   ├── page.tsx       # Entry point, auth routing
│   │   └── globals.css    # Global styles, Tailwind
│   ├── components/         # React components
│   │   ├── ChatScreen.tsx # Main chat interface (952 lines)
│   │   ├── MessageBubble.tsx # Message rendering
│   │   ├── DatasetConnection.tsx # Sheet URL input
│   │   ├── VoiceVisualizer.tsx # Audio waveform
│   │   ├── AuthScreen.tsx # Login screen
│   │   └── ui/            # Radix UI components (53 files)
│   ├── lib/
│   │   ├── hooks.ts       # State management (useAppState)
│   │   ├── types.ts       # TypeScript interfaces
│   │   └── utils.ts       # Utility functions
│   └── services/
│       └── api.ts         # Backend HTTP client
├── package.json           # Dependencies (Next.js 15.3.6, React 19)
└── next.config.ts         # Next.js configuration
```

### State Management (lib/hooks.ts)

**Hook**: `useAppState()`

**State Structure**:
```typescript
{
  auth: {isAuthenticated: boolean, username: string | null},
  messages: Message[],
  chatTabs: ChatTab[],
  activeChatId: string | null,
  config: {googleSheetUrl: string | null}
}
```

**Persistence**: All state persisted to `localStorage`:
- `kiwi_assistant_auth`: Auth state
- `kiwi_assistant_chat`: Current chat messages
- `kiwi_assistant_tabs`: All chat tabs with metadata
- `kiwi_assistant_config`: App configuration

**Key Operations**:
- `createNewChat()`: Create new chat tab, switch to it
- `switchChat(id)`: Switch active chat, load its messages
- `deleteChat(id)`: Remove chat tab, switch to remaining
- `setDatasetForChat(url, status, stats)`: Associate dataset with active chat
- `addMessage(content, role, metadata)`: Add message to active chat and update tab

**Initialization**: On mount, load all state from localStorage, set first tab as active.

### Multi-Chat Tab Architecture

**Design**: Each chat tab maintains independent state:
- **Messages**: Full conversation history
- **Dataset Context**: Google Sheets URL, connection status, detailed stats
- **Metadata**: Created/updated timestamps, title

**Isolation**: Switching chats loads that chat's messages and dataset context. Dataset connections are per-chat, not global. Each chat can connect to a different Google Sheet.

**UI Flow**:
```
1. User clicks "Your Chats" → Sidebar opens with chat list
2. User clicks "New Chat" → createNewChat(), empty state
3. User clicks existing chat → switchChat(id), loads messages
4. User connects dataset → setDatasetForChat(), stored in active chat only
5. User asks question → Uses active chat's dataset context
6. User switches chat → Previous chat's state preserved, new chat loaded
```

**Verification**: On component mount, if chat has dataset marked as "ready", re-call `api.loadDataset()` to verify backend has data loaded. Shows "Verifying..." state until confirmed.

### Voice Interaction Flow

**File**: `components/ChatScreen.tsx`

**Recording Flow**:
```
1. User clicks microphone button (handleVoiceToggle)
2. Check if dataset connected (required for voice)
3. Request browser microphone permission (navigator.mediaDevices.getUserMedia)
4. Create MediaRecorder with audio/webm;codecs=opus
5. Set up event handlers:
   ├── ondataavailable: Collect audio chunks
   └── onstop: Process recording
6. Start recording (recorder.start())
7. Auto-stop after 10 seconds (setTimeout)
8. On manual stop or timeout:
   ├── Stop all media tracks
   ├── Create audio blob from chunks
   ├── Set isProcessingVoice=true (loading UI)
   ├── Call api.transcribeAudio(blob)
   ├── Receive transcribed text
   ├── Enable voice mode (setIsVoiceMode(true))
   ├── Send text via handleSendMessage(text, shouldPlayTTS=true)
   └── Set isProcessingVoice=false
```

**TTS Playback Flow**:
```
1. Receive response from backend (ProcessQueryResponse)
2. Check if shouldPlayTTS flag is true
3. Call playTextToSpeech(explanation)
   ├── Set isSpeaking=true (UI indicator)
   ├── Fetch /api/text-to-speech with {text, voice_id}
   ├── Receive MP3 audio blob
   ├── Create blob URL (URL.createObjectURL)
   ├── Create Audio object from URL
   ├── Set up event handlers:
   │   ├── onended: Clean up, set isSpeaking=false
   │   └── onerror: Clean up, show error toast
   └── Play audio (audio.play())
4. Clean up blob URL on end (URL.revokeObjectURL)
```

**Voice State Management**:
- `isRecording`: Microphone actively capturing
- `isProcessingVoice`: Transcription in progress
- `isSpeaking`: TTS playback active
- `isVoiceMode`: Voice interaction mode enabled (triggers TTS for responses)
- `mediaRecorder`: MediaRecorder instance reference

**Voice ID**: Hardcoded to `OUBMjq0LvBjb07bhwD3H` (user's preferred ElevenLabs voice).

### API Service (services/api.ts)

**Base URL**: `process.env.NEXT_PUBLIC_API_BASE_URL` (default: `http://localhost:8000`)

**Methods**:

```typescript
api.loadDataset(url: string): Promise<LoadDataResponse>
  → POST /api/load-dataset
  → Body: {url}
  → Returns: {success, stats: {totalTables, totalRecords, sheetCount, 
              sheets, detectedTables}}

api.sendMessage(text: string): Promise<ProcessQueryResponse>
  → POST /api/query
  → Body: {text}
  → Returns: {success, explanation, data, plan, schema_context, 
              data_refreshed, is_greeting, is_memory_storage}

api.transcribeAudio(audioBlob: Blob): Promise<string>
  → POST /api/transcribe
  → Body: FormData with audio file
  → Returns: transcribed text string

api.checkAuth(): Promise<boolean>
  → GET /api/auth/check
  → Returns: authenticated status (always true, auth disabled)
```

**Error Handling**: All methods throw errors with backend error messages. Caught in components and displayed via toast notifications (sonner library).

### Dataset Connection Flow

**Component**: `DatasetConnection.tsx`

**Flow**:
```
1. User clicks dataset status button in header
2. Modal opens (Dialog component)
3. User pastes Google Sheets URL
4. Click "Connect Dataset" button
5. Validate URL format (basic check)
6. Set loading state (isConnecting=true)
7. Call api.loadDataset(url)
8. On success:
   ├── Extract stats from response
   ├── Call setDatasetForChat(url, 'ready', stats)
   ├── Display success toast with table count
   ├── Close modal
   └── Update header to show "Loaded Successfully"
9. On error:
   ├── Display error toast with message
   └── Keep modal open for retry
```

**Locking**: Once connected, dataset URL is locked for that chat (isLocked prop). User must create new chat to connect different dataset.

**Stats Display**: Shows totalTables, totalRecords, sheetCount, and list of sheet names.

### UI Component Hierarchy

```
ChatScreen (Main Interface)
├── Header
│   ├── "Your Chats" Button → Opens sidebar
│   ├── Dataset Status Button → Opens DatasetConnection modal
│   │   └── Shows "Loaded Successfully" | "Verifying..." | empty
│   ├── "Chat" Toggle → Switch voice/chat mode
│   └── User Dropdown → Settings, Profile, Logout
├── Sidebar (AnimatePresence, slides from left)
│   ├── "New Chat" Button
│   ├── Chat List (scrollable)
│   │   └── Chat Item (title, message count, delete button)
│   └── Overlay (click to close)
├── Main Content (AnimatePresence mode="wait")
│   ├── Voice Mode (default)
│   │   ├── Brand Header ("Hey, {username}")
│   │   ├── VoiceVisualizer (animated waveform)
│   │   ├── Microphone Button (record/stop)
│   │   └── Info Toggles (Query Plan, Data, Schema)
│   │       └── Expanded Content Area (JSON/table preview)
│   └── Chat Mode (toggle)
│       ├── Message List (scrollable, auto-scroll to bottom)
│       │   └── MessageBubble[] (user/assistant, with metadata)
│       └── ChatInput (text input + send button)
└── Modals
    ├── DatasetConnection (URL input, stats display)
    └── Settings (Theme selector: Light/Dark/System)
```

**Animations**: Framer Motion for smooth transitions between voice/chat modes, sidebar slide-in, message fade-in.

**Theme System**: `next-themes` provider with Tailwind dark mode classes. Theme persisted to localStorage.

---

## Data Flow Diagrams

### Complete Query Processing Pipeline

```
User Question (Voice/Text)
        │
        ├─[Voice]─→ Browser MediaRecorder ─→ WebM Blob
        │                                      │
        │                                      ▼
        │                              POST /api/transcribe
        │                                      │
        │                                      ▼
        │                              ElevenLabs Scribe v2 ─→ Text
        │
        ▼
[Pre-Processing Layer]
        │
        ├─→ Phonetic Corrections (hardcoded patterns)
        ├─→ Greeting Detection (regex patterns)
        │   └─→ If greeting: Return canned response, EXIT
        ├─→ Memory Detection (LLM-based intent parsing)
        │   └─→ If memory: Update JSON, return confirmation, EXIT
        └─→ Translation (if Tamil Unicode detected)
            └─→ Gemini 1.5 Flash ─→ English Text
                    │
                    ▼
        [Schema Retrieval Layer]
                    │
                    └─→ ChromaDB Query (top_k=50)
                        └─→ HuggingFace Embeddings
                            └─→ Schema Context (List[{text, metadata}])
                                    │
                                    ▼
                [Planning Layer]
                                    │
                                    ├─→ Load Permanent Memory (JSON)
                                    ├─→ Inject Memory into System Prompt
                                    └─→ Gemini 1.5 Flash (JSON mode)
                                        └─→ QueryPlan (JSON)
                                                │
                                                ▼
                        [Validation Layer]
                                                │
                                                ├─→ JSON Schema Validation
                                                ├─→ Table Existence Check (DuckDB)
                                                ├─→ Column Name Normalization
                                                ├─→ Column Existence Check
                                                ├─→ Filter Type Validation
                                                └─→ Query Type Rule Enforcement
                                                        │
                                                        ▼
                                [Execution Layer]
                                                        │
                                                        ├─→ SQL Compiler (Template-based)
                                                        │   └─→ SQL String
                                                        └─→ DuckDB Execute
                                                            └─→ pandas DataFrame
                                                                    │
                                                                    ▼
                                        [Explanation Layer]
                                                                    │
                                                                    ├─→ Detect Language
                                                                    ├─→ Load Memory
                                                                    └─→ Gemini 2.0 Flash Exp
                                                                        └─→ Explanation (English)
                                                                                │
                                                                                ▼
                                                        [Post-Processing Layer]
                                                                                │
                                                                                ├─[Tamil Query]─→ Gemini Translate
                                                                                │                 └─→ Tamil Explanation
                                                                                ├─→ DataFrame to JSON
                                                                                └─→ Build Response
                                                                                        │
                                                                                        ▼
                                                                                Response Object
                                                                                        │
                                                                                        ├─[Voice Mode]─→ POST /api/text-to-speech
                                                                                        │                 └─→ ElevenLabs TTS
                                                                                        │                     └─→ MP3 Audio
                                                                                        │                         └─→ Browser Audio API
                                                                                        │
                                                                                        ▼
                                                                                User (Text/Audio)
```

### Dataset Loading Pipeline

```
Google Sheets URL (Frontend Input)
        │
        ▼
POST /api/load-dataset
        │
        ▼
[Spreadsheet ID Extraction]
        │
        └─→ Regex Pattern Match (/spreadsheets/d/([a-zA-Z0-9-_]+))
                │
                ▼
        [Update Configuration]
                │
                └─→ Write to config/settings.yaml
                        │
                        ▼
                [Google Sheets API]
                        │
                        ├─→ Authenticate (Service Account OAuth2)
                        └─→ Fetch All Worksheets
                                │
                                ▼
                        [For Each Sheet]
                                │
                                ├─→ Fetch Raw Data (all cells)
                                ├─→ Compute SHA-256 Hash (change detection)
                                ├─→ Detect Tables (custom_detector.py)
                                │   └─→ Split by empty rows, identify headers
                                ├─→ Infer Types (connector.py)
                                │   ├─→ Numeric: >30% numbers → INT64/FLOAT
                                │   ├─→ Boolean: True/False patterns → BOOL
                                │   ├─→ Date: >50% parseable → DATETIME
                                │   └─→ String: Default
                                └─→ Combine Date + Time Columns
                                    └─→ Create Timestamp Column
                                            │
                                            ▼
                                [DuckDB Snapshot]
                                            │
                                            ├─→ Create In-Memory Connection
                                            ├─→ Register Tables (table_id as name)
                                            └─→ Persist to latest.duckdb
                                                    │
                                                    ▼
                                        [ChromaDB Rebuild]
                                                    │
                                                    ├─→ Clear Collection (delete all)
                                                    ├─→ Generate Schema Documents
                                                    │   └─→ Table/column descriptions
                                                    ├─→ Embed (HuggingFace local model)
                                                    └─→ Store in schema_store/
                                                            │
                                                            ▼
                                                [Update Sheet Registry]
                                                            │
                                                            └─→ Save Hashes to sheet_state.json
                                                                    │
                                                                    ▼
                                                        [Build Response]
                                                                    │
                                                                    └─→ LoadDataResponse
                                                                        └─→ {success, stats}
                                                                                │
                                                                                ▼
                                                                        Frontend (Display Stats)
```

---

## Configuration and Environment

### Backend Configuration (config/settings.yaml)

```yaml
google_sheets:
  credentials_path: credentials/service_account.json  # OAuth2 service account
  spreadsheet_id: 1mRcD-apkPVAUU_HPZ8KBzMxdct7zdKMp2qPoivSBpl4  # Updated dynamically

llm:
  provider: gemini
  model: gemini-1.5-flash                            # Planning model
  temperature: 0.0                                   # Deterministic output
  max_retries: 3                                     # API retry attempts
  api_key_env: GEMINI_API_KEY                        # Environment variable name

duckdb:
  snapshot_path: data_sources/snapshots/latest.duckdb

schema_intelligence:
  embedding_model: text-embedding-3-large            # Not used (HuggingFace instead)
  top_k: 5                                           # Overridden to 50 in code
```

### Environment Variables

**Backend (.env)**:
```bash
GEMINI_API_KEY=<your-gemini-api-key>                # Required for planning/explanation
ELEVENLABS_API_KEY=<your-elevenlabs-api-key>        # Required for voice features
SUPABASE_URL=<your-supabase-url>                    # Optional (auth disabled)
SUPABASE_ANON_KEY=<your-supabase-anon-key>          # Optional (auth disabled)
SUPABASE_SERVICE_KEY=<your-supabase-service-key>    # Optional (auth disabled)
ENABLE_AUTH=false                                    # Auth disabled by default
```

**Frontend (.env.local)**:
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000       # Backend URL
```

**Google Sheets Service Account**:
- Place JSON file at `kiwi-rag/credentials/service_account.json`
- Grant service account email access to target Google Sheets
- File is gitignored for security

---

## Running the System

### Backend

```bash
cd kiwi-rag
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python -m uvicorn api.main:app --reload --port 8000
```

**Startup Sequence**:
1. Load environment variables from .env
2. Initialize FastAPI app with CORS
3. Print available endpoints
4. Listen on http://0.0.0.0:8000

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with backend URL
npm run dev
```

**Startup Sequence**:
1. Next.js development server starts
2. Turbopack compilation
3. Listen on http://localhost:3000
4. Hot reload enabled

---

## Extension Points

### Adding New Query Types

**Steps**:
1. Update `planning_layer/plan_schema.json` with new query type definition
2. Add validation rules in `validation_layer/plan_validator.py:validate_plan()`
3. Implement SQL compilation in `execution_layer/sql_compiler.py:compile_sql()`
4. Update frontend `lib/types.ts:QueryPlan` interface
5. Update planner system prompt in `planning_layer/planner_prompt.py`

### Adding New Data Sources

**Current**: Google Sheets only

**To Add** (e.g., CSV, PostgreSQL, Airtable):
1. Create new connector in `data_sources/<source>/connector.py`
2. Implement `fetch_data()` returning `DetectedTable[]` structure
3. Update `snapshot_loader.py` to handle new source type
4. Update frontend to accept new connection types in DatasetConnection.tsx

**Key Constraint**: Must return pandas DataFrame in `DetectedTable.dataframe` field.

### Adding New Languages

**Current**: English, Tamil

**To Add** (e.g., Hindi, Spanish):
1. Update `utils/translation.py` with language detection and translation prompts
2. Add language-specific greeting patterns to `utils/greeting_detector.py`
3. Update `explanation_layer/explainer_client.py` to detect new language
4. Test end-to-end flow with sample queries

**Key Constraint**: Gemini must support the language for translation.

### Adding Custom Metrics

**File**: `analytics_engine/metric_registry.py`

**Steps**:
1. Define metric in `MetricRegistry.metrics` dict:
   ```python
   "total_revenue": {
       "sql": "SUM(revenue)",
       "base_table": "sales",
       "description": "Total revenue across all sales"
   }
   ```
2. Metric automatically available in queries (no code changes needed)
3. Update planner prompt to include new metric in examples

**Validation**: Metrics validated against `base_table` in `validation_layer/plan_validator.py`.

---

## Performance Characteristics

### Backend Performance

**Dataset Loading**:
- **Time**: ~5-10 seconds for 25 tables, 1300 rows
- **Bottleneck**: Google Sheets API fetch (~3s), table detection (~2s), embedding generation (~3s)
- **Optimization**: Incremental updates via hash-based change detection

**Query Processing**:
- **Time**: ~2-5 seconds end-to-end
- **Breakdown**:
  - Schema retrieval: ~200ms (ChromaDB local query)
  - Planning: ~1-2s (Gemini API network call)
  - Validation: ~50ms (local checks)
  - Execution: ~100ms (DuckDB in-memory)
  - Explanation: ~1-2s (Gemini API network call)
- **Bottleneck**: LLM API calls (planning + explanation account for 80% of latency)

**Memory Usage**:
- **DuckDB**: ~100MB for 1300 rows (in-memory tables)
- **ChromaDB**: ~50MB for 25 tables (embeddings + metadata)
- **Total Process**: ~500MB resident memory

### Frontend Performance

**Initial Load**: ~1-2 seconds (Next.js hydration, React 19)
**Chat Rendering**: ~50ms per message (Framer Motion animations)
**Voice Recording**: Real-time, no perceptible lag
**TTS Playback**: Starts within 500ms of receiving response

---

## Troubleshooting

### Common Issues

**"No data found for the requested criteria"**
- **Cause**: Query plan generated incorrect filters or table name
- **Debug**: Check `schema_context` in response, verify table/column names in DuckDB
- **Fix**: Improve schema descriptions in `embedding_builder.py`, increase top_k

**"Table does not exist"**
- **Cause**: DuckDB snapshot not loaded or table name mismatch
- **Debug**: Check `data_sources/snapshots/latest.duckdb` exists, list tables in DuckDB
- **Fix**: Reload dataset, verify table detection logic in `table_detection.py`

**"Failed to parse JSON from LLM response"**
- **Cause**: Gemini returned invalid JSON (rare with JSON mode)
- **Debug**: Check `planner_client.py` logs for raw response text
- **Fix**: Improve planner prompt clarity, increase `max_retries` in settings.yaml

**"Empty transcription result"**
- **Cause**: No speech detected, microphone permission denied, or audio too quiet
- **Debug**: Check browser console for microphone errors, verify audio blob size
- **Fix**: Grant microphone permission, speak louder, check ElevenLabs API key

**"ChromaDB ONNX error"**
- **Cause**: Attempting to use ONNX embeddings (explicitly disabled)
- **Debug**: Check `chromadb_client.py` initialization, verify sentence-transformers installed
- **Fix**: Ensure `sentence-transformers>=2.2.0` in requirements.txt, using HuggingFace embeddings

---

## Dependencies

### Backend (requirements.txt)

**Core**:
- `fastapi>=0.104.0`: REST API framework
- `uvicorn[standard]>=0.24.0`: ASGI server
- `google-generativeai>=0.3.0`: Gemini API client
- `duckdb>=0.9.0`: In-memory SQL analytics
- `chromadb>=0.4.0`: Vector database
- `sentence-transformers>=2.2.0`: HuggingFace embeddings

**Data Processing**:
- `pandas>=2.0.0`: DataFrame manipulation
- `numpy>=1.24.0`: Numerical operations
- `gspread>=5.0.0`: Google Sheets API
- `google-auth>=2.0.0`: OAuth2 authentication

**Voice**:
- `elevenlabs>=1.0.0`: STT/TTS API client

**Utilities**:
- `pyyaml>=6.0`: Configuration parsing
- `jsonschema>=4.0.0`: JSON validation
- `python-dotenv>=1.0.0`: Environment variables
- `langdetect>=1.0.9`: Language detection

### Frontend (package.json)

**Core**:
- `next@15.3.6`: React framework (App Router)
- `react@19.0.0`: UI library
- `typescript@^5`: Type safety

**UI**:
- `@radix-ui/*`: Headless accessible components
- `framer-motion@^12.23.24`: Declarative animations
- `tailwindcss@^4`: Utility-first CSS
- `lucide-react@^0.552.0`: Icon library

**State/Forms**:
- `next-themes@^0.4.6`: Theme management
- `sonner@^2.0.6`: Toast notifications
- `react-hook-form@^7.60.0`: Form handling
- `zod@^4.1.12`: Schema validation

---

## License and Contributing

**License**: Not specified in codebase

**Contributing**: No CONTRIBUTING.md present

**Recommended**:
1. Add LICENSE file (MIT/Apache 2.0)
2. Add CONTRIBUTING.md with code style guidelines, PR process, testing requirements
3. Add CODEOWNERS for review assignments

---

## Contact and Support

**Repository**: Not specified in codebase

**Issues**: Create GitHub issue for bugs/feature requests

**Documentation**: This README serves as primary technical documentation
