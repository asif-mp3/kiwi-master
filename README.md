# Thara.ai - Intelligent Data Assistant

Thara.ai is a voice-enabled AI data assistant that transforms how users interact with their business data. Instead of writing complex SQL queries or navigating through dashboards, users can simply ask questions in natural language (English or Tamil) and receive instant, accurate answers with visualizations.

---

## Table of Contents

1. [Overview](#overview)
2. [How It Works - The Complete Flow](#how-it-works---the-complete-flow)
3. [Architecture Deep Dive](#architecture-deep-dive)
4. [Frontend System](#frontend-system)
5. [Backend System](#backend-system)
6. [Data Processing Pipeline](#data-processing-pipeline)
7. [Query Processing Pipeline](#query-processing-pipeline)
8. [Intelligence Layers](#intelligence-layers)
9. [Supported Query Types](#supported-query-types)
10. [Key Features](#key-features)
11. [Tech Stack](#tech-stack)
12. [Setup Guide](#setup-guide)
13. [Deployment](#deployment)

---

## Overview

Thara.ai bridges the gap between raw data and actionable insights. It allows non-technical users to query their business data (stored in Google Sheets, Excel files, or Google Drive folders) using conversational language. The system understands context, remembers preferences, handles follow-up questions, and presents results with appropriate visualizations.

**Core Capabilities:**
- Natural language query understanding (English and Tamil)
- Voice input and voice output (text-to-speech)
- Automatic data visualization (charts, tables)
- Smart table selection from multiple data sources
- Self-healing query execution
- Conversation memory and context tracking
- Data export (PDF and Excel)

---

## How It Works - The Complete Flow

When a user asks a question like "What were total sales last month?", the following happens:

### Step 1: Input Reception
The user can type their question or speak it. If speaking, the audio is transcribed using ElevenLabs' speech-to-text service. The system also detects if the input is in Tamil and translates it to English for processing.

### Step 2: Intent Classification
The system determines what type of request this is:
- **Greeting**: "Hi", "Hello" → Returns a friendly greeting
- **Memory Request**: "Remember that I prefer Chennai data" → Stores user preference
- **Schema Inquiry**: "What data do you have?" → Explains available tables
- **Data Query**: "Total sales last month" → Proceeds to query processing
- **Off-topic**: "What's the weather?" → Politely redirects to data questions

### Step 3: Entity Extraction
The system extracts meaningful entities from the question:
- **Time references**: "last month", "Q3 2025", "yesterday"
- **Locations**: "Chennai", "Tamil Nadu", "Branch 42"
- **Categories**: "Electronics", "Sarees"
- **Metrics**: "sales", "revenue", "profit", "attendance"

### Step 4: Table Routing
This is where intelligent table selection happens. The system:
1. Uses ChromaDB vector similarity to find semantically relevant tables
2. Applies an LLM (Gemini) to make the final table selection
3. Considers factors like: Does the table have a Date column? Is it aggregated data or raw transactions? Does it contain the requested metrics?

### Step 5: Query Planning
An LLM generates a structured execution plan containing:
- Query type (metric, comparison, trend, rank, filter, etc.)
- Target table and columns
- Filters to apply
- Aggregations needed
- Sorting and limiting

### Step 6: Plan Validation
The plan is validated and corrected:
- Column names are verified against actual schema
- SKU/ID columns are replaced with human-readable alternatives
- Date columns are validated
- Filter values are corrected (fuzzy matching)

### Step 7: SQL Compilation & Execution
The plan is compiled into DuckDB SQL and executed. If the query fails, the self-healing mechanism:
1. Analyzes the error
2. Attempts automatic fixes (column name corrections, type casting)
3. Retries up to 3 times

### Step 8: Advanced Analytics
For complex query types, additional analysis is performed:
- **Trends**: Calculates direction, slope, percentage change, detects spikes
- **Comparisons**: Computes differences, percentage changes, winners
- **Rankings**: Formats top/bottom N results

### Step 9: Natural Language Explanation
The LLM generates a conversational response explaining the results in a friendly, professional tone. The response adapts to the user's language (Tamil responses for Tamil input).

### Step 10: Visualization Generation
The system automatically determines the best chart type:
- **Bar charts**: For comparisons, rankings, categorical data
- **Line charts**: For trends over time
- **Pie charts**: For percentage breakdowns
- **Tables**: For detailed listings

### Step 11: Response Delivery
The complete response includes:
- Natural language explanation
- Data visualization (chart)
- Raw data table (expandable)
- Export options (PDF, Excel)
- Voice playback option

---

## Architecture Deep Dive

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USER INTERFACE                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Voice Input  │  │ Text Input   │  │ Response Display         │  │
│  │ (Microphone) │  │ (Keyboard)   │  │ (Chat + Charts + Table)  │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Next.js)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ ChatScreen   │  │ MessageBubble│  │ DataChart                │  │
│  │ (Main UI)    │  │ (Messages)   │  │ (Visualizations)         │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │ HTTP/REST API
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      API LAYER (api/)                        │   │
│  │  • Request validation  • Authentication  • Rate limiting     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                 │                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   PLANNING LAYER (planning_layer/)           │   │
│  │  • Table Router (ChromaDB + LLM selection)                   │   │
│  │  • Entity Extractor (dates, locations, categories)           │   │
│  │  • Planner Client (LLM-based query planning)                 │   │
│  │  • LLM Table Selector (intelligent table choice)             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                 │                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 VALIDATION LAYER (validation_layer/)         │   │
│  │  • Plan Validator (column verification, SKU replacement)     │   │
│  │  • Schema matching  • Filter value correction                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                 │                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                 EXECUTION LAYER (execution_layer/)           │   │
│  │  • SQL Compiler (plan → DuckDB SQL)                          │   │
│  │  • Executor (runs queries)                                   │   │
│  │  • Query Healer (self-healing on errors)                     │   │
│  │  • Advanced Executor (trends, comparisons, percentages)      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                 │                                   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                EXPLANATION LAYER (explanation_layer/)        │   │
│  │  • Explainer Client (LLM-generated natural language)         │   │
│  │  • Thara Personality (friendly, professional tone)           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    DATA LAYER                                │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │   │
│  │  │  DuckDB     │  │  ChromaDB   │  │  Data Connectors    │  │   │
│  │  │  (Analytics)│  │  (Vectors)  │  │  (Sheets/Drive/CSV) │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Frontend System

### Core Components

**ChatScreen** (`components/ChatScreen.tsx`)
The main chat interface that handles:
- Message input (text and voice)
- Message history display
- Session management
- Voice recording and playback controls

**MessageBubble** (`components/MessageBubble.tsx`)
Displays individual messages with:
- User messages (right-aligned, purple)
- Assistant messages (left-aligned, with Thara avatar)
- Action buttons (play audio, copy, view query plan)
- Expandable data table with export options
- Embedded visualizations

**DataChart** (`components/DataChart.tsx`)
Renders visualizations using Recharts:
- Bar charts for comparisons
- Line charts for trends
- Pie charts for distributions
- Responsive sizing with animations

**QueryPlanViewer** (`components/QueryPlanViewer.tsx`)
Debug tool showing the generated query plan:
- Selected table
- Query type
- Filters applied
- Columns used

### State Management
- React hooks for local component state
- Session-based chat history
- Real-time voice status tracking
- Message metadata (plans, visualizations, raw data)

---

## Backend System

### API Layer (`api/`)

**Main Endpoints:**
- `POST /api/query` - Process a natural language query
- `POST /api/load-dataset` - Load data from Google Sheets/Drive
- `POST /api/transcribe` - Convert voice to text
- `POST /api/text-to-speech` - Convert text to voice
- `GET /api/health` - Health check
- `GET /api/debug/routing` - Debug table routing
- `GET /api/debug/profiles` - View table profiles

**Services** (`api/services.py`)
Orchestrates the entire query pipeline:
1. Receives the query
2. Detects query type (greeting, memory, data query)
3. Coordinates all processing layers
4. Assembles the final response

### Planning Layer (`planning_layer/`)

**Table Router** (`table_router.py`)
Finds the most relevant table for a query:
1. Uses ChromaDB to find semantically similar tables
2. Scores tables based on column relevance
3. Returns confidence scores

**LLM Table Selector** (`llm_table_selector.py`)
Makes the final table selection using Gemini:
- Builds rich context about each table
- Marks tables with/without date columns
- Identifies aggregated vs. transaction-level data
- Returns selection with reasoning

**Entity Extractor** (`entity_extractor.py`)
Extracts structured entities from queries:
- Date ranges (relative and absolute)
- Location names
- Category names
- Metric names

**Planner Client** (`planner_client.py`)
Generates structured query plans:
- Calls Gemini with the planner prompt
- Returns JSON plan with query type, table, filters, metrics

### Validation Layer (`validation_layer/`)

**Plan Validator** (`plan_validator.py`)
Ensures plan correctness:
- Validates column names exist in schema
- Replaces SKU/ID columns with human-readable alternatives
- Corrects filter values using fuzzy matching
- Validates date column selection for trends

### Execution Layer (`execution_layer/`)

**SQL Compiler** (`sql_compiler.py`)
Converts query plans to DuckDB SQL:
- Handles different query types
- Applies filters, groupings, aggregations
- Generates appropriate SELECT statements

**Executor** (`executor.py`)
Runs SQL queries against DuckDB:
- Executes compiled SQL
- Returns results as DataFrames
- Handles errors gracefully

**Query Healer** (`query_healer.py`)
Self-healing mechanism for failed queries:
- Analyzes SQL errors
- Attempts automatic fixes
- Retries with corrected SQL
- Reports healing attempts

**Advanced Executor** (`advanced_executor.py`)
Handles complex analytics:
- **Trend Analysis**: Direction, slope, spikes, min/max dates
- **Comparisons**: Absolute and percentage differences
- **Percentage Calculations**: Distribution analysis
- **Rankings**: Top/bottom N with proper formatting

### Explanation Layer (`explanation_layer/`)

**Explainer Client** (`explainer_client.py`)
Generates natural language responses:
- Uses Gemini to explain results
- Applies Thara personality (friendly, professional)
- Handles different response types (trends, comparisons, etc.)
- Supports Tamil language responses

### Schema Intelligence (`schema_intelligence/`)

**ChromaDB Client** (`chromadb_client.py`)
Vector store for semantic search:
- Stores table descriptions as embeddings
- Enables similarity-based table finding
- Persists across sessions

**Data Profiler** (`data_profiler.py`)
Analyzes table structure:
- Identifies column types (dimension, metric, date)
- Detects unique values
- Calculates statistics
- Generates semantic descriptions

**Profile Store** (`profile_store.py`)
Caches table profiles:
- Stores profiling results to disk
- Enables fast lookups
- Tracks known entities (locations, categories)

### Data Sources (`data_sources/`)

**Google Sheets Connector** (`gsheet/connector.py`)
Loads data from Google Sheets:
- Authenticates with service account
- Fetches all sheets from a spreadsheet
- Handles multiple tabs

**Google Drive Folder Connector** (`connectors/gdrive_folder_connector.py`)
Loads data from Drive folders:
- Downloads Excel/CSV files
- Supports public folder links
- Caches downloaded files

**Snapshot Loader** (`gsheet/snapshot_loader.py`)
Manages DuckDB snapshots:
- Creates in-memory tables
- Handles incremental updates
- Manages table lifecycle

### Utilities (`utils/`)

**Translation** (`translation.py`)
Multi-language support:
- Detects Tamil input
- Translates to English for processing
- Translates responses back to Tamil

**Voice Utils** (`voice_utils.py`)
Voice processing:
- ElevenLabs speech-to-text
- Audio format handling

**Memory Detector** (`memory_detector.py`)
User preference memory:
- Detects "remember" requests
- Stores preferences per user
- Applies stored context to queries

**Query Context** (`query_context.py`)
Conversation tracking:
- Maintains query history
- Supports follow-up questions
- Handles corrections

**Personality** (`personality.py`)
Thara's personality definition:
- Friendly, professional tone
- Avoids robotic responses
- Contextual greetings

**Visualization** (`visualization.py`)
Chart type determination:
- Analyzes query type and data
- Selects appropriate chart
- Formats data for Recharts

---

## Data Processing Pipeline

### Initial Data Load

1. **User provides data source**
   - Google Sheet URL
   - Google Drive folder URL
   - Excel/CSV file upload

2. **Data extraction**
   - Sheets: Uses gspread to fetch all tabs
   - Drive: Downloads files via public link parsing
   - Files: Reads with pandas

3. **Table creation**
   - Each sheet/file becomes a DuckDB table
   - Column types are inferred
   - Tables are named with source prefix

4. **Profiling**
   - Each table is analyzed
   - Column roles identified (date, dimension, metric)
   - Sample values collected
   - Statistics computed

5. **Indexing**
   - Table descriptions stored in ChromaDB
   - Enables semantic search
   - Profiles cached to disk

### Incremental Updates

The system detects when source data changes:
- Compares checksums
- Only reloads changed tables
- Updates profiles and vectors

---

## Query Processing Pipeline

### Detailed Step-by-Step

```
User Query: "Show me sales trend by category for last 3 months"
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: PREPROCESSING                                           │
│ • Tamil detection → No                                          │
│ • Greeting detection → No                                       │
│ • Memory detection → No                                         │
│ • Schema inquiry → No                                           │
│ • Proceed to data query processing                              │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: ENTITY EXTRACTION                                       │
│ • Time: "last 3 months" → 2025-11-01 to 2026-02-01             │
│ • Dimension: "category"                                         │
│ • Metric: "sales"                                               │
│ • Analysis type: "trend"                                        │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: TABLE ROUTING                                           │
│ • ChromaDB similarity search → Top 5 candidates                 │
│ • LLM analysis of candidates                                    │
│ • Selection: "Daily_Sales_Transactions"                         │
│ • Reason: Has Date column, Category column, Sale_Amount         │
│ • Confidence: 95%                                               │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: QUERY PLANNING                                          │
│ • Query type: "trend"                                           │
│ • Table: "Daily_Sales_Transactions"                             │
│ • Metric: "Sale_Amount" (SUM)                                   │
│ • Date column: "Date"                                           │
│ • Group by: "Category"                                          │
│ • Time unit: "month"                                            │
│ • Filters: Date >= 2025-11-01                                   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: PLAN VALIDATION                                         │
│ • Column "Sale_Amount" exists → ✓                               │
│ • Column "Date" exists → ✓                                      │
│ • Column "Category" exists → ✓                                  │
│ • No SKU columns in group_by → ✓                                │
│ • Plan validated successfully                                   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: SQL COMPILATION                                         │
│ SELECT                                                          │
│   DATE_TRUNC('month', Date) as period,                         │
│   Category,                                                     │
│   SUM(Sale_Amount) as value                                     │
│ FROM Daily_Sales_Transactions                                   │
│ WHERE Date >= '2025-11-01'                                      │
│ GROUP BY DATE_TRUNC('month', Date), Category                   │
│ ORDER BY period                                                 │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: EXECUTION                                               │
│ • Execute SQL in DuckDB                                         │
│ • Result: 30 rows (10 categories × 3 months)                   │
│ • Execution time: 45ms                                          │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: ADVANCED ANALYTICS                                      │
│ For each category:                                              │
│ • Calculate trend direction (increasing/decreasing/stable)      │
│ • Compute percentage change                                     │
│ • Identify spikes (values > avg + 1.5×std_dev)                 │
│ • Find max/min dates                                            │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 9: EXPLANATION GENERATION                                  │
│ "Here's the sales trend by category over the last 3 months:    │
│  Electronics showed strong growth (+15%), while Clothing        │
│  remained stable. Sarees had an unusual spike in December,      │
│  reaching ₹4.5L, likely due to festive season."                │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 10: VISUALIZATION                                          │
│ • Query type: trend + grouped → Multi-line chart               │
│ • X-axis: Month                                                 │
│ • Y-axis: Sales Amount                                          │
│ • Series: One line per category                                 │
│ • Colors: Auto-assigned                                         │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│ FINAL RESPONSE                                                  │
│ {                                                               │
│   "text": "Here's the sales trend...",                         │
│   "visualization": { type: "line", data: [...] },              │
│   "data": [ {month: "Nov", Electronics: 100K, ...}, ... ],     │
│   "plan": { query_type: "trend", ... },                        │
│   "confidence": 95                                              │
│ }                                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Intelligence Layers

### 1. Semantic Understanding
- **ChromaDB embeddings** enable finding tables by meaning, not just keywords
- "revenue" matches tables with "Sale_Amount" column
- "attendance" matches HR/employee tables

### 2. LLM-Based Planning
- **Gemini** understands query intent
- Generates structured plans, not raw SQL
- Handles ambiguous queries intelligently

### 3. Schema Awareness
- System knows column types and roles
- Distinguishes dates from IDs
- Understands aggregated vs. raw data

### 4. Self-Healing Execution
- Automatically fixes common SQL errors
- Column name typos corrected
- Type mismatches handled

### 5. Contextual Memory
- Remembers user preferences
- Handles follow-up questions
- Resolves references ("top category" → actual name)

---

## Supported Query Types

| Type | Description | Example |
|------|-------------|---------|
| **Metric** | Single aggregated value | "Total sales?" |
| **Comparison** | Compare two values | "Chennai vs Mumbai sales?" |
| **Trend** | Change over time | "Sales trend this quarter?" |
| **Grouped Trend** | Trend by dimension | "Sales trend by category?" |
| **Rank** | Top/bottom N items | "Top 5 products by revenue?" |
| **Filter** | List with conditions | "Sales above 10,000?" |
| **Percentage** | Distribution analysis | "Sales by payment mode?" |
| **Lookup** | Find specific record | "Sales for product X?" |
| **List** | Show all records | "Show all branches" |

---

## Key Features

### Voice Interface
- **Input**: Speak questions using the microphone
- **Output**: Hear responses via ElevenLabs TTS
- **Language**: Supports English and Tamil

### Smart Visualizations
- Automatic chart type selection
- Responsive design
- Interactive tooltips
- Export to image

### Data Export
- **Excel**: Full data with formatting
- **PDF**: Printable report with branding

### Query Plan Transparency
- See which table was selected
- Understand filters applied
- Debug query issues

### Tamil Language Support
- Type or speak in Tamil
- Responses in Tamil
- Translation happens seamlessly

### User Preferences
- "Remember I'm interested in Chennai data"
- Preferences applied to future queries
- Per-user memory storage

### Follow-up Questions
- "What about last month?"
- "Break that down by category"
- Context preserved across turns

---

## Tech Stack

### Frontend
| Technology | Purpose |
|------------|---------|
| Next.js 15 | React framework with App Router |
| React 19 | UI components |
| Tailwind CSS 4 | Styling |
| Framer Motion | Animations |
| Recharts | Data visualizations |
| Radix UI | Accessible components |
| Lucide Icons | Icon library |
| XLSX | Excel export |
| jsPDF | PDF export |

### Backend
| Technology | Purpose |
|------------|---------|
| FastAPI | REST API framework |
| Python 3.11+ | Backend language |
| DuckDB | In-memory analytics database |
| ChromaDB | Vector store for semantic search |
| Sentence Transformers | Text embeddings |
| Google Gemini | LLM for planning/explanation |
| ElevenLabs | Voice STT/TTS |
| Pandas | Data manipulation |
| gspread | Google Sheets API |

### Infrastructure
| Service | Purpose |
|---------|---------|
| Vercel | Frontend hosting |
| Hugging Face Spaces | Backend hosting |
| Supabase | Authentication |
| Google Cloud | Translation API |

---

## Setup Guide

### Prerequisites
- Python 3.11 or higher
- Node.js 18 or higher
- API Keys:
  - Gemini API Key (Google AI Studio)
  - ElevenLabs API Key
  - Google Service Account JSON (for Sheets access)

### Backend Setup

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
GEMINI_API_KEY=your-gemini-key
ELEVENLABS_API_KEY=your-elevenlabs-key
```

Place Google service account JSON at `backend/credentials/service_account.json`

Start the backend:
```bash
python -m uvicorn api.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:
```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Start the frontend:
```bash
npm run dev
```

Open http://localhost:3000

---

## Deployment

### Frontend (Vercel)
1. Connect GitHub repository to Vercel
2. Set environment variables
3. Deploy automatically on push

### Backend (Hugging Face Spaces)

The backend includes a deployment script:

```bash
cd backend
python deploy_to_hf.py
```

This uploads all backend files to Hugging Face Spaces, which runs the Dockerized FastAPI application.

**Required HF Space Settings:**
- SDK: Docker
- Hardware: CPU Basic (or higher)
- Secrets: GEMINI_API_KEY, ELEVENLABS_API_KEY

---

## Project Structure

```
Thara-ai/
├── backend/
│   ├── api/                      # FastAPI routes and services
│   │   ├── main.py              # App entry point, CORS, routes
│   │   ├── services.py          # Query orchestration
│   │   └── models.py            # Request/response models
│   │
│   ├── planning_layer/           # Query understanding
│   │   ├── table_router.py      # ChromaDB-based table finding
│   │   ├── llm_table_selector.py# LLM-based table selection
│   │   ├── entity_extractor.py  # Extract dates, locations, etc.
│   │   ├── planner_client.py    # Generate query plans
│   │   └── planner_prompt.py    # LLM prompt for planning
│   │
│   ├── validation_layer/         # Plan validation
│   │   └── plan_validator.py    # Validate and correct plans
│   │
│   ├── execution_layer/          # Query execution
│   │   ├── executor.py          # Run SQL queries
│   │   ├── sql_compiler.py      # Plan to SQL conversion
│   │   ├── query_healer.py      # Self-healing on errors
│   │   └── advanced_executor.py # Complex analytics
│   │
│   ├── explanation_layer/        # Response generation
│   │   ├── explainer_client.py  # LLM-based explanations
│   │   └── explanation_prompt.py# Prompt templates
│   │
│   ├── schema_intelligence/      # Data understanding
│   │   ├── chromadb_client.py   # Vector store
│   │   ├── data_profiler.py     # Table analysis
│   │   └── profile_store.py     # Profile caching
│   │
│   ├── data_sources/             # Data connectors
│   │   ├── gsheet/              # Google Sheets
│   │   └── connectors/          # Drive, CSV, Excel
│   │
│   ├── analytics_engine/         # Database management
│   │   └── duckdb_manager.py    # DuckDB operations
│   │
│   ├── utils/                    # Utilities
│   │   ├── translation.py       # Tamil ↔ English
│   │   ├── voice_utils.py       # Audio processing
│   │   ├── memory_detector.py   # User preferences
│   │   ├── query_context.py     # Conversation tracking
│   │   ├── personality.py       # Thara's personality
│   │   └── visualization.py     # Chart selection
│   │
│   ├── config/                   # Configuration
│   │   ├── settings.yaml        # App settings
│   │   └── metric_definitions.yaml
│   │
│   ├── Dockerfile               # Container definition
│   ├── requirements.txt         # Dev dependencies
│   └── requirements-prod.txt    # Production dependencies
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   │   ├── page.tsx        # Main chat page
│   │   │   └── layout.tsx      # Root layout
│   │   │
│   │   ├── components/          # React components
│   │   │   ├── ChatScreen.tsx  # Main chat interface
│   │   │   ├── MessageBubble.tsx# Message display
│   │   │   ├── DataChart.tsx   # Visualizations
│   │   │   └── ui/             # Reusable UI components
│   │   │
│   │   ├── lib/                 # Utilities
│   │   │   ├── types.ts        # TypeScript types
│   │   │   └── utils.ts        # Helper functions
│   │   │
│   │   └── services/            # API client
│   │       └── api.ts          # Backend communication
│   │
│   ├── package.json            # Dependencies
│   └── tailwind.config.ts      # Tailwind configuration
│
└── README.md                    # This file
```

---

## License

MIT License - Feel free to use, modify, and distribute.

---

**Built with love by the Thara.ai team**
