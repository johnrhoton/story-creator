import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from database.load_seed import (
    database_is_empty_for_seed,
    seed_database_from_load_folder,
)
from database.migrations import run_migrations
from database.profiles import get_profiles
from database.schema import create_tables


@contextmanager
def isolated_database_directory():
    original_cwd = Path.cwd()

    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)

        try:
            yield Path(temp_dir)
        finally:
            os.chdir(original_cwd)


class LoadSeedTests(unittest.TestCase):
    def test_seed_database_from_load_folder_imports_into_empty_database_once(self):
        with isolated_database_directory() as temp_dir:
            load_dir = temp_dir / "load"
            load_dir.mkdir()
            (load_dir / "profiles.yaml").write_text(
                """
profiles:
  - profile_name: Explorer
    gender: female
    physical_traits: curious eyes
    personality_traits: brave
    notes: seed profile
""".strip(),
                encoding="utf-8",
            )

            run_migrations()
            create_tables()

            self.assertTrue(database_is_empty_for_seed())

            first_counts = seed_database_from_load_folder()
            second_counts = seed_database_from_load_folder()

            self.assertEqual(first_counts["load/profiles.yaml"]["profiles"], 1)
            self.assertEqual(second_counts, {})
            self.assertFalse(database_is_empty_for_seed())
            self.assertEqual(len(get_profiles()), 1)

    def test_seed_database_from_load_folder_ignores_missing_load_folder(self):
        with isolated_database_directory():
            run_migrations()
            create_tables()

            self.assertEqual(seed_database_from_load_folder(), {})
