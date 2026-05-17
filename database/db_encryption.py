import base64
import copy
import hashlib
import json
import os
import zlib

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import DATABASE_ENCRYPTION_KDF_ITERATIONS
from database.connection import get_connection
from database.metadata import (
    get_metadata_value,
    mark_local_data_modified,
    set_metadata_value,
)


DATABASE_ENCRYPTION_ENABLED = "database_encryption_enabled"
DATABASE_ENCRYPTION_ITERATIONS = "database_encryption_iterations"
DATABASE_ENCRYPTION_SALT = "database_encryption_salt"
DATABASE_ENCRYPTION_VERIFIER = "database_encryption_verifier"
DATABASE_ENCRYPTION_EXPORT_KEY = "__database_encryption"
DATABASE_ENCRYPTED_VALUE_PREFIX_V1 = "db-encrypted:v1:"
DATABASE_ENCRYPTED_VALUE_PREFIX_V2 = "db-encrypted:v2:"
DATABASE_ENCRYPTED_VALUE_PREFIX = DATABASE_ENCRYPTED_VALUE_PREFIX_V2
DATABASE_ENCRYPTION_VERIFIER_VALUE = "story-builder-database-encryption"
SALT_BYTES = 16
LEGACY_KDF_ITERATIONS = 390000

ENCRYPTED_TABLE_FIELDS = {
    "characters": {
        "profile_name",
        "physical_traits",
        "personality_traits",
        "notes",
        "prompt",
        "response",
        "summary",
    },
    "profiles": {
        "profile_name",
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
        "additional_instructions",
        "language",
        "language_level",
    },
    "story_chapters": {
        "chapter_description",
        "chapter_body",
        "chapter_summary",
    },
    "story_beats": {
        "title",
        "characters",
        "location",
        "time_span",
        "summary",
        "continuity_effect",
        "unresolved_threads",
        "search_keywords",
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
    "object_history": {
        "contents",
    },
}

DECRYPT_TABLE_FIELDS = {
    table_name: set(field_names)
    for table_name, field_names in ENCRYPTED_TABLE_FIELDS.items()
}

DECRYPT_TABLE_FIELDS["characters"].update({
    "physical_traits",
    "personality_traits",
})
DECRYPT_TABLE_FIELDS["profiles"].update({
    "physical_traits",
    "personality_traits",
})
DECRYPT_TABLE_FIELDS["story_templates"].add("tone_style")
DECRYPT_TABLE_FIELDS["stories"].update({
    "tone_style",
    "additional_instructions",
    "language",
    "language_level",
    "male_characters",
    "female_characters",
})
DECRYPT_TABLE_FIELDS["story_chapters"].add("chapter_description")

_active_fernet = None
_active_password_signature = None


def set_active_database_password(password):
    global _active_fernet
    global _active_password_signature

    if not password:
        _active_fernet = None
        _active_password_signature = None
        return

    salt = get_or_create_database_encryption_salt()
    iterations = get_database_encryption_iterations()
    password_signature = build_password_signature(
        password,
        salt,
        iterations
    )

    if _active_password_signature == password_signature and _active_fernet:
        return

    fernet = build_fernet(
        password,
        salt,
        iterations
    )

    if not database_password_matches_verifier(fernet):
        _active_fernet = None
        _active_password_signature = None
        return

    _active_fernet = fernet
    _active_password_signature = password_signature


def get_database_encryption_status():
    return {
        "enabled": is_database_encryption_enabled(),
        "unlocked": _active_fernet is not None,
    }


def get_database_encryption_export_metadata():
    if not is_database_encryption_enabled():
        return None

    return {
        "version": 1,
        "salt": get_metadata_value(DATABASE_ENCRYPTION_SALT),
        "kdf": "PBKDF2HMAC-SHA256",
        "iterations": get_database_encryption_iterations(),
        "value_prefix": DATABASE_ENCRYPTED_VALUE_PREFIX,
        "verifier": get_metadata_value(DATABASE_ENCRYPTION_VERIFIER),
    }


def apply_database_encryption_export_metadata(metadata, cursor):
    global _active_fernet
    global _active_password_signature

    if not metadata:
        return

    if metadata.get("version") != 1 or not metadata.get("salt"):
        raise ValueError("Unsupported database encryption metadata.")

    set_metadata_value(cursor, DATABASE_ENCRYPTION_ENABLED, "true")
    set_metadata_value(cursor, DATABASE_ENCRYPTION_SALT, metadata["salt"])
    set_metadata_value(
        cursor,
        DATABASE_ENCRYPTION_ITERATIONS,
        str(metadata.get("iterations") or LEGACY_KDF_ITERATIONS)
    )

    if metadata.get("verifier"):
        set_metadata_value(
            cursor,
            DATABASE_ENCRYPTION_VERIFIER,
            metadata["verifier"]
        )

    _active_fernet = None
    _active_password_signature = None


def is_database_encryption_enabled():
    return get_metadata_value(DATABASE_ENCRYPTION_ENABLED) == "true"


def enable_database_encryption(password):
    if not password:
        raise ValueError("A database encryption password is required.")

    initialize_database_encryption(password)

    conn = get_connection()
    cursor = conn.cursor()

    for table_name, field_names in ENCRYPTED_TABLE_FIELDS.items():
        encrypt_table_fields(cursor, table_name, field_names)

    mark_local_data_modified(cursor)

    conn.commit()
    conn.close()


def initialize_database_encryption(password):
    if not password:
        raise ValueError("A database encryption password is required.")

    conn = get_connection()
    cursor = conn.cursor()

    set_metadata_value(cursor, DATABASE_ENCRYPTION_ENABLED, "true")
    set_metadata_value(
        cursor,
        DATABASE_ENCRYPTION_ITERATIONS,
        str(DATABASE_ENCRYPTION_KDF_ITERATIONS)
    )
    conn.commit()
    conn.close()

    set_active_database_password(password)

    conn = get_connection()
    cursor = conn.cursor()
    set_database_encryption_verifier(cursor)
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


def get_database_encryption_iterations():
    iterations = get_metadata_value(DATABASE_ENCRYPTION_ITERATIONS)

    if not iterations:
        return LEGACY_KDF_ITERATIONS

    try:
        return int(iterations)
    except ValueError:
        return LEGACY_KDF_ITERATIONS


def database_password_matches_verifier(fernet):
    verifier = get_metadata_value(DATABASE_ENCRYPTION_VERIFIER)

    if not verifier:
        return True

    try:
        return (
            decrypt_database_value_with_fernet(verifier, fernet)
            == DATABASE_ENCRYPTION_VERIFIER_VALUE
        )
    except ValueError:
        return False


def set_database_encryption_verifier(cursor):
    set_metadata_value(
        cursor,
        DATABASE_ENCRYPTION_VERIFIER,
        encrypt_database_value(DATABASE_ENCRYPTION_VERIFIER_VALUE)
    )


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

    for field_name in DECRYPT_TABLE_FIELDS.get(table_name, set()):
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

    encrypted_value = _active_fernet.encrypt(value_json)

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

    return decrypt_database_value_with_fernet(value, _active_fernet)


def decrypt_database_value_with_fernet(value, fernet):
    try:
        if value.startswith(DATABASE_ENCRYPTED_VALUE_PREFIX_V2):
            encrypted_value = value.removeprefix(
                DATABASE_ENCRYPTED_VALUE_PREFIX_V2
            ).encode("ascii")
            value_json = fernet.decrypt(encrypted_value)
        else:
            encrypted_value = value.removeprefix(
                DATABASE_ENCRYPTED_VALUE_PREFIX_V1
            ).encode("ascii")
            compressed_value = fernet.decrypt(encrypted_value)
            value_json = zlib.decompress(compressed_value)

        return json.loads(value_json.decode("utf-8"))

    except (ValueError, InvalidToken, zlib.error) as error:
        raise ValueError(
            "Could not decrypt database value. Check the database password."
        ) from error


def is_database_encrypted_value(value):
    return (
        isinstance(value, str)
        and (
            value.startswith(DATABASE_ENCRYPTED_VALUE_PREFIX_V1)
            or value.startswith(DATABASE_ENCRYPTED_VALUE_PREFIX_V2)
        )
    )


def build_fernet(password, salt, iterations):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )

    key = base64.urlsafe_b64encode(
        kdf.derive(password.encode("utf-8"))
    )

    return Fernet(key)


def build_password_signature(password, salt, iterations):
    return hashlib.sha256(
        salt
        + str(iterations).encode("ascii")
        + password.encode("utf-8")
    ).hexdigest()
