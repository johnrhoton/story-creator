import unittest

from ui_helpers import (
    append_profile_data_to_character,
    build_character_header,
    combine_profile_defaults,
    format_display_timestamp,
)


class UiHelperTests(unittest.TestCase):
    def test_format_display_timestamp_replaces_iso_separator(self):
        self.assertEqual(
            format_display_timestamp("2026-05-14T12:34:56+00:00"),
            "2026-05-14 12:34:56+00:00"
        )
        self.assertEqual(format_display_timestamp(None), "")
        self.assertEqual(format_display_timestamp(""), "")

    def test_combine_profile_defaults_uses_selected_profiles(self):
        profiles = [
            ("hero", "female", "athletic", "brave", "leads"),
            ("mentor", "male", "older", "patient", "guides"),
        ]

        defaults = combine_profile_defaults(
            ["hero", "mentor"],
            profiles
        )

        self.assertEqual(defaults["name"], "")
        self.assertEqual(defaults["age"], "")
        self.assertEqual(defaults["gender"], "male")
        self.assertEqual(defaults["physical_traits"], "athletic, older")
        self.assertEqual(defaults["personality_traits"], "brave, patient")
        self.assertEqual(defaults["notes"], "leads, guides")
        self.assertEqual(defaults["profile_name"], "hero, mentor")

    def test_combine_profile_defaults_falls_back_when_selection_is_empty(self):
        defaults = combine_profile_defaults(
            [],
            [
                ("hero", "female", "athletic", "brave", "leads")
            ]
        )

        self.assertEqual(defaults["gender"], "female")
        self.assertEqual(defaults["physical_traits"], "")
        self.assertEqual(defaults["profile_name"], None)

    def test_combine_profile_defaults_ignores_unknown_selection(self):
        defaults = combine_profile_defaults(
            ["missing"],
            [
                ("hero", "female", "athletic", "brave", "leads")
            ]
        )

        self.assertEqual(defaults["gender"], "female")
        self.assertEqual(defaults["personality_traits"], "")
        self.assertEqual(defaults["profile_name"], None)

    def test_append_profile_data_to_character_preserves_existing_text_first(self):
        profile_name, physical, personality, notes = (
            append_profile_data_to_character(
                ["hero", "mentor"],
                [
                    ("hero", "female", "athletic", "brave", "leads"),
                    ("mentor", "male", "older", "patient", "guides"),
                ],
                "scarred",
                "curious",
                "existing note"
            )
        )

        self.assertEqual(profile_name, "hero, mentor")
        self.assertEqual(physical, "scarred, athletic, older")
        self.assertEqual(personality, "curious, brave, patient")
        self.assertEqual(notes, "existing note, leads, guides")

    def test_build_character_header_uses_available_parts(self):
        self.assertEqual(
            build_character_header("Alice", "18", "hero"),
            "Alice — 18 — hero"
        )
        self.assertEqual(
            build_character_header("", "", None),
            "Unnamed character"
        )


if __name__ == "__main__":
    unittest.main()
