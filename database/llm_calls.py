from datetime import datetime

from database.connection import get_connection
from database.metadata import mark_local_data_modified


def save_llm_call(provider, model, prompt, response):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO llm_calls
        (
            created_at,
            provider,
            model,
            prompt,
            response
        )
        VALUES (?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        provider,
        model,
        prompt,
        response
    ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def get_llm_calls():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            created_at,
            provider,
            model,
            prompt,
            response
        FROM llm_calls
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows
