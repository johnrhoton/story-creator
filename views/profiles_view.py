import streamlit as st

from config import GENDER_OPTIONS
from services.profile_service import (
    clone_existing_profile,
    create_profile,
    delete_existing_profiles,
    delete_existing_profile,
    edit_profile,
    list_profiles_for_export,
    list_profiles,
    rename_existing_profile,
)
from views.bulk_actions import render_bulk_actions


def render_profiles_tab():
    st.header("Profiles")

    with st.form("profile_form"):
        profile_name = st.text_input("Profile name").lower()

        profile_gender = st.selectbox(
            "Default gender",
            GENDER_OPTIONS
        )

        profile_physical_traits = st.text_area(
            "Default physical traits"
        )

        profile_personality_traits = st.text_area(
            "Default personality traits"
        )

        profile_notes = st.text_area(
            "Default notes"
        )

        save_profile = st.form_submit_button(
            "Save profile"
        )

    if save_profile:
        if not profile_name:
            st.error("Profile name is required.")
        else:
            create_profile(
                profile_name,
                profile_gender,
                profile_physical_traits,
                profile_personality_traits,
                profile_notes
            )

            st.success(f"Profile '{profile_name}' saved.")
            st.rerun()

    st.subheader("Saved profiles by gender")

    profiles = list_profiles()

    if profiles:
        render_profile_bulk_actions(profiles)

    for gender_group in GENDER_OPTIONS:
        grouped_profiles = [
            profile for profile in profiles
            if profile[1] == gender_group
        ]

        st.markdown(f"### {gender_group.capitalize()}")

        if not grouped_profiles:
            st.info(f"No {gender_group} profiles saved yet.")
            continue

        for profile in grouped_profiles:
            (
                profile_name,
                gender,
                physical_traits,
                personality_traits,
                notes
            ) = profile

            with st.expander(profile_name):
                with st.form(f"edit_profile_{profile_name}"):

                    edited_profile_name = st.text_input(
                        "Profile name",
                        value=profile_name
                    ).lower()

                    edited_gender = st.selectbox(
                        "Gender",
                        GENDER_OPTIONS,
                        index=GENDER_OPTIONS.index(gender)
                        if gender in GENDER_OPTIONS
                        else 0
                    )

                    edited_physical_traits = st.text_area(
                        "Physical traits",
                        value=physical_traits or ""
                    )

                    edited_personality_traits = st.text_area(
                        "Personality traits",
                        value=personality_traits or ""
                    )

                    edited_notes = st.text_area(
                        "Notes",
                        value=notes or ""
                    )

                    save_profile_changes = st.form_submit_button(
                        "Save profile changes"
                    )

                if save_profile_changes:
                    if not edited_profile_name:
                        st.error("Profile name cannot be empty.")
                    else:
                        if edited_profile_name != profile_name:
                            rename_existing_profile(
                                profile_name,
                                edited_profile_name
                            )

                        edit_profile(
                            edited_profile_name,
                            edited_gender,
                            edited_physical_traits,
                            edited_personality_traits,
                            edited_notes
                        )

                        st.success(f"Profile '{edited_profile_name}' updated.")
                        st.rerun()

                col_clone, col_delete = st.columns(2)

                with col_clone:
                    if st.button(
                        "Clone profile",
                        key=f"clone_profile_{profile_name}"
                    ):
                        new_profile_name = clone_existing_profile(profile_name)
                        st.success(f"Profile cloned as '{new_profile_name}'.")
                        st.rerun()

                with col_delete:
                    if st.button(
                        "Delete profile",
                        key=f"delete_profile_{profile_name}"
                    ):
                        delete_existing_profile(profile_name)
                        st.success(f"Profile '{profile_name}' deleted.")
                        st.rerun()


def render_profile_bulk_actions(profiles):
    render_bulk_actions(
        profiles,
        "Select profiles",
        "selected_profile_bulk_actions",
        lambda row: row[0],
        lambda row: row[0],
        build_selected_profiles_export_payload,
        "exported_profiles",
        delete_existing_profiles,
        "Delete selected profiles",
        "delete_selected_profiles",
        "Export selected profiles",
        "export_selected_profiles",
        "profile"
    )


def build_selected_profiles_export_payload(selected_profiles):
    profiles = list_profiles_for_export(
        selected_profiles,
        decrypt_values=not st.session_state.get(
            "encrypt_export_downloads",
            False
        )
    )

    return {
        "profiles": profiles
    }
