import os
import json
import threading
from pathlib import Path

# Backend directory for data storage
_BACKEND_DIR = Path(__file__).parent.parent
_CACHE_FILE = _BACKEND_DIR / "data" / "query_plan_cache.json"

_plan_cache = {}
_plan_cache_lock = threading.Lock()
_loaded = False

def _load_cache():
    global _plan_cache, _loaded
    if _loaded:
        return
    with _plan_cache_lock:
        if _loaded:
            return
        os.makedirs(_CACHE_FILE.parent, exist_ok=True)
        if _CACHE_FILE.exists():
            try:
                with open(_CACHE_FILE, 'r', encoding='utf-8') as f:
                    _plan_cache = json.load(f)
            except Exception:
                _plan_cache = {}
        _loaded = True

def _save_cache():
    with _plan_cache_lock:
        try:
            with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(_plan_cache, f)
        except Exception:
            pass

def get_cached_plan(query_text: str) -> dict:
    """Retrieve a cached execution plan for the exact query text."""
    _load_cache()
    # Normalize query for caching
    key = query_text.lower().strip()
    return _plan_cache.get(key)

def set_cached_plan(query_text: str, plan: dict):
    """Save an execution plan to cache."""
    if not plan or plan.get('query_type') == 'unknown':
        return
    _load_cache()
    key = query_text.lower().strip()
    _plan_cache[key] = plan
    # Save asynchronously if we want to avoid blocking, but for now blocking is fast enough
    _save_cache()

def clear_cache():
    """Clear query cache (e.g. when data is reloaded)"""
    global _plan_cache
    with _plan_cache_lock:
        _plan_cache = {}
        if _CACHE_FILE.exists():
            try:
                os.remove(_CACHE_FILE)
            except Exception:
                pass
