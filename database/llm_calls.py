from datetime import datetime

from database.connection import get_connection
from database.db_encryption import decrypt_database_rows, encrypt_database_field
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
        encrypt_database_field("llm_calls", "prompt", prompt),
        encrypt_database_field("llm_calls", "response", response)
    ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def save_failed_llm_call(
    provider,
    model,
    prompt,
    response,
    error_type,
    error_codes,
    error_message,
    error_details
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO failed_llm_calls
        (
            created_at,
            provider,
            model,
            prompt,
            response,
            error_type,
            error_codes,
            error_message,
            error_details
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        provider,
        model,
        encrypt_database_field("failed_llm_calls", "prompt", prompt),
        encrypt_database_field("failed_llm_calls", "response", response),
        error_type,
        error_codes,
        encrypt_database_field(
            "failed_llm_calls",
            "error_message",
            error_message
        ),
        encrypt_database_field(
            "failed_llm_calls",
            "error_details",
            error_details
        )
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

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "llm_calls",
        cursor.fetchall(),
        columns
    )
    conn.close()

    return rows


def get_failed_llm_calls():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            created_at,
            provider,
            model,
            prompt,
            response,
            error_type,
            error_codes,
            error_message,
            error_details
        FROM failed_llm_calls
        ORDER BY id DESC
    """)

    columns = [column[0] for column in cursor.description]
    rows = decrypt_database_rows(
        "failed_llm_calls",
        cursor.fetchall(),
        columns
    )
    conn.close()

    return rows
