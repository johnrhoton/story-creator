import csv
import io
import json

import streamlit as st

from config import DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER
from llm_client import generate_text
from prompts import build_glossary_prompt


def generate_glossary(
    source_text,
    dictionary_languages,
    entry_count=15,
    text_type="story section",
    source_language=""
):
    languages = normalize_dictionary_languages(dictionary_languages)

    if not source_text or not str(source_text).strip() or not languages:
        return []

    prompt = build_glossary_prompt(
        source_text=source_text,
        dictionary_languages=languages,
        entry_count=entry_count,
        text_type=text_type,
        source_language=source_language,
    )
    response_text = generate_text(
        st.session_state.get("llm_provider", DEFAULT_LLM_PROVIDER),
        st.session_state.get("llm_model", DEFAULT_LLM_MODEL),
        prompt
    )

    return parse_glossary_response(response_text or "", languages)


def parse_glossary_response(response_text, dictionary_languages=None):
    if not response_text or not response_text.strip():
        return []

    try:
        payload = json.loads(strip_json_fence(response_text))
    except json.JSONDecodeError:
        return []

    if isinstance(payload, dict):
        entries = payload.get("entries")
    elif isinstance(payload, list):
        entries = payload
    else:
        entries = None

    if not isinstance(entries, list):
        return []

    languages = normalize_dictionary_languages(dictionary_languages or [])
    parsed = []
    seen = set()

    for entry in entries:
        normalized = normalize_glossary_entry(entry, languages)
        if not normalized:
            continue

        headword_key = normalized["headword"].casefold()
        if headword_key in seen:
            continue

        seen.add(headword_key)
        parsed.append(normalized)

    return parsed


def normalize_glossary_entry(entry, dictionary_languages):
    if not isinstance(entry, dict):
        return None

    headword = str(entry.get("headword") or "").strip()
    if not headword:
        return None

    translations = entry.get("translations") or {}
    if not isinstance(translations, dict):
        translations = {}

    normalized_translations = {}
    for language in dictionary_languages:
        normalized_translations[language] = str(
            translations.get(language) or ""
        ).strip()

    return {
        "headword": headword,
        "translations": normalized_translations,
    }


def glossary_entries_to_csv(entries, dictionary_languages):
    languages = normalize_dictionary_languages(dictionary_languages)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["headword", *languages])

    for entry in entries or []:
        translations = entry.get("translations") or {}
        writer.writerow([
            entry.get("headword") or "",
            *[
                translations.get(language, "")
                for language in languages
            ],
        ])

    return output.getvalue()


def build_glossary_table(entries, dictionary_languages):
    languages = normalize_dictionary_languages(dictionary_languages)
    rows = []

    for entry in entries or []:
        translations = entry.get("translations") or {}
        row = {
            "headword": entry.get("headword") or "",
        }

        for language in languages:
            row[language] = translations.get(language, "")

        rows.append(row)

    return rows


def normalize_dictionary_languages(dictionary_languages):
    if isinstance(dictionary_languages, str):
        values = dictionary_languages.split(",")
    else:
        values = dictionary_languages or []

    return [
        str(value).strip()
        for value in values
        if str(value).strip()
    ]


def strip_json_fence(response_text):
    text = response_text.strip()

    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) >= 3:
            return "\n".join(lines[1:-1]).strip()

    return text
