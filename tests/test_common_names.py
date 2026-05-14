import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from database.characters import save_character
from database.common_names import (
    age_to_name_index,
    character_name_exists,
    find_nearest_free_name,
    get_common_names,
    seed_common_names,
    suggest_character_name,
)
from database.migrations import run_migrations
from database.schema import create_tables


@contextmanager
def isolated_database_directory():
    original_cwd = Path.cwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        try:
            run_migrations()
            create_tables()
            seed_common_names()
            yield Path(temp_dir)
        finally:
            os.chdir(original_cwd)


class CommonNameTests(unittest.TestCase):
    def test_age_to_name_index_handles_boundaries_and_invalid_values(self):
        self.assertEqual(age_to_name_index(5, 10), 0)
        self.assertEqual(age_to_name_index(60, 10), 9)
        self.assertEqual(age_to_name_index(1, 10), 0)
        self.assertEqual(age_to_name_index(100, 10), 9)
        self.assertEqual(
            age_to_name_index("not a number", 10),
            age_to_name_index(18, 10)
        )
        self.assertEqual(age_to_name_index(18, 1), 0)

    def test_find_nearest_free_name_prefers_target_then_next_then_previous(self):
        names = [
            (1, "Alice"),
            (2, "Beatrice"),
            (3, "Clara"),
            (4, "Daisy"),
        ]

        self.assertEqual(
            find_nearest_free_name(names, 1, set()),
            "Beatrice"
        )
        self.assertEqual(
            find_nearest_free_name(names, 1, {"beatrice"}),
            "Clara"
        )
        self.assertEqual(
            find_nearest_free_name(
                names,
                1,
                {"beatrice", "clara", "alice"}
            ),
            "Daisy"
        )
        self.assertIsNone(
            find_nearest_free_name(
                names,
                1,
                {"alice", "beatrice", "clara", "daisy"}
            )
        )

    def test_seed_common_names_is_idempotent(self):
        with isolated_database_directory():
            first_count = len(get_common_names("female"))

            seed_common_names()

            self.assertEqual(len(get_common_names("female")), first_count)
            self.assertGreater(first_count, 0)

    def test_character_name_exists_ignores_case_and_spacing(self):
        with isolated_database_directory():
            save_character(
                None,
                " Alice ",
                "18",
                "female",
                "quick",
                "curious",
                "note",
                "prompt",
                "response",
                "summary"
            )

            self.assertTrue(character_name_exists("alice"))
            self.assertTrue(character_name_exists(" ALICE "))
            self.assertFalse(character_name_exists("Beatrice"))

    def test_suggest_character_name_skips_existing_names(self):
        with isolated_database_directory():
            suggested_name = suggest_character_name(18, "female")

            save_character(
                None,
                suggested_name,
                "18",
                "female",
                "quick",
                "curious",
                "note",
                "prompt",
                "response",
                "summary"
            )

            self.assertNotEqual(
                suggest_character_name(18, "female"),
                suggested_name
            )

    def test_suggest_character_name_returns_empty_for_unknown_gender(self):
        with isolated_database_directory():
            self.assertEqual(
                suggest_character_name(18, "unknown"),
                ""
            )


if __name__ == "__main__":
    unittest.main()
