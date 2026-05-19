import json
import logging
import sqlite3
import time
from contextlib import contextmanager


logger = logging.getLogger(__name__)


EVENT_APP_START = "app_start"
EVENT_STORY_GENERATION_STARTED = "story_generation_started"
EVENT_STORY_GENERATION_COMPLETED = "story_generation_completed"
EVENT_STORY_GENERATION_FAILED = "story_generation_failed"
EVENT_CHAPTER_GENERATION_STARTED = "chapter_generation_started"
EVENT_CHAPTER_GENERATION_COMPLETED = "chapter_generation_completed"
EVENT_CHAPTER_GENERATION_FAILED = "chapter_generation_failed"
EVENT_RAG_SEARCH_STARTED = "rag_search_started"
EVENT_RAG_SEARCH_COMPLETED = "rag_search_completed"
EVENT_RAG_SEARCH_FAILED = "rag_search_failed"
EVENT_TEMPLATE_IMPORT = "template_import"
EVENT_EXPORT_CREATED = "export_created"
EVENT_LLM_CALL_STARTED = "llm_call_started"
EVENT_LLM_CALL_COMPLETED = "llm_call_completed"
EVENT_LLM_CALL_FAILED = "llm_call_failed"


def record_event(event_type, status="", metadata=None, **fields):
    try:
        from database import log_app_event

        return log_app_event(
            event_type=event_type,
            status=status,
            metadata_json=serialize_metadata(metadata),
            **fields,
        )
    except sqlite3.OperationalError as error:
        if "no such table: app_events" in str(error):
            logger.debug("App events table is not available yet.")
        else:
            logger.exception("Could not record app event: %s", event_type)
        return None
    except Exception:
        logger.exception("Could not record app event: %s", event_type)
        return None


@contextmanager
def timed_event(
    event_type,
    status="completed",
    failure_status="failed",
    metadata=None,
    **fields,
):
    start_time = time.perf_counter()

    try:
        yield
    except Exception as error:
        duration_ms = elapsed_ms(start_time)
        record_event(
            event_type,
            status=failure_status,
            duration_ms=duration_ms,
            error_type=type(error).__name__,
            error_message=str(error),
            metadata=metadata,
            **fields,
        )
        raise

    duration_ms = elapsed_ms(start_time)
    record_event(
        event_type,
        status=status,
        duration_ms=duration_ms,
        metadata=metadata,
        **fields,
    )


@contextmanager
def operation_events(
    started_event_type,
    completed_event_type,
    failed_event_type,
    metadata=None,
    **fields,
):
    start_time = time.perf_counter()
    record_event(
        started_event_type,
        status="started",
        metadata=metadata,
        **fields,
    )

    try:
        yield
    except Exception as error:
        duration_ms = elapsed_ms(start_time)
        record_event(
            failed_event_type,
            status="failed",
            duration_ms=duration_ms,
            error_type=type(error).__name__,
            error_message=str(error),
            metadata=metadata,
            **fields,
        )
        raise

    duration_ms = elapsed_ms(start_time)
    record_event(
        completed_event_type,
        status="completed",
        duration_ms=duration_ms,
        metadata=metadata,
        **fields,
    )


def elapsed_ms(start_time):
    return round((time.perf_counter() - start_time) * 1000, 2)


def estimate_tokens(text):
    if not text:
        return 0

    return max(1, round(len(str(text)) / 4))


def serialize_metadata(metadata):
    if not metadata:
        return ""

    try:
        return json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return json.dumps(
            {"repr": repr(metadata)},
            ensure_ascii=False,
            sort_keys=True,
        )


def build_event_dict(row):
    (
        event_id,
        event_type,
        timestamp,
        status,
        duration_ms,
        story_id,
        chapter_id,
        template_id,
        character_id,
        provider,
        model,
        token_estimate,
        error_type,
        error_message,
        metadata_json,
    ) = row

    return {
        "id": event_id,
        "event_type": event_type,
        "timestamp": timestamp,
        "status": status,
        "duration_ms": duration_ms,
        "story_id": story_id,
        "chapter_id": chapter_id,
        "template_id": template_id,
        "character_id": character_id,
        "provider": provider,
        "model": model,
        "token_estimate": token_estimate,
        "error_type": error_type,
        "error_message": error_message,
        "metadata": safe_json_loads(metadata_json),
    }


def list_recent_events(limit=100):
    from database import get_app_events

    return [
        build_event_dict(row)
        for row in get_app_events(limit=limit)
    ]


def safe_json_loads(value):
    if not value:
        return {}

    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return {"raw": value}
