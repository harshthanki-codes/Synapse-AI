import os
import sqlite3
from config.settings import SQLITE_DB_PATH


def clear_checkpoint_cache(db_path: str = SQLITE_DB_PATH) -> int:
    """Removes crash lock markers and clears persisted LangGraph checkpoints."""
    if os.path.exists(".resumed"):
        os.remove(".resumed")

    removed_rows = 0
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            for table in ("checkpoints", "writes"):
                try:
                    cur.execute(f"DELETE FROM {table}")
                    removed_rows += max(cur.rowcount, 0)
                except sqlite3.OperationalError:
                    pass
            conn.commit()
        finally:
            conn.close()
    return removed_rows


if __name__ == "__main__":
    count = clear_checkpoint_cache()
    print(f"Cache cleared successfully ({count} checkpoint entries removed).")
