"""
Service layer for API endpoints.
Extracts reusable logic from streamlit_app.py without modifying core backend.
"""

import sys
from pathlib import Path
import re
from typing import Dict, Any, Optional, Tuple

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from schema_intelligence.hybrid_retriever import retrieve_schema
from planning_layer.planner_client import generate_plan
from validation_layer.plan_validator import validate_plan
from execution_layer.executor import execute_plan
from explanation_layer.explainer_client import explain_results
from data_sources.gsheet.connector import fetch_sheets_with_tables
from utils.translation import translate_to_english, translate_to_tamil
from data_sources.gsheet.change_detector import needs_refresh
from data_sources.gsheet.snapshot_loader import load_snapshot
from schema_intelligence.chromadb_client import SchemaVectorStore
from utils.voice_utils import transcribe_audio
from utils.memory_detector import detect_memory_intent
from utils.permanent_memory import update_memory
from utils.greeting_detector import is_greeting, get_greeting_response
import yaml


# Global state management (replaces Streamlit session state)
class AppState:
    """Application state management"""
    def __init__(self):
        self.vector_store: Optional[SchemaVectorStore] = None
        self.data_loaded: bool = False
        self.current_spreadsheet_id: Optional[str] = None
    
    def initialize_vector_store(self):
        """Initialize vector store if not already done"""
        if self.vector_store is None:
            self.vector_store = SchemaVectorStore()
        return self.vector_store


# Singleton instance
app_state = AppState()


def extract_spreadsheet_id(url: str) -> Optional[str]:
    """Extract spreadsheet ID from Google Sheets URL"""
    # Pattern for Google Sheets URLs
    pattern = r'/spreadsheets/d/([a-zA-Z0-9-_]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    # If it's already just the ID
    if re.match(r'^[a-zA-Z0-9-_]+$', url):
        return url
    return None


