"""Services package - split from monolithic services.py for maintainability."""
# CRITICAL: Add project root to sys.path BEFORE importing any service modules,
# since app_state.py imports from utils.*, schema_intelligence.*, etc. which need backend/ in sys.path
import sys
from pathlib import Path
_project_root = Path(__file__).parent.parent.parent  # api/services/ -> api/ -> backend/
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from api.services.app_state import app_state, AppState
from api.services.query_utils import (
    _extract_metric_name_from_result, _humanize_metric,
    _resolve_top_references, _extract_result_values, _sanitize_for_json
)
from api.services.dataset_service import (
    extract_spreadsheet_id, load_dataset_service,
    load_dataset_from_source, sync_drive_folder,
    check_and_refresh_data
)
from api.services.projection_service import (
    _handle_projection, _generate_projection_explanation
)
from api.services.correction_service import (
    _handle_correction, _handle_pending_correction_response,
    _generate_clarification_message
)
from api.services.query_executor import (
    _execute_with_forced_table, _execute_with_modified_plan
)
from api.services.query_service import (
    process_query_service, transcribe_audio_service,
    start_onboarding_service, process_onboarding_input_service,
    get_routing_debug_service, get_table_profiles_service,
    clear_context_service
)
