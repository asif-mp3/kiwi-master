import duckdb
from pathlib import Path

from utils.logger import get_logger

logger = get_logger("duckdb")


class DuckDBManager:
    def __init__(self, path="data_sources/snapshots/latest.duckdb"):
        db_path = Path(path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = str(db_path)
        self.conn = duckdb.connect(self._db_path)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def list_tables(self):
        return [row[0] for row in self.conn.execute("SHOW TABLES").fetchall()]

    def query(self, sql: str):
        return self.conn.execute(sql).fetchdf()

    def get_connection(self):
        """Return the underlying DuckDB connection for advanced queries."""
        return self.conn

    def close(self):
        """Close the DuckDB connection."""
        try:
            if self.conn:
                self.conn.close()
        except Exception as e:
            logger.warning("Error closing DuckDB connection: %s", e)
