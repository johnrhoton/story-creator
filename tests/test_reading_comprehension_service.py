import json
import unittest

from prompts import build_reading_comprehension_prompt
from services.reading_comprehension_service import (
    build_reading_comprehension_table,
    parse_reading_comprehension_response,
    reading_comprehension_to_csv,
)


class ReadingComprehensionServiceTests(unittest.TestCase):
    def test_build_prompt_includes_optional_question_language(self):
        prompt = build_reading_comprehension_prompt(
            "Iris sees the light.",
            question_count=15,
            source_language="English",
            question_language="German",
            text_type="chapter 1"
        )

        self.assertIn("Create 15 questions", prompt)
        self.assertIn("Original textual language:\nEnglish", prompt)
        self.assertIn("Question language:\nGerman", prompt)
        self.assertIn("Iris sees the light.", prompt)

    def test_build_prompt_omits_translation_when_language_absent(self):
        prompt = build_reading_comprehension_prompt(
            "Iris sees the light.",
            question_count=3,
            source_language="English",
            question_language="",
        )

        self.assertIn("Do not include translated_question values", prompt)

    def test_parse_reading_comprehension_response_accepts_valid_json(self):
        response = json.dumps({
            "questions": [
                {
                    "question": "What does Iris see?",
                    "answer": "Iris sees the light.",
                    "translated_question": "Was sieht Iris?",
                }
            ]
        })

        questions = parse_reading_comprehension_response(response)

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["question"], "What does Iris see?")
        self.assertEqual(questions[0]["answer"], "Iris sees the light.")
        self.assertEqual(
            questions[0]["translated_question"],
            "Was sieht Iris?"
        )

    def test_parse_reading_comprehension_response_rejects_invalid_json(self):
        self.assertEqual(parse_reading_comprehension_response("not json"), [])

    def test_reading_comprehension_csv_uses_optional_translation_column(self):
        questions = [
            {
                "question": "What does Iris see?",
                "answer": "Iris sees the light.",
                "translated_question": "Was sieht Iris?",
            }
        ]

        without_translation = reading_comprehension_to_csv(
            questions,
            include_translation=False
        )
        with_translation = reading_comprehension_to_csv(
            questions,
            include_translation=True
        )

        self.assertIn("question,answer", without_translation)
        self.assertNotIn("translated_question", without_translation)
        self.assertIn("question,answer,translated_question", with_translation)
        self.assertIn("Was sieht Iris?", with_translation)

    def test_reading_comprehension_table_uses_optional_translation_column(self):
        rows = build_reading_comprehension_table(
            [
                {
                    "question": "What happens?",
                    "answer": "The mirror breaks.",
                    "translated_question": "Was passiert?",
                }
            ],
            include_translation=True
        )

        self.assertEqual(
            rows,
            [
                {
                    "question": "What happens?",
                    "answer": "The mirror breaks.",
                    "translated_question": "Was passiert?",
                }
            ]
        )


if __name__ == "__main__":
    unittest.main()
