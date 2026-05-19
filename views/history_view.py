import json
import logging

import streamlit as st

from database import get_failed_llm_calls, get_llm_calls, get_object_history
from ui_helpers import format_display_timestamp


logger = logging.getLogger(__name__)


OBJECT_TYPE_OPTIONS = [
    "Characters",
    "Profiles",
    "Templates",
    "Stories",
]

LLM_STATUS_OPTIONS = [
    "Success",
    "Failure",
]


def render_history_tab():
    history_type = st.radio(
        "History type",
        [
            "Objects",
            "LLM calls",
        ],
        horizontal=True,
        key="history_type"
    )

    if history_type == "Objects":
        render_object_history()
    elif history_type == "LLM calls":
        render_llm_history()


def render_object_history():
    st.header("Object history")

    selected_object_types = st.multiselect(
        "Object types",
        OBJECT_TYPE_OPTIONS,
        default=OBJECT_TYPE_OPTIONS,
        key="object_history_types"
    )

    entries = [
        entry
        for entry in build_object_history_entries()
        if entry["object_type"] in selected_object_types
    ]

    if not entries:
        st.info("No object history entries found.")
        return

    for entry in entries:
        with st.expander(build_object_history_label(entry)):
            st.write(f"**Object type:** {entry['object_type']}")
            st.write(f"**ID:** {entry['object_id']}")
            st.write(f"**Name:** {entry['name']}")
            st.write(
                f"**Timestamp:** "
                f"{format_display_timestamp(entry['timestamp'])}"
            )
            st.write(f"**CRUD operation:** {entry['operation']}")
            st.write("**Last contents:**")
            st.json(entry["contents"])


def build_object_history_entries():
    entries = []

    for row in get_object_history():
        (
            record_id,
            created_at,
            object_type,
            object_id,
            object_name,
            operation,
            contents
        ) = row

        entries.append({
            "history_id": record_id,
            "object_type": object_type,
            "object_id": object_id,
            "name": object_name,
            "timestamp": created_at,
            "operation": operation,
            "contents": safe_json_loads(contents),
        })

    return entries


def build_object_history_label(entry):
    timestamp = format_display_timestamp(entry.get("timestamp"))
    timestamp_text = timestamp or "No timestamp"

    return (
        f"{entry.get('object_type')} — "
        f"#{entry.get('object_id')} — "
        f"{entry.get('name')} — "
        f"{timestamp_text} — "
        f"{entry.get('operation')}"
    )


def safe_json_loads(value):
    if isinstance(value, dict):
        return value

    if not value:
        return {}

    try:
        return json.loads(value)
    except Exception:
        logger.exception("Could not parse history JSON.")
        return {"raw": value}


def render_llm_history():
    st.header("LLM call history")

    selected_statuses = st.multiselect(
        "Status",
        LLM_STATUS_OPTIONS,
        default=LLM_STATUS_OPTIONS,
        key="llm_history_statuses"
    )

    entries = [
        entry
        for entry in build_llm_history_entries()
        if entry["status"] in selected_statuses
    ]

    if not entries:
        st.info("No LLM calls found.")
        return

    for entry in entries:
        with st.expander(build_llm_history_label(entry)):
            st.write(f"**ID:** {entry['id']}")
            st.write(f"**Provider:** {entry['provider']}")
            st.write(f"**Model:** {entry['model']}")
            st.write(
                f"**Timestamp:** "
                f"{format_display_timestamp(entry['timestamp'])}"
            )
            st.write(f"**Status:** {entry['status']}")

            if entry["status"] == "Failure":
                st.write(f"**Error type:** {entry.get('error_type') or ''}")
                st.write(f"**Error code(s):** {entry.get('error_codes') or ''}")

            st.write("**Prompt:**")
            st.code(entry.get("prompt") or "")

            st.write("**Response:**")
            st.write(entry.get("response") or "")

            if entry["status"] == "Failure":
                st.write("**Error message:**")
                st.write(entry.get("error_message") or "")

                st.write("**Informational details:**")
                st.code(entry.get("error_details") or "")


def build_llm_history_entries():
    entries = []

    for row in get_llm_calls():
        (
            record_id,
            created_at,
            provider,
            model,
            prompt,
            response
        ) = row

        entries.append({
            "id": record_id,
            "provider": provider,
            "model": model,
            "timestamp": created_at,
            "status": "Success",
            "prompt": prompt,
            "response": response,
        })

    for row in get_failed_llm_calls():
        (
            record_id,
            created_at,
            provider,
            model,
            prompt,
            response,
            error_type,
            error_codes,
            error_message,
            error_details
        ) = row

        entries.append({
            "id": record_id,
            "provider": provider,
            "model": model,
            "timestamp": created_at,
            "status": "Failure",
            "prompt": prompt,
            "response": response,
            "error_type": error_type,
            "error_codes": error_codes,
            "error_message": error_message,
            "error_details": error_details,
        })

    return sorted(
        entries,
        key=lambda entry: (
            entry.get("timestamp") or "",
            entry.get("id") or 0,
        ),
        reverse=True
    )


def build_llm_history_label(entry):
    return (
        f"#{entry.get('id')} — "
        f"{entry.get('provider')} — "
        f"{entry.get('model')} — "
        f"{format_display_timestamp(entry.get('timestamp'))} — "
        f"{entry.get('status')}"
    )
