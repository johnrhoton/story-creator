import json
import unittest

from prompts import build_glossary_prompt
from services.glossary_service import (
    build_glossary_table,
    glossary_entries_to_csv,
    normalize_dictionary_languages,
    parse_glossary_response,
)
from views.glossary_view import build_glossary_url, resolve_glossary_source


class GlossaryServiceTests(unittest.TestCase):
    def test_build_glossary_prompt_includes_languages_and_count(self):
        prompt = build_glossary_prompt(
            "The mirrors were broken.",
            ["German", "Spanish"],
            entry_count=15,
            text_type="chapter 2",
            source_language="English"
        )

        self.assertIn("Select 15", prompt)
        self.assertIn("Source/story language:\nEnglish", prompt)
        self.assertIn("headword must be in the same language", prompt)
        self.assertIn("German, Spanish", prompt)
        self.assertIn("chapter 2", prompt)
        self.assertIn("The mirrors were broken.", prompt)

    def test_parse_glossary_response_accepts_valid_json(self):
        response = json.dumps({
            "entries": [
                {
                    "headword": "mirror",
                    "translations": {
                        "German": "der Spiegel",
                        "Spanish": "el espejo",
                    },
                },
                {
                    "headword": "break",
                    "translations": {
                        "German": "brechen/zerbrechen",
                        "Spanish": "romper",
                    },
                },
            ]
        })

        entries = parse_glossary_response(
            response,
            ["German", "Spanish"]
        )

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["headword"], "mirror")
        self.assertEqual(
            entries[1]["translations"]["German"],
            "brechen/zerbrechen"
        )

    def test_parse_glossary_response_rejects_invalid_json(self):
        self.assertEqual(parse_glossary_response("not json", ["German"]), [])

    def test_glossary_entries_to_csv_uses_language_columns(self):
        csv_data = glossary_entries_to_csv(
            [
                {
                    "headword": "mirror",
                    "translations": {
                        "German": "der Spiegel",
                        "Spanish": "el espejo",
                    },
                }
            ],
            ["German", "Spanish"]
        )

        self.assertIn("headword,German,Spanish", csv_data)
        self.assertIn("mirror,der Spiegel,el espejo", csv_data)

    def test_normalize_dictionary_languages_splits_commas(self):
        self.assertEqual(
            normalize_dictionary_languages("German, Spanish, French"),
            ["German", "Spanish", "French"]
        )

    def test_build_glossary_table_uses_language_columns(self):
        rows = build_glossary_table(
            [
                {
                    "headword": "break",
                    "translations": {"German": "brechen"},
                }
            ],
            ["German"]
        )

        self.assertEqual(rows, [{"headword": "break", "German": "brechen"}])

    def test_build_glossary_url_supports_story_and_chapter(self):
        self.assertEqual(
            build_glossary_url(7),
            "?view=Glossary&story_id=7"
        )
        self.assertEqual(
            build_glossary_url(7, 3),
            "?view=Glossary&story_id=7&chapter_number=3"
        )

    def test_resolve_glossary_source_supports_full_story_and_chapter(self):
        chapters = [
            (1, 7, 1, "Opening", "One two", "summary"),
            (2, 7, 2, "Next", "Three four", "summary"),
        ]

        full_text, full_type, full_file = resolve_glossary_source(
            7,
            "Full story",
            chapters
        )
        chapter_text, chapter_type, chapter_file = resolve_glossary_source(
            7,
            2,
            chapters
        )

        self.assertIn("One two", full_text)
        self.assertEqual(full_type, "full story")
        self.assertEqual(full_file, "story_7_glossary.csv")
        self.assertEqual(chapter_text, "Three four")
        self.assertEqual(chapter_type, "chapter 2")
        self.assertEqual(chapter_file, "story_7_chapter_2_glossary.csv")


if __name__ == "__main__":
    unittest.main()
