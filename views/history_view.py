import streamlit as st

from services.character_service import list_characters


def render_history_tab():
    st.header("Character history")

    rows = list_characters()

    if not rows:
        st.info("No characters saved yet.")
        return

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