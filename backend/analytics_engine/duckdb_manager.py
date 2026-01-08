import duckdb
from pathlib import Path

class DuckDBManager:
    def __init__(self, path="data_sources/snapshots/latest.duckdb"):
        # Ensure directory exists before connecting
        db_path = Path(path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(db_path))

    def list_tables(self):
        return [row[0] for row in self.conn.execute("SHOW TABLES").fetchall()]

    def query(self, sql: str):
        return self.conn.execute(sql).fetchdf()

    def get_connection(self):
        """Return the underlying DuckDB connection for advanced queries."""
        return self.conn
