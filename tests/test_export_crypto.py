import unittest

from database.export_crypto import (
    ENCRYPTION_METADATA_KEY,
    ENCRYPTED_VALUE_PREFIX_V2,
    decrypt_export_values,
    encrypt_export_values,
    is_encrypted_value,
)


class ExportCryptoTests(unittest.TestCase):
    def test_encrypt_export_values_encrypts_values_not_keys(self):
        export_data = {
            "characters": [
                {
                    "id": 1,
                    "name": "Alice",
                    "age": "18",
                    "summary": None
                }
            ]
        }

        encrypted_data = encrypt_export_values(
            export_data,
            "password"
        )

        self.assertIn("characters", encrypted_data)
        self.assertIn(ENCRYPTION_METADATA_KEY, encrypted_data)
        self.assertIn("name", encrypted_data["characters"][0])
        self.assertEqual(
            encrypted_data[ENCRYPTION_METADATA_KEY]["version"],
            2
        )
        self.assertTrue(
            is_encrypted_value(encrypted_data["characters"][0]["name"])
        )
        self.assertTrue(
            encrypted_data["characters"][0]["name"].startswith(
                ENCRYPTED_VALUE_PREFIX_V2
            )
        )
        self.assertTrue(
            is_encrypted_value(encrypted_data["characters"][0]["id"])
        )
        self.assertTrue(
            is_encrypted_value(encrypted_data["characters"][0]["summary"])
        )
        self.assertNotEqual(encrypted_data, export_data)

    def test_decrypt_export_values_round_trips_original_types(self):
        export_data = {
            "exported_at": "2026-05-14T12:00:00",
            "characters": [
                {
                    "id": 1,
                    "name": "Alice",
                    "active": True,
                    "summary": None
                }
            ]
        }

        encrypted_data = encrypt_export_values(
            export_data,
            "password"
        )

        self.assertEqual(
            decrypt_export_values(encrypted_data, "password"),
            export_data
        )

    def test_empty_password_leaves_data_unchanged_copy(self):
        export_data = {
            "characters": [
                {
                    "name": "Alice"
                }
            ]
        }

        encrypted_data = encrypt_export_values(export_data, "")
        decrypted_data = decrypt_export_values(export_data, "")

        self.assertEqual(encrypted_data, export_data)
        self.assertEqual(decrypted_data, export_data)
        self.assertIsNot(encrypted_data, export_data)
        self.assertIsNot(decrypted_data, export_data)

    def test_wrong_password_raises_clear_error(self):
        encrypted_data = encrypt_export_values(
            {
                "characters": [
                    {
                        "name": "Alice"
                    }
                ]
            },
            "correct"
        )

        with self.assertRaisesRegex(ValueError, "Check the export password"):
            decrypt_export_values(encrypted_data, "wrong")

    def test_plain_values_pass_through_during_decryption(self):
        export_data = {
            "characters": [
                {
                    "name": "Alice"
                }
            ]
        }

        self.assertEqual(
            decrypt_export_values(export_data, "password"),
            export_data
        )


if __name__ == "__main__":
    unittest.main()