def load_dataset_service(url: str) -> Dict[str, Any]:
    """
    Load data from Google Sheets with given URL.
    Returns LoadDataResponse-compatible dict.
    """
    try:
        print(f"🔍 Starting load_dataset_service for URL: {url}")
        spreadsheet_id = extract_spreadsheet_id(url)
        if not spreadsheet_id:
            print(f"❌ Invalid spreadsheet ID extracted from URL")
            return {
                'success': False,
                'error': 'Invalid Google Sheets URL or ID'
            }
        
        print(f"✅ Extracted spreadsheet ID: {spreadsheet_id}")
        
        # Update config with new spreadsheet ID
        config_path = project_root / "config" / "settings.yaml"
        print(f"📝 Updating config at: {config_path}")
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        config['google_sheets']['spreadsheet_id'] = spreadsheet_id
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        print(f"✅ Config updated with spreadsheet ID")
        
        # Initialize vector store
        print(f"🔄 Initializing vector store...")
        store = app_state.initialize_vector_store()
        print(f"✅ Vector store initialized")
        
        # Reload data using fetch_sheets_with_tables
        print(f"📊 Fetching sheets with tables...")
        sheets_with_tables = fetch_sheets_with_tables()
        print(f"✅ Fetched {len(sheets_with_tables)} sheets")
        
        # Clear and rebuild vector store
        print(f"🗑️ Clearing vector store...")
        store.clear_collection()
        print(f"📥 Loading snapshot...")
        load_snapshot(sheets_with_tables, full_reset=True)
        print(f"🔨 Rebuilding vector store...")
        store.rebuild()
        print(f"✅ Vector store rebuilt")
        
        # Build response
        total_tables = sum(len(tables) for tables in sheets_with_tables.values())
        total_records = 0
        detected_tables = []
        
        print(f"📋 Building response with {total_tables} tables...")
        
        for sheet_name, tables in sheets_with_tables.items():
            for table in tables:
                # Extract dataframe to get actual row count and columns
                df = table.get('dataframe')
                actual_rows = len(df) if df is not None else 0
                actual_columns = list(df.columns) if df is not None else []
                
                detected_tables.append({
                    'table_id': table.get('table_id', ''),
                    'title': table.get('title', ''),
                    'sheet_name': sheet_name,
                    'source_id': table.get('source_id', ''),
                    'sheet_hash': table.get('sheet_hash', ''),
                    'row_range': table.get('row_range', [0, 0]),
                    'col_range': table.get('col_range', [0, 0]),
                    'total_rows': actual_rows,
                    'columns': actual_columns,
                    'preview_data': []
                })
                total_records += actual_rows
        
        app_state.data_loaded = True
        app_state.current_spreadsheet_id = spreadsheet_id
        
        print(f"✅ Successfully loaded dataset: {total_tables} tables, {total_records} records")
        
        return {
            'success': True,
            'stats': {
                'totalTables': total_tables,
                'totalRecords': total_records,
                'sheetCount': len(sheets_with_tables),
                'sheets': list(sheets_with_tables.keys()),
                'detectedTables': detected_tables
            }
        }
    
    except Exception as e:
        print(f"❌ Exception in load_dataset_service: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def check_and_refresh_data() -> bool:
    """
    Automatically check for data changes and refresh if needed.
    Returns True if data was refreshed.
    """
    try:
        sheets_with_tables = fetch_sheets_with_tables()
        needs_refresh_flag, full_reset, changed_sheets = needs_refresh(sheets_with_tables)
        
        if needs_refresh_flag:
            store = app_state.initialize_vector_store()
            
            if full_reset:
                # Full reset
                store.clear_collection()
                load_snapshot(sheets_with_tables, full_reset=True)
                store.rebuild()
            else:
                # Incremental rebuild
                source_ids = []
                for sheet_name in changed_sheets:
                    if sheet_name in sheets_with_tables and sheets_with_tables[sheet_name]:
                        source_id = sheets_with_tables[sheet_name][0].get('source_id')
                        if source_id:
                            source_ids.append(source_id)
                
                load_snapshot(sheets_with_tables, full_reset=False, changed_sheets=changed_sheets)
                
                if source_ids:
                    store.rebuild(source_ids=source_ids)
                else:
                    store.rebuild()
            
            return True
        
        return False
    
    except Exception as e:
        print(f"Error in check_and_refresh_data: {e}")
        return False


def process_query_service(question: str) -> Dict[str, Any]:
    """
    Process a user query through the full RAG pipeline.
    Returns ProcessQueryResponse-compatible dict.
    """
    try:
        # Phonetic corrections for common STT errors (Hardcoded)
        # Matches "fresh geese", "fresh cheese", "fresh keys", etc.
        question = re.sub(r'fresh\s+(geese|cheese|keys|piece|peace|bees)', 'Freshggies', question, flags=re.IGNORECASE)

        # Check for greetings first
        if is_greeting(question):
            greeting_response = get_greeting_response(question)
            return {
                'success': True,
                'explanation': greeting_response,
                'data': None,
                'plan': None,
                'schema_context': [],
                'data_refreshed': False,
                'is_greeting': True
            }
        
        # Check for memory intent
        memory_result = detect_memory_intent(question)
        if memory_result and memory_result.get("has_memory_intent"):
            category = memory_result["category"]
            key = memory_result["key"]
            value = memory_result["value"]
            
            success = update_memory(category, key, value)
            
            if success:
                return {
                    'success': True,
                    'explanation': "Got it. I'll remember that.",
                    'data': None,
                    'plan': None,
                    'schema_context': [],
                    'data_refreshed': False,
                    'is_memory_storage': True
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to store memory'
                }
        
        # Automatic change detection (DISABLED for performance - manual refresh required)
        # data_refreshed = check_and_refresh_data()
        data_refreshed = False
        
        # --- TRANSLATION LAYER (PRE-PROCESS) ---
        processing_query = question
        is_tamil_query = bool(re.search(r'[\u0B80-\u0BFF]', question))
        
        if is_tamil_query:
            print(f"🈯 Tamil Query Detected: {question}")
            processing_query = translate_to_english(question)
            print(f"🇬🇧 Translated to English: {processing_query}")
            
        # Schema retrieval (use English query)
        # FORCE FULL CONTEXT: User has ~25 tables, so top_k=50 ensures retrieval never filters out the correct table.
        schema_context = retrieve_schema(processing_query, top_k=50)
        
        # Planning (use English query)
        plan = generate_plan(processing_query, schema_context)
        validate_plan(plan)
        
        # Execution
        result = execute_plan(plan)
        
        # Explanation (use English query context)
        explanation = explain_results(result, query_plan=plan, original_question=processing_query)
        
        # --- TRANSLATION LAYER (POST-PROCESS) ---
        if is_tamil_query:
            print(f"🇬🇧 English Explanation: {explanation}")
            explanation = translate_to_tamil(explanation)
            print(f"🈯 Translated Explanation: {explanation}")
        
        # Convert result to list of dicts for JSON serialization
        data_list = None
        if result is not None and hasattr(result, 'to_dict'):
            data_list = result.to_dict('records')
        
        return {
            'success': True,
            'explanation': explanation,
            'data': data_list,
            'plan': plan,
            'schema_context': [{'text': item['text']} for item in schema_context],
            'data_refreshed': data_refreshed
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def transcribe_audio_service(audio_file_path: str) -> Dict[str, Any]:
    """
    Transcribe audio file to text.
    Returns TranscribeResponse-compatible dict.
    """
    try:
        transcribed_text = transcribe_audio(audio_file_path)
        return {
            'success': True,
            'text': transcribed_text
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }
