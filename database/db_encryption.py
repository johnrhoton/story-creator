import base64
import copy
import json
import os
import zlib

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from database.connection import get_connection
from database.metadata import (
    get_metadata_value,
    mark_local_data_modified,
    set_metadata_value,
)


DATABASE_ENCRYPTION_ENABLED = "database_encryption_enabled"
DATABASE_ENCRYPTION_SALT = "database_encryption_salt"
DATABASE_ENCRYPTED_VALUE_PREFIX = "db-encrypted:v1:"
SALT_BYTES = 16
KDF_ITERATIONS = 390000

ENCRYPTED_TABLE_FIELDS = {
    "characters": {
        "physical_traits",
        "personality_traits",
        "notes",
        "prompt",
        "response",
        "summary",
    },
    "profiles": {
        "physical_traits",
        "personality_traits",
        "notes",
    },
    "story_templates": {
        "overview",
        "setting_background",
        "tone_style",
    },
    "story_template_chapters": {
        "chapter_description",
    },
    "stories": {
        "overview",
        "setting_background",
        "tone_style",
        "male_characters",
        "female_characters",
    },
    "story_chapters": {
        "chapter_description",
        "chapter_body",
        "chapter_summary",
    },
    "llm_calls": {
        "prompt",
        "response",
    },
    "failed_llm_calls": {
        "prompt",
        "response",
        "error_message",
        "error_details",
    },
}

_active_fernet = None


def set_active_database_password(password):
    global _active_fernet

    if not password:
        _active_fernet = None
        return

    salt = get_or_create_database_encryption_salt()
    _active_fernet = build_fernet(password, salt)


def get_database_encryption_status():
    return {
        "enabled": is_database_encryption_enabled(),
        "unlocked": _active_fernet is not None,
    }


def is_database_encryption_enabled():
    return get_metadata_value(DATABASE_ENCRYPTION_ENABLED) == "true"


def enable_database_encryption(password):
    if not password:
        raise ValueError("A database encryption password is required.")

    set_active_database_password(password)

    conn = get_connection()
    cursor = conn.cursor()

    set_metadata_value(cursor, DATABASE_ENCRYPTION_ENABLED, "true")
    conn.commit()

    for table_name, field_names in ENCRYPTED_TABLE_FIELDS.items():
        encrypt_table_fields(cursor, table_name, field_names)

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def encrypt_table_fields(cursor, table_name, field_names):
    cursor.execute(f"SELECT id, {', '.join(field_names)} FROM {table_name}")

    columns = [
        column[0]
        for column in cursor.description
    ]

    for row in cursor.fetchall():
        row_data = dict(zip(columns, row))
        encrypted_values = {
            field_name: encrypt_database_value(row_data[field_name])
            for field_name in field_names
        }

        assignments = ", ".join(
            f"{field_name} = ?"
            for field_name in encrypted_values
        )

        cursor.execute(
            f"UPDATE {table_name} SET {assignments} WHERE id = ?",
            tuple(encrypted_values.values()) + (row_data["id"],)
        )


def get_or_create_database_encryption_salt():
    existing_salt = get_metadata_value(DATABASE_ENCRYPTION_SALT)

    if existing_salt:
        return base64.urlsafe_b64decode(existing_salt.encode("ascii"))

    salt = os.urandom(SALT_BYTES)
    encoded_salt = base64.urlsafe_b64encode(salt).decode("ascii")

    conn = get_connection()
    cursor = conn.cursor()
    set_metadata_value(cursor, DATABASE_ENCRYPTION_SALT, encoded_salt)
    conn.commit()
    conn.close()

    return salt


def encrypt_database_row(table_name, row_data):
    encrypted_row = copy.deepcopy(row_data)

    for field_name in ENCRYPTED_TABLE_FIELDS.get(table_name, set()):
        if field_name in encrypted_row:
            encrypted_row[field_name] = encrypt_database_value(
                encrypted_row[field_name]
            )

    return encrypted_row


def encrypt_database_field(table_name, field_name, value):
    if field_name not in ENCRYPTED_TABLE_FIELDS.get(table_name, set()):
        return value

    return encrypt_database_value(value)


def decrypt_database_row(table_name, row_data):
    decrypted_row = copy.deepcopy(row_data)

    for field_name in ENCRYPTED_TABLE_FIELDS.get(table_name, set()):
        if field_name in decrypted_row:
            decrypted_row[field_name] = decrypt_database_value_if_needed(
                decrypted_row[field_name]
            )

    return decrypted_row


def decrypt_database_tuple(table_name, row, columns):
    row_data = dict(zip(columns, row))
    decrypted_row = decrypt_database_row(table_name, row_data)

    return tuple(
        decrypted_row[column]
        for column in columns
    )


def decrypt_database_rows(table_name, rows, columns):
    return [
        decrypt_database_tuple(table_name, row, columns)
        for row in rows
    ]


def encrypt_database_value(value):
    if value is None or is_database_encrypted_value(value):
        return value

    if _active_fernet is None or not is_database_encryption_enabled():
        return value

    value_json = json.dumps(
        value,
        ensure_ascii=False
    ).encode("utf-8")

    compressed_value = zlib.compress(value_json)
    encrypted_value = _active_fernet.encrypt(compressed_value)

    return (
        f"{DATABASE_ENCRYPTED_VALUE_PREFIX}"
        f"{encrypted_value.decode('ascii')}"
    )


def decrypt_database_value_if_needed(value):
    if not is_database_encrypted_value(value):
        return value

    if _active_fernet is None:
        raise ValueError(
            "Database is encrypted. Enter the database password in the "
            "sidebar to unlock it."
        )

    encrypted_value = value.removeprefix(
        DATABASE_ENCRYPTED_VALUE_PREFIX
    ).encode("ascii")

    try:
        compressed_value = _active_fernet.decrypt(encrypted_value)
        value_json = zlib.decompress(compressed_value)

        return json.loads(value_json.decode("utf-8"))

    except (ValueError, InvalidToken, zlib.error) as error:
        raise ValueError(
            "Could not decrypt database value. Check the database password."
        ) from error


def is_database_encrypted_value(value):
    return (
        isinstance(value, str)
        and value.startswith(DATABASE_ENCRYPTED_VALUE_PREFIX)
    )


def build_fernet(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )

    key = base64.urlsafe_b64encode(
        kdf.derive(password.encode("utf-8"))
    )

    return Fernet(key)
