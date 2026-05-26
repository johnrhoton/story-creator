import sqlite3
from pathlib import Path

from config import get_sqlite_db_path


def get_database_path():
    return Path(get_sqlite_db_path())


def get_connection():
    db_path = get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn
