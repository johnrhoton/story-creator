from database.connection import get_connection
from database.metadata import mark_local_data_modified


def add_llm_model(provider, model, best_use, is_default=False):
    conn = get_connection()
    cursor = conn.cursor()

    if is_default:
        clear_default_for_provider(cursor, provider)

    cursor.execute("""
        INSERT OR REPLACE INTO llm_models
        (
            provider,
            model,
            best_use,
            is_default
        )
        VALUES (?, ?, ?, ?)
    """, (
        provider,
        model,
        best_use,
        1 if is_default else 0
    ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def set_default_llm_model(model_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT provider
        FROM llm_models
        WHERE id = ?
    """, (
        model_id,
    ))

    row = cursor.fetchone()

    if not row:
        conn.close()
        return False

    provider = row[0]

    clear_default_for_provider(cursor, provider)

    cursor.execute("""
        UPDATE llm_models
        SET is_default = 1
        WHERE id = ?
    """, (
        model_id,
    ))

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return True


def clear_default_for_provider(cursor, provider):
    cursor.execute("""
        UPDATE llm_models
        SET is_default = 0
        WHERE provider = ?
    """, (
        provider,
    ))


def delete_llm_model(model_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM llm_models
        WHERE id = ?
    """, (
        model_id,
    ))

    if cursor.rowcount:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def delete_llm_models(model_ids):
    if not model_ids:
        return 0

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join("?" for _model_id in model_ids)

    cursor.execute(f"""
        DELETE FROM llm_models
        WHERE id IN ({placeholders})
    """, tuple(model_ids))

    deleted_count = cursor.rowcount

    if deleted_count:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return deleted_count


def get_llm_models():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            provider,
            model,
            best_use,
            is_default
        FROM llm_models
        ORDER BY provider, is_default DESC, model
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_llm_models_for_export(model_ids):
    if not model_ids:
        return []

    conn = get_connection()
    cursor = conn.cursor()

    placeholders = ", ".join("?" for _model_id in model_ids)

    cursor.execute(f"""
        SELECT
            id,
            provider,
            model,
            best_use,
            is_default
        FROM llm_models
        WHERE id IN ({placeholders})
        ORDER BY provider, model
    """, tuple(model_ids))

    columns = [column[0] for column in cursor.description]
    rows = [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

    conn.close()

    return rows


def get_llm_models_by_provider(provider):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            provider,
            model,
            best_use,
            is_default
        FROM llm_models
        WHERE provider = ?
        ORDER BY is_default DESC, model
    """, (
        provider,
    ))

    rows = cursor.fetchall()
    conn.close()

    return rows
