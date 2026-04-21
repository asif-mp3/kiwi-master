import duckdb
import threading
from pathlib import Path
from typing import Optional

from utils.logger import get_logger

logger = get_logger("duckdb")

# Module-level shared connection — opened once, reused for all read queries.
# This eliminates 16+ connection open/close cycles per query.
_shared_conn: Optional[duckdb.DuckDBPyConnection] = None
_shared_path: Optional[str] = None
_conn_lock = threading.Lock()


def _get_shared_conn(path: str) -> duckdb.DuckDBPyConnection:
    """Return the module-level shared DuckDB connection, creating it if needed."""
    global _shared_conn, _shared_path
    if _shared_conn is None or _shared_path != path:
        with _conn_lock:
            if _shared_conn is None or _shared_path != path:
                if _shared_conn is not None:
                    try:
                        _shared_conn.close()
                    except Exception:
                        pass
                _shared_conn = duckdb.connect(path)
                _shared_path = path
                logger.debug("DuckDB shared connection opened: %s", path)
    return _shared_conn


def reset_shared_conn():
    """
    Close and discard the shared connection.
    Call this after writing new data so the next query opens a fresh connection.
    """
    global _shared_conn, _shared_path
    with _conn_lock:
        if _shared_conn is not None:
            try:
                _shared_conn.close()
            except Exception:
                pass
            _shared_conn = None
            _shared_path = None
            logger.debug("DuckDB shared connection reset (data reload)")


class DuckDBManager:
    def __init__(self, path="data_sources/snapshots/latest.duckdb"):
        db_path = Path(path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_path)
        self.conn = _get_shared_conn(self._db_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Do not close the shared connection on context exit.
        return False

    def list_tables(self):
        return [row[0] for row in self.conn.execute("SHOW TABLES").fetchall()]

    def query(self, sql: str):
        return self.conn.execute(sql).fetchdf()

    def get_connection(self):
        """Return the underlying DuckDB connection for advanced queries."""
        return self.conn

    def close(self):
        """No-op — shared connection is managed at module level."""
        pass
