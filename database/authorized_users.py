from database.connection import get_connection
from database.metadata import get_utc_timestamp, mark_local_data_modified


DEFAULT_ADMIN_EMAIL = "rhoton@gmail.com"
DEFAULT_ADMIN_ROLE = "Administrator"
ADMINISTRATOR_ROLE = "Administrator"


def seed_default_authorized_user(cursor):
    timestamp = get_utc_timestamp()
    cursor.execute("""
        INSERT OR IGNORE INTO authorized_users
        (
            email,
            role,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        DEFAULT_ADMIN_EMAIL,
        DEFAULT_ADMIN_ROLE,
        timestamp,
        timestamp,
    ))


def get_authorized_users():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            email,
            role,
            google_sub,
            updated_at
        FROM authorized_users
        ORDER BY email
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_authorized_user_by_identity(google_sub=None, email=None):
    conn = get_connection()
    cursor = conn.cursor()

    row = None

    if google_sub:
        cursor.execute("""
            SELECT
                id,
                email,
                role,
                google_sub,
                updated_at
            FROM authorized_users
            WHERE google_sub = ?
        """, (
            google_sub,
        ))
        row = cursor.fetchone()

    if row is None and email:
        cursor.execute("""
            SELECT
                id,
                email,
                role,
                google_sub,
                updated_at
            FROM authorized_users
            WHERE lower(email) = lower(?)
        """, (
            email,
        ))
        row = cursor.fetchone()

    conn.close()

    return row


def bind_authorized_user_google_sub(user_id, google_sub):
    if not user_id or not google_sub:
        return False

    conn = get_connection()
    cursor = conn.cursor()
    timestamp = get_utc_timestamp()

    cursor.execute("""
        UPDATE authorized_users
        SET
            google_sub = ?,
            updated_at = ?
        WHERE id = ?
          AND (
              google_sub IS NULL
              OR google_sub = ''
          )
    """, (
        google_sub,
        timestamp,
        user_id,
    ))

    updated = cursor.rowcount > 0

    if updated:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return updated


def add_authorized_user(email, role):
    email = normalize_email(email)
    role = normalize_role(role)
    timestamp = get_utc_timestamp()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO authorized_users
        (
            email,
            role,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        email,
        role,
        timestamp,
        timestamp,
    ))

    user_id = cursor.lastrowid
    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return user_id


def update_authorized_user(user_id, email, role):
    email = normalize_email(email)
    role = normalize_role(role)
    timestamp = get_utc_timestamp()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE authorized_users
        SET
            email = ?,
            role = ?,
            updated_at = ?
        WHERE id = ?
    """, (
        email,
        role,
        timestamp,
        user_id,
    ))

    updated = cursor.rowcount > 0

    if updated:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return updated


def delete_authorized_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM authorized_users
        WHERE id = ?
    """, (
        user_id,
    ))

    deleted = cursor.rowcount > 0

    if deleted:
        mark_local_data_modified(cursor)

    conn.commit()
    conn.close()

    return deleted


def normalize_email(email):
    return str(email or "").strip().lower()


def normalize_role(role):
    return str(role or "").strip() or "User"
