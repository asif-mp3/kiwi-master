"""
Generate Technical Pitch Deck PDF for Thara AI (CEO Assistant)
"""
from fpdf import FPDF

# ── Colors ──────────────────────────────────────────────────────
DARK_BG     = (15, 15, 25)
CARD_BG     = (25, 25, 40)
ACCENT      = (139, 92, 246)   # violet-500
ACCENT2     = (168, 85, 247)   # purple-500
WHITE       = (255, 255, 255)
GRAY        = (180, 180, 200)
LIGHT_GRAY  = (220, 220, 235)
GOLD        = (250, 204, 21)
GREEN       = (74, 222, 128)
CYAN        = (34, 211, 238)
PINK        = (244, 114, 182)
ORANGE      = (251, 146, 60)


class PitchPDF(FPDF):
    def __init__(self):
        super().__init__('P', 'mm', 'A4')
        self.set_auto_page_break(auto=True, margin=15)
        # Add Unicode font (Arial from Windows)
        self.add_font("DejaVu", "", r"C:\Windows\Fonts\arial.ttf")
        self.add_font("DejaVu", "B", r"C:\Windows\Fonts\arialbd.ttf")

    # ── helpers ──
    def _bg(self):
        self.set_fill_color(*DARK_BG)
        self.rect(0, 0, 210, 297, 'F')

    def _accent_bar(self, y, w=210):
        self.set_fill_color(*ACCENT)
        self.rect(0, y, w, 1.2, 'F')

    def _section_title(self, title, y=None):
        if y is not None:
            self.set_y(y)
        self.set_font('DejaVu', 'B', 16)
        self.set_text_color(*ACCENT)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
        self._accent_bar(self.get_y())
        self.ln(4)

    def _sub_title(self, title):
        self.set_font('DejaVu', 'B', 12)
        self.set_text_color(*GOLD)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def _body(self, text, bold=False):
        self.set_font('DejaVu', 'B' if bold else '', 9)
        self.set_text_color(*LIGHT_GRAY)
        self.multi_cell(0, 5, text)
        self.ln(1)

    def _bullet(self, text, color=LIGHT_GRAY, indent=15):
        x = self.get_x()
        self.set_x(x + indent)
        self.set_font('DejaVu', '', 9)
        self.set_text_color(*ACCENT)
        self.cell(4, 5, chr(8226))  # bullet
        self.set_text_color(*color)
        self.multi_cell(0, 5, text)
        self.ln(0.5)

    def _stat_box(self, x, y, w, h, number, label, color=ACCENT):
        self.set_fill_color(*CARD_BG)
        self.rect(x, y, w, h, 'F')
        # accent top line
        self.set_fill_color(*color)
        self.rect(x, y, w, 1.5, 'F')
        # number
        self.set_xy(x, y + 5)
        self.set_font('DejaVu', 'B', 22)
        self.set_text_color(*color)
        self.cell(w, 10, number, align='C')
        # label
        self.set_xy(x, y + 17)
        self.set_font('DejaVu', '', 8)
        self.set_text_color(*GRAY)
        self.cell(w, 6, label, align='C')

    def _table_row(self, cols, widths, header=False):
        h = 7
        self.set_font('DejaVu', 'B' if header else '', 8)
        if header:
            self.set_fill_color(*ACCENT)
            self.set_text_color(*WHITE)
        else:
            self.set_fill_color(*CARD_BG)
            self.set_text_color(*LIGHT_GRAY)
        for i, (col, w) in enumerate(zip(cols, widths)):
            self.cell(w, h, str(col), border=0, fill=True, align='L' if i == 0 else 'C')
        self.ln(h)


