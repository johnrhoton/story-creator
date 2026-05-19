import logging
from pathlib import Path


logger = logging.getLogger(__name__)


LOAD_FOLDER = Path("load")
LOAD_FILE_SUFFIXES = {".json", ".yaml", ".yml"}
SEED_CONTENT_KEYS = {
    "characters",
    "llm_models",
    "profiles",
    "stories",
    "story_beats",
    "story_chapters",
    "story_templates",
    "story_template_chapters",
}


def seed_database_from_load_folder(load_folder=LOAD_FOLDER):
    load_path = Path(load_folder)

    if not load_path.exists():
        return {}

    if not load_path.is_dir():
        logger.warning("Skipping database seed because %s is not a directory.", load_path)
        return {}

    if not database_is_empty_for_seed():
        logger.info("Skipping load folder seed because database already has app data.")
        return {}

    import_counts = {}

    for load_file in list_load_files(load_path):
        try:
            counts = import_load_file(load_file)
        except Exception:
            logger.exception("Failed to import seed file %s.", load_file)
            raise

        import_counts[str(load_file)] = counts
        logger.info("Imported seed file %s with counts %s.", load_file, counts)

    return import_counts


def database_is_empty_for_seed():
    from database import export_database_to_dict

    data = export_database_to_dict()

    return not any(
        data.get(key)
        for key in SEED_CONTENT_KEYS
    )


def list_load_files(load_path):
    return [
        path
        for path in sorted(load_path.iterdir(), key=lambda item: item.name.lower())
        if path.is_file() and path.suffix.lower() in LOAD_FILE_SUFFIXES
    ]


def import_load_file(load_file):
    from database import import_database_from_json, import_database_from_yaml

    suffix = load_file.suffix.lower()

    with load_file.open("rb") as file_handle:
        if suffix == ".json":
            return import_database_from_json(file_handle, replace_existing=False)

        return import_database_from_yaml(file_handle, replace_existing=False)
