from datetime import datetime
from pathlib import Path

from config import DB_NAME
from database.migrations import run_migrations
from database.schema import create_tables
from database.load_seed import seed_database_from_load_folder


def reinitialize_database():
    db_path = Path(DB_NAME)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived_path = None

    if db_path.exists():
        archived_path = db_path.with_name(
            f"{db_path.stem}_reinitialized_{timestamp}{db_path.suffix}"
        )

        db_path.rename(archived_path)

    run_migrations()
    create_tables()
    seed_database_from_load_folder()

    return str(archived_path) if archived_path else None
