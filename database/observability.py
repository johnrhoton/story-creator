from datetime import datetime

from database.connection import get_connection


OBSERVABILITY_COLUMNS = [
    "id",
    "event_type",
    "timestamp",
    "status",
    "duration_ms",
    "story_id",
    "chapter_id",
    "template_id",
    "character_id",
    "provider",
    "model",
    "token_estimate",
    "error_type",
    "error_message",
    "metadata_json",
]


def log_app_event(
    event_type,
    status="",
    duration_ms=None,
    story_id=None,
    chapter_id=None,
    template_id=None,
    character_id=None,
    provider="",
    model="",
    token_estimate=None,
    error_type="",
    error_message="",
    metadata_json="",
    timestamp=None,
):
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO app_events
            (
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
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_type,
            timestamp or datetime.now().isoformat(timespec="seconds"),
            status or "",
            duration_ms,
            story_id,
            chapter_id,
            template_id,
            character_id,
            provider or "",
            model or "",
            token_estimate,
            error_type or "",
            error_message or "",
            metadata_json or "",
        ))

        event_id = cursor.lastrowid
        conn.commit()
    finally:
        conn.close()

    return event_id


def get_app_events(limit=100):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
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
            metadata_json
        FROM app_events
        ORDER BY datetime(timestamp) DESC, id DESC
        LIMIT ?
    """, (
        int(limit or 100),
    ))

    rows = cursor.fetchall()
    conn.close()

    return rows
