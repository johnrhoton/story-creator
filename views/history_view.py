import streamlit as st

from database import get_failed_llm_calls, get_llm_calls
from services.character_service import list_characters


def render_history_tab():
    st.header("Character history")

    rows = list_characters()

    if not rows:
        st.info("No characters saved yet.")
    else:
        for row in rows:
            (
                record_id,
                created_at,
                profile_name,
                name,
                age,
                gender,
                physical_traits,
                personality_traits,
                notes,
                response,
                summary
            ) = row

            profile_display = profile_name or "No profile"

            with st.expander(
                f"#{record_id} — {name or 'Unnamed character'} — "
                f"{age} — {profile_display} — {created_at}"
            ):
                st.write(f"**Created:** {created_at}")
                st.write(f"**Profile:** {profile_display}")
                st.write(f"**Age:** {age}")
                st.write(f"**Gender:** {gender}")
                st.write(f"**Physical traits:** {physical_traits}")
                st.write(f"**Personality traits:** {personality_traits}")
                st.write(f"**Notes:** {notes}")

                st.write("**Summary:**")
                st.write(summary or "")

                st.write("**Description:**")
                st.write(response)

    st.divider()

    render_llm_call_history()

    st.divider()

    render_failed_llm_call_history()


def render_llm_call_history():
    st.header("LLM call history")

    rows = get_llm_calls()

    if not rows:
        st.info("No LLM calls logged yet.")
        return

    for row in rows:
        (
            record_id,
            created_at,
            provider,
            model,
            prompt,
            response
        ) = row

        with st.expander(
            f"#{record_id} — {provider} — {model} — {created_at}"
        ):
            st.write(f"**Created:** {created_at}")
            st.write(f"**Provider:** {provider}")
            st.write(f"**Model:** {model}")

            st.write("**Prompt:**")
            st.code(prompt or "")

            st.write("**Response:**")
            st.write(response or "")


def render_failed_llm_call_history():
    st.header("Failed LLM calls")

    rows = get_failed_llm_calls()

    if not rows:
        st.info("No failed LLM calls logged yet.")
        return

    for row in rows:
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

        with st.expander(
            f"#{record_id} — {provider} — {model} — {created_at}"
        ):
            st.write(f"**Created:** {created_at}")
            st.write(f"**Provider:** {provider}")
            st.write(f"**Model:** {model}")
            st.write(f"**Error type:** {error_type or ''}")
            st.write(f"**Error code(s):** {error_codes or ''}")

            st.write("**Prompt:**")
            st.code(prompt or "")

            st.write("**Response:**")
            st.write(response or "")

            st.write("**Error message:**")
            st.write(error_message or "")

            st.write("**Informational details:**")
            st.code(error_details or "")
