"""
Webhook Handler for Real-time Google Sheets Updates
=====================================================

This module handles webhook notifications from Google Apps Script
when sheet data changes. It provides:
1. Async update queue - no blocking on webhook handler
2. SSE notifications - push updates to frontend
3. Thread-safe dirty tracking - mark sheets for refresh

Architecture:
  Google Apps Script → POST /api/sheet-update → Queue → Worker → SSE → Frontend
"""

import threading
import queue
import asyncio
from datetime import datetime
from typing import Dict, Set, List, Optional, Any
from dataclasses import dataclass, field
import time


@dataclass
class SheetUpdate:
    """Represents a sheet update notification."""
    spreadsheet_id: str
    sheet_name: Optional[str] = None
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class SheetUpdateHandler:
    """
    Handles real-time sheet updates via webhooks.
    
    Thread-safe singleton that manages:
    - Update queue for async processing
    - SSE subscriber list for frontend notifications
    - Worker thread for background refresh
    """
    
    _instance: Optional['SheetUpdateHandler'] = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - one handler per process."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._update_queue: queue.Queue[SheetUpdate] = queue.Queue()
        self._dirty_sheets: Set[str] = set()
        self._dirty_lock = threading.Lock()
        
        # Worker thread for processing updates
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        
        # SSE subscribers (asyncio queues for each connected client)
        self._sse_subscribers: List[asyncio.Queue] = []
        self._sse_lock = threading.Lock()
        
        # Last refresh timestamp
        self._last_refresh: Optional[datetime] = None
        self._last_refresh_sheet: Optional[str] = None
        
        self._initialized = True
        print("[Webhook] SheetUpdateHandler initialized")
    
    def queue_update(self, spreadsheet_id: str, sheet_name: Optional[str] = None) -> bool:
        """
        Queue a sheet update for async processing.
        
        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
            sheet_name: Optional specific sheet that changed
            
        Returns:
            True if update was queued successfully
        """
        try:
            update = SheetUpdate(
                spreadsheet_id=spreadsheet_id,
                sheet_name=sheet_name
            )
            self._update_queue.put_nowait(update)
            
            # Mark sheet as dirty
            with self._dirty_lock:
                key = f"{spreadsheet_id}#{sheet_name}" if sheet_name else spreadsheet_id
                self._dirty_sheets.add(key)
            
            print(f"[Webhook] Queued update for {sheet_name or 'all sheets'}")
            return True
            
        except queue.Full:
            print("[Webhook] Update queue full, dropping update")
            return False
    
    def start_worker(self):
        """Start the background worker thread."""
        if self._running:
            return
            
        self._running = True
        self._worker_thread = threading.Thread(
            target=self._process_updates,
            name="sheet-update-worker",
            daemon=True
        )
        self._worker_thread.start()
        print("[Webhook] Background worker started")
    
    def stop_worker(self):
        """Stop the background worker thread."""
        self._running = False
        if self._worker_thread:
            # Put sentinel to wake up blocked get()
            self._update_queue.put(None)
            self._worker_thread.join(timeout=5)
            self._worker_thread = None
        print("[Webhook] Background worker stopped")
    
    def _process_updates(self):
        """Worker loop - processes queued updates."""
        print("[Webhook] Worker thread started")
        
        while self._running:
            try:
                # Wait for update (blocks until available)
                update = self._update_queue.get(timeout=1.0)
                
                if update is None:  # Sentinel for shutdown
                    break
                
                print(f"[Webhook] Processing update for {update.spreadsheet_id}")
                
                # Process the update
                self._do_refresh(update)
                
                # Notify SSE subscribers
                self._notify_subscribers({
                    'type': 'data_refreshed',
                    'spreadsheet_id': update.spreadsheet_id,
                    'sheet_name': update.sheet_name,
                    'timestamp': datetime.now().isoformat()
                })
                
                # Clear dirty flag
                with self._dirty_lock:
                    key = f"{update.spreadsheet_id}#{update.sheet_name}" if update.sheet_name else update.spreadsheet_id
                    self._dirty_sheets.discard(key)
                
                self._update_queue.task_done()
                
            except queue.Empty:
                continue  # Timeout, check if still running
            except Exception as e:
                print(f"[Webhook] Error processing update: {e}")
                import traceback
                traceback.print_exc()
    
    def _do_refresh(self, update: SheetUpdate):
        """
        Perform the actual data refresh.
        
        This fetches updated sheet data, updates DuckDB, and reprofiles tables.
        """
        try:
            from api.services import app_state, check_and_refresh_data
            from data_sources.gsheet.connector import fetch_sheets_with_tables
            from data_sources.gsheet.snapshot_loader import load_snapshot
            
            print(f"[Webhook] Starting refresh for {update.sheet_name or 'all sheets'}...")
            start_time = time.time()
            
            # Force data_loaded to False to trigger refresh
            app_state.data_loaded = False
            
            # Use existing refresh logic
            refreshed = check_and_refresh_data()
            
            elapsed = time.time() - start_time
            
            if refreshed:
                self._last_refresh = datetime.now()
                self._last_refresh_sheet = update.sheet_name
                print(f"[Webhook] ✓ Refresh completed in {elapsed:.2f}s")
            else:
                print(f"[Webhook] No changes detected (hash match)")
            
            # Mark data as loaded again
            app_state.data_loaded = True
            
        except Exception as e:
            print(f"[Webhook] Refresh failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _notify_subscribers(self, event: Dict[str, Any]):
        """Send event to all SSE subscribers."""
        with self._sse_lock:
            dead_subscribers = []
            
            for i, sub_queue in enumerate(self._sse_subscribers):
                try:
                    # Non-blocking put
                    sub_queue.put_nowait(event)
                except asyncio.QueueFull:
                    print(f"[Webhook] Subscriber {i} queue full, marking for removal")
                    dead_subscribers.append(sub_queue)
                except Exception as e:
                    print(f"[Webhook] Error notifying subscriber: {e}")
                    dead_subscribers.append(sub_queue)
            
            # Remove dead subscribers
            for dead in dead_subscribers:
                self._sse_subscribers.remove(dead)
    
    def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to update notifications (for SSE).
        
        Returns:
            Asyncio queue that will receive update events
        """
        sub_queue = asyncio.Queue(maxsize=10)
        with self._sse_lock:
            self._sse_subscribers.append(sub_queue)
        print(f"[Webhook] New SSE subscriber (total: {len(self._sse_subscribers)})")
        return sub_queue
    
    def unsubscribe(self, sub_queue: asyncio.Queue):
        """Remove an SSE subscriber."""
        with self._sse_lock:
            if sub_queue in self._sse_subscribers:
                self._sse_subscribers.remove(sub_queue)
        print(f"[Webhook] SSE subscriber removed (total: {len(self._sse_subscribers)})")
    
    def is_dirty(self, spreadsheet_id: str, sheet_name: Optional[str] = None) -> bool:
        """Check if a sheet has pending updates."""
        with self._dirty_lock:
            if sheet_name:
                return f"{spreadsheet_id}#{sheet_name}" in self._dirty_sheets
            return any(k.startswith(spreadsheet_id) for k in self._dirty_sheets)
    
    def get_last_refresh(self) -> Optional[Dict[str, Any]]:
        """Get info about the last refresh."""
        if self._last_refresh:
            return {
                'timestamp': self._last_refresh.isoformat(),
                'sheet_name': self._last_refresh_sheet,
                'seconds_ago': (datetime.now() - self._last_refresh).total_seconds()
            }
        return None


# Singleton accessor
def get_webhook_handler() -> SheetUpdateHandler:
    """Get the singleton webhook handler instance."""
    return SheetUpdateHandler()