def build_pdf():
    pdf = PitchPDF()

    # ════════════════════════════════════════════════════════════
    # PAGE 1 : COVER
    # ════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._bg()

    # top accent
    pdf._accent_bar(0, 210)

    # Product name
    pdf.set_y(35)
    pdf.set_font('DejaVu', 'B', 36)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 15, 'THARA AI', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.set_font('DejaVu', '', 14)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 8, 'CEO Assistant  |  Intelligent Data Analytics Platform', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf.ln(3)
    pdf.set_font('DejaVu', '', 10)
    pdf.set_text_color(*GRAY)
    pdf.cell(0, 6, 'Enterprise-Grade Bilingual Voice-First Analytics Engine', align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, 'Talk to your data in English or Tamil. Get instant answers.', align='C', new_x="LMARGIN", new_y="NEXT")

    # Hero stats
    y = 85
    box_w = 40
    gap = 8
    start_x = (210 - (box_w * 4 + gap * 3)) / 2

    stats = [
        ("<2s", "Avg Response", CYAN),
        ("9", "Data Connectors", ACCENT2),
        ("29", "API Endpoints", GREEN),
        ("155", "Test Cases", GOLD),
    ]
    for i, (num, lbl, clr) in enumerate(stats):
        pdf._stat_box(start_x + i * (box_w + gap), y, box_w, 28, num, lbl, clr)

    y2 = 125
    stats2 = [
        ("5", "AI Pipeline Layers", PINK),
        ("16", "Tables Auto-Profiled", ORANGE),
        ("0", "TypeScript `any`", GREEN),
        ("550+", "Logs Structured", CYAN),
    ]
    for i, (num, lbl, clr) in enumerate(stats2):
        pdf._stat_box(start_x + i * (box_w + gap), y2, box_w, 28, num, lbl, clr)

    # Tagline
    pdf.set_y(168)
    pdf.set_font('DejaVu', 'B', 11)
    pdf.set_text_color(*WHITE)
    pdf.cell(0, 8, 'TECHNICAL ACHIEVEMENTS & USPs', align='C', new_x="LMARGIN", new_y="NEXT")

    pdf._accent_bar(178)

    # Key USPs list
    pdf.set_y(183)
    usps = [
        "Multi-Step Cross-Table Query Engine -- joins data across tables without complex SQL",
        "Self-Healing SQL Executor -- 5+ automatic recovery strategies, 3 retries, 0.90 fuzzy threshold",
        "Native Tamil + English Bilingual -- not a translation wrapper; native NLP in both languages",
        "Voice-First UX -- VAD, streaming TTS (200ms TTFB), live word-by-word captions",
        "Dataset-Agnostic -- works with ANY domain (sales, HR, healthcare, education, logistics)",
        "Zero Hallucination Guardrails -- data-only responses, no LLM speculation",
        "Plug-and-Play Data -- 9 connectors, auto-load Google Drive folders, zero schema setup",
        "Intelligent Routing -- LLM-primary table selection, 60% fewer tokens than top-k approaches",
        "Production-Hardened -- rate limiting, SSRF prevention, Sentry, CI/CD, 100% pinned deps",
        "Personality-Driven -- named assistant 'Thara' with 50+ natural conversation patterns",
    ]
    for u in usps:
        pdf._bullet(u, LIGHT_GRAY, indent=20)

    # ════════════════════════════════════════════════════════════
    # PAGE 2 : ARCHITECTURE & TECH STACK
    # ════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._bg()
    pdf._section_title("1. SYSTEM ARCHITECTURE", 12)

    pdf._sub_title("5-Layer Intelligent Query Pipeline")
    layers = [
        ("Layer 1: Routing", "LLM-primary table selection with rule-based fallback. Confidence scoring (high >60%, low <15%). Context-aware follow-up detection."),
        ("Layer 2: Planning", "Gemini 2.0 Flash generates structured query plans. Multi-step support for cross-table joins with variable substitution."),
        ("Layer 3: Validation", "JSON schema validation, date format normalization, column existence checks before execution."),
        ("Layer 4: Execution", "DuckDB in-memory SQL engine. Self-healing with fuzzy matching (0.90 threshold). 3 retry attempts with 5+ fix strategies."),
        ("Layer 5: Explanation", "LLM-powered natural language response. Emotion detection, personality-driven, bilingual output."),
    ]
    for title, desc in layers:
        pdf.set_font('DejaVu', 'B', 9)
        pdf.set_text_color(*CYAN)
        pdf.cell(0, 5, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('DejaVu', '', 8)
        pdf.set_text_color(*LIGHT_GRAY)
        pdf.multi_cell(0, 4.5, desc)
        pdf.ln(1.5)

    pdf._sub_title("Core Tech Stack")
    widths = [55, 65, 60]
    pdf._table_row(["Component", "Technology", "Version"], widths, header=True)
    stack = [
        ["LLM Engine", "Google Gemini 2.0 Flash", "google-genai 1.64.0"],
        ["Database", "DuckDB (in-memory OLAP)", "1.1.3"],
        ["API Framework", "FastAPI + Uvicorn", "0.115.6"],
        ["Frontend", "Next.js + React + TypeScript", "16.1.6 / 19.0.0"],
        ["Voice STT", "ElevenLabs Scribe v2", "1.14.0"],
        ["Voice TTS", "ElevenLabs Flash v2.5", "Streaming"],
        ["Translation", "Google Cloud Translate", "3.18.0"],
        ["Vector DB", "ChromaDB + Sentence-Trans.", "0.5.23"],
        ["Charting", "Recharts (5 chart types)", "3.0.2"],
        ["UI Library", "Radix UI (28+ primitives)", "Latest"],
        ["Styling", "Tailwind CSS 4", "4.0"],
        ["Animations", "Framer Motion", "12.23.24"],
    ]
    for row in stack:
        pdf._table_row(row, widths)

    # ════════════════════════════════════════════════════════════
    # PAGE 3 : PERFORMANCE & LATENCY
    # ════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._bg()
    pdf._section_title("2. PERFORMANCE & LATENCY METRICS", 12)

    # stat boxes
    y = pdf.get_y() + 2
    box_w = 55
    gap = 10
    sx = (210 - (box_w * 3 + gap * 2)) / 2
    perf_stats = [
        ("<2s", "End-to-End Query", CYAN),
        ("200ms", "TTS First Byte", GREEN),
        ("<500ms", "Table Routing", ACCENT),
    ]
    for i, (n, l, c) in enumerate(perf_stats):
        pdf._stat_box(sx + i * (box_w + gap), y, box_w, 28, n, l, c)

    pdf.set_y(y + 35)

    pdf._sub_title("Caching Strategy")
    caches = [
        "TTS Audio Cache: 500 MB max, 24-hour TTL, disk-based (eliminates repeat API calls)",
        "Schema Profile Cache: 3,600s TTL, in-memory (instant table metadata access)",
        "Query Result Cache: REMOVED by design (prevents stale/wrong data in multi-user scenarios)",
        "DuckDB Snapshots: Persistent .duckdb file (sub-100ms analytical queries)",
    ]
    for c in caches:
        pdf._bullet(c)

    pdf._sub_title("Rate Limiting & Throughput")
    pdf._bullet("60 requests/minute per IP (sliding window, configurable via RATE_LIMIT_RPM)")
    pdf._bullet("Exempt endpoints: /, /api/health, /api/auth/check")
    pdf._bullet("HTTP 429 response with Retry-After header on violation")

    pdf._sub_title("Query Execution Performance")
    widths2 = [80, 50, 50]
    pdf._table_row(["Metric", "Value", "Notes"], widths2, header=True)
    perf_rows = [
        ["STT Transcription", "<2 seconds", "ElevenLabs Scribe v2"],
        ["TTS First Audio Chunk", "200-500ms", "Streaming (vs 2-4s buffered)"],
        ["LLM Planning", "1-3 seconds", "Gemini 2.0 Flash"],
        ["SQL Compilation", "<50ms", "Template-based, no string interp"],
        ["DuckDB Query", "<100ms", "In-memory OLAP engine"],
        ["Self-Healing Retry", "3 attempts", "Fuzzy match threshold: 0.90"],
        ["Max Result Set", "10,000 rows", "Configurable limit"],
        ["Connection Pool", "10 connections", "DuckDB max connections"],
        ["LLM Router Timeout", "10 seconds", "Falls back to rule-based"],
        ["Request Timeout", "20 seconds", "Configurable in settings.yaml"],
    ]
    for row in perf_rows:
        pdf._table_row(row, widths2)

    # ════════════════════════════════════════════════════════════
    # PAGE 4 : NLP & VOICE CAPABILITIES
    # ════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._bg()
    pdf._section_title("3. NLP & VOICE CAPABILITIES", 12)

    pdf._sub_title("Bilingual NLP Engine (Tamil + English)")
    pdf._bullet("Language auto-detection via langdetect (no user config needed)")
    pdf._bullet("Google Cloud Translate API for Tamil <-> English translation")
    pdf._bullet("50+ entity extraction keywords (metrics, dimensions, identifiers, locations)")
    pdf._bullet("24 Tamil month name variations recognized (January -> Janvari)")
    pdf._bullet("31 Tamil ordinal number forms for date extraction")
    pdf._bullet("Follow-up detection: pronouns, comparison phrases, time ranges")
    pdf._bullet("Greeting detection: 26 Tamil starters + 22 English variations")

    pdf._sub_title("Voice Activity Detection (VAD) -- Proprietary")
    widths3 = [80, 50, 50]
    pdf._table_row(["Parameter", "Value", "Purpose"], widths3, header=True)
    vad_rows = [
        ["FFT Size", "256-point", "Frequency analysis"],
        ["Smoothing Constant", "0.3", "Noise reduction"],
        ["Silence Threshold", "8 (audio level)", "Speech vs silence"],
        ["Min Speech Duration", "500ms", "Avoid premature cutoff"],
        ["Silence Duration", "1.5 seconds", "Natural pause detection"],
        ["Check Interval", "50ms", "Real-time responsiveness"],
        ["Max Recording", "15 seconds", "Auto-stop timeout"],
        ["Audio Codec", "WebM/Opus", "Bandwidth optimized"],
    ]
    for row in vad_rows:
        pdf._table_row(row, widths3)

    pdf.ln(2)
    pdf._sub_title("Voice UX Features")
    pdf._bullet("Streaming TTS: Audio plays as chunks arrive (200ms TTFB, not 2-4s buffered)")
    pdf._bullet("Live Captions: Word-by-word animation at 80ms intervals")
    pdf._bullet("Always-On Mode: Continuous listening, auto-resumes after TTS finishes")
    pdf._bullet("Farewell Detection: Recognizes goodbye phrases in both languages")
    pdf._bullet("Haptic Feedback: Vibration patterns on record start/stop")
    pdf._bullet("Dual Voice: Separate English and Tamil neural voices (ElevenLabs)")
    pdf._bullet("Voice Visualizer: 32-bar frequency spectrum with ambient glow effects")
    pdf._bullet("1.15x Playback Speed: Optimized for natural conversation pacing")

    # ════════════════════════════════════════════════════════════
    # PAGE 5 : DATA INTEGRATION
    # ════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._bg()
    pdf._section_title("4. DATA INTEGRATION -- PLUG & PLAY", 12)

    pdf._sub_title("9 Data Source Connectors")
    widths4 = [50, 55, 75]
    pdf._table_row(["Connector", "Formats", "Detection"], widths4, header=True)
    connectors = [
        ["Google Sheets", "Sheets API", "spreadsheets.google.com"],
        ["Google Drive File", "CSV, Excel, PDF", "drive.google.com/file"],
        ["Google Drive Folder", "All files in folder", "drive.google.com/folders"],
        ["CSV", ".csv", "Extension / content-type"],
        ["Excel", ".xlsx, .xls, .xlsm", "Extension detection"],
        ["PDF", ".pdf (table extraction)", "pdfplumber library"],
        ["Dropbox", "CSV, Excel", "dropbox.com URLs"],
        ["OneDrive/SharePoint", "CSV, Excel", "sharepoint.com URLs"],
        ["Local Filesystem", "Any supported format", "file:// or absolute paths"],
    ]
    for row in connectors:
        pdf._table_row(row, widths4)

    pdf.ln(2)
    pdf._sub_title("Auto-Profiling System")
    pdf._bullet("Automatic table type detection: transactional, summary, item-level")
    pdf._bullet("Column classification: metrics (50+ keywords), dimensions (20+), identifiers (25+)")
    pdf._bullet("Date range inference per table (enables temporal filtering)")
    pdf._bullet("Data quality scoring: 0-100% per table")
    pdf._bullet("NULL analysis: warnings for >50% NULL columns")
    pdf._bullet("Sample size: 10,000 rows for profiling analysis")
    pdf._bullet("Entity learning: locations, categories, products extracted from data profiles")

    pdf._sub_title("Data Sync & Change Detection")
    pdf._bullet("SHA-256 hash-based change detection at sheet level")
    pdf._bullet("Incremental rebuilds: only changed sheets re-processed")
    pdf._bullet("Failure isolation: old data preserved if sync fails")
    pdf._bullet("SSE loading progress: real-time phases (scanning -> profiling -> ready)")
    pdf._bullet("Auto-load on startup: DEFAULT_DRIVE_FOLDER_URL env variable")

    pdf._sub_title("Export Capabilities")
    pdf._bullet("Excel export via XLSX library (client-side)")
    pdf._bullet("PDF export via jsPDF with auto-table formatting")
    pdf._bullet("COUNT queries show underlying data rows, not just the count")

    # ════════════════════════════════════════════════════════════
    # PAGE 6 : SECURITY & PRODUCTION
    # ════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._bg()
    pdf._section_title("5. SECURITY & PRODUCTION HARDENING", 12)

    pdf._sub_title("Security Architecture")
    pdf._bullet("SQL Injection Prevention: 18 regex patterns (UNION, xp_, WAITFOR, hex payloads)")
    pdf._bullet("SSRF Prevention: Whitelist of 8 allowed domains (Google, Dropbox, OneDrive, etc.)")
    pdf._bullet("Private IP Blocking: 127.x, 10.x, 172.16.x, 192.168.x all rejected")
    pdf._bullet("Input Validation: 10,000 char max, NULL byte removal, quote escaping")
    pdf._bullet("Auth: Token-based (64-char hex), SKIP_AUTH gated to dev environment only")
    pdf._bullet("Debug endpoints: Protected behind require_auth middleware")
    pdf._bullet("Prompt Injection Protection: 100 char limit on user memory inputs")

    pdf._sub_title("Hallucination Prevention")
    pdf._bullet("System prompt guardrail: 'ONLY use actual data numbers' (enforced 3x in prompts)")
    pdf._bullet("No-speculation mode: 'Report what was searched factually, never analyze WHY'")
    pdf._bullet("NaN/None handling: Skip invalid values instead of defaulting to 0")
    pdf._bullet("Fuzzy match safety: 0.90 threshold prevents 'Oct' -> 'Nov' type errors")
    pdf._bullet("Healing transparency: Surface all column/table fixes to user in response")

    pdf._sub_title("Code Quality Metrics")
    widths5 = [90, 45, 45]
    pdf._table_row(["Metric", "Before", "After"], widths5, header=True)
    quality = [
        ["TypeScript `any` types", "11", "0"],
        ["console.log statements", "99", "0"],
        ["Python print() statements", "550+", "0 (structured logging)"],
        ["ignoreBuildErrors", "true", "REMOVED"],
        ["Silent except: pass", "2", "0 (all logged)"],
        ["Dependency pinning", ">=", "== (exact versions)"],
        ["services.py lines", "4,176", "1,285 + 6 modules"],
        ["ChatScreen.tsx lines", "2,860", "981 + 5 components"],
    ]
    for row in quality:
        pdf._table_row(row, widths5)

    pdf.ln(2)
    pdf._sub_title("CI/CD & Testing")
    pdf._bullet("GitHub Actions: Automated on push to main/dev + PR validation")
    pdf._bullet("Backend: pytest + coverage (30% minimum threshold)")
    pdf._bullet("Frontend: TypeScript type check + ESLint + Next.js production build")
    pdf._bullet("155 test cases across 11 test modules")
    pdf._bullet("Sentry integration: Optional error tracking via SENTRY_DSN env var")
    pdf._bullet("Global exception handler: Returns JSON, never raw 500 HTML errors")

    # ════════════════════════════════════════════════════════════
    # PAGE 7 : SUMMARY & DIFFERENTIATORS
    # ════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf._bg()
    pdf._section_title("6. WHAT MAKES THARA AI UNIQUE", 12)

    pdf._sub_title("Technical Differentiators vs Competitors")

    diffs = [
        ("Cross-Table Intelligence",
         "Multi-step query engine joins data across tables automatically. Example: 'Who worked on peak sales dates?' fetches sales peak date, then queries attendance -- no SQL knowledge needed."),
        ("Self-Healing Queries",
         "If a query fails (typo, wrong column name, case mismatch), the engine automatically retries with 5+ fixing strategies. 0.90 fuzzy match threshold ensures accurate recovery without false positives."),
        ("True Bilingual -- Not Translation",
         "Native Tamil NLP with 24 month names, 31 ordinal numbers, entity extraction in both languages. Not a translation wrapper -- understands Tamil grammar and context natively."),
        ("Voice-First Architecture",
         "Proprietary VAD with 50ms polling. Streaming TTS delivers first audio in 200ms (vs 2-4s industry standard). Always-on mode enables hands-free continuous conversation."),
        ("Zero-Config Data Onboarding",
         "Drop a Google Drive folder link -- auto-loads all files, profiles every column, detects date ranges, classifies table types. Zero schema definition required."),
        ("Personality-Driven UX",
         "Named assistant 'Thara' with 50+ natural conversation patterns in both languages. Emotion detection adapts response tone. Never asks 'Did you mean?' -- makes confident decisions."),
        ("Enterprise Security",
         "18-pattern SQL injection defense, SSRF whitelist, private IP blocking, rate limiting, prompt injection protection. Production-ready from day one."),
        ("Dataset Agnostic",
         "Works with ANY domain -- sales, HR, healthcare, education, logistics. All routing logic derives from loaded data profiles, zero hardcoded domain knowledge."),
    ]

    for title, desc in diffs:
        pdf.set_font('DejaVu', 'B', 10)
        pdf.set_text_color(*CYAN)
        pdf.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font('DejaVu', '', 8)
        pdf.set_text_color(*LIGHT_GRAY)
        pdf.multi_cell(0, 4.5, desc)
        pdf.ln(2)

    # Bottom summary box
    pdf.ln(3)
    pdf.set_fill_color(*CARD_BG)
    box_y = pdf.get_y()
    pdf.rect(15, box_y, 180, 30, 'F')
    pdf.set_fill_color(*ACCENT)
    pdf.rect(15, box_y, 180, 1.5, 'F')

    pdf.set_xy(20, box_y + 5)
    pdf.set_font('DejaVu', 'B', 12)
    pdf.set_text_color(*WHITE)
    pdf.cell(170, 7, "THARA AI = Voice + Data + Intelligence", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.set_font('DejaVu', '', 9)
    pdf.set_text_color(*GRAY)
    pdf.cell(170, 6, "Talk to your business data in your language. Get instant, accurate, trustworthy answers.", align='C', new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(20)
    pdf.cell(170, 6, "No SQL. No dashboards. No training. Just ask.", align='C')

    # ── Footer on all pages ──
    for i in range(1, pdf.pages_count + 1):
        pdf.page = i
        pdf.set_y(-12)
        pdf.set_font('DejaVu', '', 7)
        pdf.set_text_color(*GRAY)
        pdf.cell(0, 5, f"Thara AI  |  Technical Pitch Deck  |  Confidential  |  Page {i}/{pdf.pages_count}", align='C')

    # ── Save ──
    output_path = "Thara_AI_Technical_Pitch.pdf"
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")
    return output_path


if __name__ == "__main__":
    build_pdf()
