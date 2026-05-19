import streamlit as st

from services.observability_service import list_recent_events
from ui_helpers import format_display_timestamp


EVENT_STATUS_OPTIONS = [
    "started",
    "completed",
    "failed",
]


def render_observability_tab():
    st.header("Debug / Observability")

    limit = st.number_input(
        "Recent events",
        min_value=10,
        max_value=500,
        value=100,
        step=10,
    )

    selected_statuses = st.multiselect(
        "Status",
        EVENT_STATUS_OPTIONS,
        default=EVENT_STATUS_OPTIONS,
    )

    events = [
        event
        for event in list_recent_events(limit=limit)
        if (event.get("status") or "") in selected_statuses
    ]

    if not events:
        st.info("No observability events found.")
        return

    st.dataframe(
        [
            {
                "timestamp": format_display_timestamp(event["timestamp"]),
                "event_type": event["event_type"],
                "status": event["status"],
                "duration_ms": event["duration_ms"],
                "story_id": event["story_id"],
                "chapter_id": event["chapter_id"],
                "template_id": event["template_id"],
                "provider": event["provider"],
                "model": event["model"],
                "token_estimate": event["token_estimate"],
                "error_type": event["error_type"],
            }
            for event in events
        ],
        hide_index=True,
        use_container_width=True,
    )

    for event in events:
        with st.expander(build_event_label(event)):
            st.json(event)


def build_event_label(event):
    parts = [
        f"#{event.get('id')}",
        event.get("event_type") or "",
        event.get("status") or "",
        format_display_timestamp(event.get("timestamp")) or "",
    ]

    if event.get("duration_ms") is not None:
        parts.append(f"{event['duration_ms']} ms")

    return " - ".join(str(part) for part in parts if part)
