import csv
import io
import json

import streamlit as st

from config import DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER
from llm_client import generate_text
from prompts import build_reading_comprehension_prompt
from services.glossary_service import strip_json_fence


def generate_reading_comprehension_questions(
    source_text,
    question_count=15,
    source_language="",
    interrogative_language="",
    text_type="story section"
):
    if not source_text or not str(source_text).strip():
        return []

    prompt = build_reading_comprehension_prompt(
        source_text=source_text,
        question_count=question_count,
        source_language=source_language,
        interrogative_language=interrogative_language,
        text_type=text_type,
    )
    response_text = generate_text(
        st.session_state.get("llm_provider", DEFAULT_LLM_PROVIDER),
        st.session_state.get("llm_model", DEFAULT_LLM_MODEL),
        prompt
    )

    return parse_reading_comprehension_response(response_text or "")


def parse_reading_comprehension_response(response_text):
    if not response_text or not response_text.strip():
        return []

    try:
        payload = json.loads(strip_json_fence(response_text))
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        questions = payload.get("questions")
    elif isinstance(payload, list):
        questions = payload
    else:
        questions = None

    if not isinstance(questions, list):
        return []

    parsed = []

    for question in questions:
        normalized = normalize_reading_comprehension_question(question)
        if normalized:
            parsed.append(normalized)

    return parsed


def normalize_reading_comprehension_question(question):
    if not isinstance(question, dict):
        return None

    question_text = str(question.get("question") or "").strip()
    answer = str(question.get("answer") or "").strip()

    if not question_text or not answer:
        return None

    return {
        "question": question_text,
        "answer": answer,
        "translated_question": str(
            question.get("translated_question") or ""
        ).strip(),
    }


def reading_comprehension_to_csv(questions, include_translation=False):
    output = io.StringIO()
    writer = csv.writer(output)
    headers = ["question", "answer"]

    if include_translation:
        headers.append("translated_question")

    writer.writerow(headers)

    for question in questions or []:
        row = [
            question.get("question") or "",
            question.get("answer") or "",
        ]

        if include_translation:
            row.append(question.get("translated_question") or "")

        writer.writerow(row)

    return output.getvalue()


def build_reading_comprehension_table(
    questions,
    include_translation=False
):
    rows = []

    for question in questions or []:
        row = {
            "question": question.get("question") or "",
            "answer": question.get("answer") or "",
        }

        if include_translation:
            row["translated_question"] = (
                question.get("translated_question") or ""
            )

        rows.append(row)

    return rows
