import base64
import copy
import json
import os
import zlib

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


ENCRYPTION_METADATA_KEY = "__export_encryption"
ENCRYPTED_VALUE_PREFIX_V1 = "encrypted:v1:"
ENCRYPTED_VALUE_PREFIX_V2 = "encrypted:v2:"
ENCRYPTED_VALUE_PREFIX = ENCRYPTED_VALUE_PREFIX_V2
SALT_BYTES = 16
KDF_ITERATIONS = 390000


def encrypt_export_values(data, password):
    if not password:
        return copy.deepcopy(data)

    salt = os.urandom(SALT_BYTES)
    fernet = build_fernet(password, salt)

    encrypted_data = transform_export_values(
        data,
        lambda value: encrypt_value(value, fernet)
    )

    encrypted_data[ENCRYPTION_METADATA_KEY] = {
        "version": 2,
        "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
        "kdf": "PBKDF2HMAC-SHA256",
        "iterations": KDF_ITERATIONS
    }

    return encrypted_data


def decrypt_export_values(data, password):
    if not password:
        return copy.deepcopy(data)

    fernet = None
    data_to_decrypt = data

    if isinstance(data, dict) and ENCRYPTION_METADATA_KEY in data:
        metadata = data[ENCRYPTION_METADATA_KEY]
        salt = base64.urlsafe_b64decode(metadata["salt"].encode("ascii"))
        fernet = build_fernet(password, salt)
        data_to_decrypt = {
            key: value
            for key, value in data.items()
            if key != ENCRYPTION_METADATA_KEY
        }

    return transform_export_values(
        data_to_decrypt,
        lambda value: decrypt_value_if_needed(value, password, fernet)
    )


def transform_export_values(value, transform_scalar):
    if isinstance(value, dict):
        return {
            key: transform_export_values(child_value, transform_scalar)
            for key, child_value in value.items()
        }

    if isinstance(value, list):
        return [
            transform_export_values(child_value, transform_scalar)
            for child_value in value
        ]

    return transform_scalar(value)


def encrypt_value(value, fernet):
    value_json = json.dumps(
        value,
        ensure_ascii=False
    ).encode("utf-8")

    compressed_value = zlib.compress(value_json)
    encrypted_value = fernet.encrypt(compressed_value)

    return f"{ENCRYPTED_VALUE_PREFIX_V2}{encrypted_value.decode('ascii')}"


def decrypt_value_if_needed(value, password, fernet=None):
    if not is_encrypted_value(value):
        return value

    if value.startswith(ENCRYPTED_VALUE_PREFIX_V2):
        if fernet is None:
            raise ValueError(
                "Could not decrypt export value. Check the export password."
            )

        encrypted_value = value.removeprefix(
            ENCRYPTED_VALUE_PREFIX_V2
        ).encode("ascii")

        try:
            compressed_value = fernet.decrypt(encrypted_value)
            value_json = zlib.decompress(compressed_value)

            return json.loads(value_json.decode("utf-8"))

        except (ValueError, InvalidToken, zlib.error) as error:
            raise ValueError(
                "Could not decrypt export value. Check the export password."
            ) from error

    encoded_payload = value.removeprefix(ENCRYPTED_VALUE_PREFIX_V1)

    try:
        payload_json = base64.urlsafe_b64decode(
            encoded_payload.encode("ascii")
        )
        payload = json.loads(payload_json.decode("utf-8"))
        salt = base64.urlsafe_b64decode(payload["salt"].encode("ascii"))
        encrypted_value = payload["value"].encode("ascii")

        fernet = build_fernet(password, salt)
        compressed_value = fernet.decrypt(encrypted_value)
        value_json = zlib.decompress(compressed_value)

        return json.loads(value_json.decode("utf-8"))

    except (KeyError, ValueError, InvalidToken, zlib.error) as error:
        raise ValueError(
            "Could not decrypt export value. Check the export password."
        ) from error


def is_encrypted_value(value):
    return (
        isinstance(value, str)
        and (
            value.startswith(ENCRYPTED_VALUE_PREFIX_V1)
            or value.startswith(ENCRYPTED_VALUE_PREFIX_V2)
        )
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
