import streamlit as st

from config import GENDER_OPTIONS
from services.character_service import (
    clone_existing_character,
    create_character,
    delete_existing_character,
    edit_character,
    generate_character_description,
    generate_character_summary,
    list_characters,
    list_profiles_for_character_creation,
    name_exists,
    suggest_name,
)
from ui_helpers import (
    append_profile_data_to_character,
    build_character_header,
    combine_profile_defaults,
)


def render_characters_tab():
    st.header("Characters")

    profiles = list_profiles_for_character_creation()
    all_profile_options = [profile[0] for profile in profiles]

    st.subheader("Create character")

    creation_gender = st.selectbox(
        "Gender",
        GENDER_OPTIONS,
        index=0
    )

    creation_age = st.text_input(
        "Age"
    )

    suggested_name = suggest_name(
        creation_age,
        creation_gender
    )

    previous_suggested_name = st.session_state.get(
        "last_suggested_character_name"
    )

    current_character_name = st.session_state.get(
        "new_character_name",
        ""
    )

    if (
        not current_character_name
        or current_character_name == previous_suggested_name
    ):
        st.session_state["new_character_name"] = suggested_name

    st.session_state[
        "last_suggested_character_name"
    ] = suggested_name

    if st.button("Use suggested name"):
        st.session_state["new_character_name"] = suggested_name
        st.rerun()

    if suggested_name:
        st.caption(
            f"Suggested unused name for age {creation_age or 'unknown'} "
            f"and gender {creation_gender}: {suggested_name}"
        )

    name = st.text_input(
        "Name",
        key="new_character_name"
    )

    gender_profiles = [
        profile for profile in profiles
        if profile[3] == creation_gender
    ]

    profile_options = [
        profile[0] for profile in gender_profiles
    ]

    if st.session_state.get("creation_gender") != creation_gender:
        st.session_state["creation_gender"] = creation_gender
        st.session_state["creation_selected_profiles"] = []

    selected_profiles = st.multiselect(
        "Profiles",
        profile_options,
        key="creation_selected_profiles"
    )

    defaults = combine_profile_defaults(
        selected_profiles,
        gender_profiles
    )

    selected_profile_key = tuple(selected_profiles)

    if (
        st.session_state.get("last_creation_profiles")
        != selected_profile_key
    ):
        st.session_state["creation_physical_traits"] = (
            defaults["physical_traits"]
        )
        st.session_state["creation_personality_traits"] = (
            defaults["personality_traits"]
        )
        st.session_state["creation_notes"] = defaults["notes"]
        st.session_state["last_creation_profiles"] = selected_profile_key

    with st.form("generate_form"):
        physical_traits = st.text_area(
            "Physical traits",
            key="creation_physical_traits"
        )

        personality_traits = st.text_area(
            "Personality traits",
            key="creation_personality_traits"
        )

        notes = st.text_area(
            "Notes",
            key="creation_notes"
        )

        length = st.number_input(
            "Description length in words",
            min_value=50,
            max_value=2000,
            value=300,
            step=50
        )

        summary_length = st.number_input(
            "Summary length in words",
            min_value=25,
            max_value=500,
            value=50,
            step=25
        )

        submitted = st.form_submit_button(
            "Generate New Character"
        )

    if submitted:
        if not name.strip():
            st.error("Character name is required.")
            return

        if name_exists(name):
            st.error(
                f"A character named '{name}' already exists. "
                "Choose another name."
            )
            return

        with st.spinner("Generating character description..."):
            prompt, generated_text = generate_character_description(
                length,
                name,
                creation_age,
                creation_gender,
                physical_traits,
                personality_traits,
                notes
            )

        if generated_text:
            with st.spinner("Generating character summary..."):
                summary = generate_character_summary(
                    generated_text,
                    summary_length
                )

            create_character(
                defaults["profile_name"],
                name,
                creation_age,
                creation_gender,
                physical_traits,
                personality_traits,
                notes,
                prompt,
                generated_text,
                summary or ""
            )

            st.rerun()

    st.divider()

    st.subheader("Current characters by gender")

    character_rows = list_characters()

    if not character_rows:
        st.info("No characters saved yet.")
        return

    for gender_group in GENDER_OPTIONS:
        grouped_characters = [
            row for row in character_rows
            if row[5] == gender_group
        ]

        st.markdown(f"### {gender_group.capitalize()}")

        if not grouped_characters:
            st.info(f"No {gender_group} characters saved yet.")
            continue

        for row in grouped_characters:
            render_character_expander(
                row,
                profiles,
                all_profile_options
            )


def render_character_expander(
    row,
    profiles,
    profile_options
):
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

    header_text = build_character_header(
        name,
        age,
        profile_name
    )

    with st.expander(header_text):
        st.write(f"**Created:** {created_at}")
        st.write(f"**Stored profile(s):** {profile_name or 'No profile'}")

        current_profile_values = (
            [p.strip() for p in profile_name.split(",")]
            if profile_name
            else []
        )

        valid_current_profiles = [
            profile for profile in current_profile_values
            if profile in profile_options
        ]

        selected_profiles_key = f"selected_profiles_{record_id}"
        physical_key = f"physical_traits_{record_id}"
        personality_key = f"personality_traits_{record_id}"
        notes_key = f"notes_{record_id}"
        summary_key = f"summary_{record_id}"
        description_key = f"description_{record_id}"

        initialise_session_value(
            selected_profiles_key,
            valid_current_profiles
        )

        initialise_session_value(
            physical_key,
            physical_traits or ""
        )

        initialise_session_value(
            personality_key,
            personality_traits or ""
        )

        initialise_session_value(
            notes_key,
            notes or ""
        )

        initialise_session_value(
            summary_key,
            summary or ""
        )

        initialise_session_value(
            description_key,
            response or ""
        )

        st.multiselect(
            "Profile(s) assigned to this character",
            profile_options,
            key=selected_profiles_key
        )

        st.caption(
            "Select profiles here, then click 'Save character changes' "
            "below to store the profile assignment."
        )

        if st.button(
            "Apply selected profiles to character",
            key=f"apply_profiles_{record_id}"
        ):
            (
                profile_value,
                combined_physical_traits,
                combined_personality_traits,
                combined_notes
            ) = append_profile_data_to_character(
                st.session_state[selected_profiles_key],
                profiles,
                st.session_state[physical_key],
                st.session_state[personality_key],
                st.session_state[notes_key]
            )

            st.session_state[physical_key] = combined_physical_traits
            st.session_state[personality_key] = combined_personality_traits
            st.session_state[notes_key] = combined_notes

            st.success(
                "Profile traits and notes appended."
            )

            st.rerun()

        render_summary_generation_section(
            record_id,
            description_key,
            summary_key
        )

        with st.form(f"edit_character_{record_id}"):
            edited_name = st.text_input(
                "Name",
                value=name or ""
            )

            edited_age = st.text_input(
                "Age",
                value=age or ""
            )

            edited_gender = st.selectbox(
                "Gender",
                GENDER_OPTIONS,
                index=GENDER_OPTIONS.index(gender)
                if gender in GENDER_OPTIONS
                else 0
            )

            edited_physical_traits = st.text_area(
                "Physical traits",
                key=physical_key
            )

            edited_personality_traits = st.text_area(
                "Personality traits",
                key=personality_key
            )

            edited_notes = st.text_area(
                "Notes",
                key=notes_key
            )

            edited_response = st.text_area(
                "Description",
                key=description_key,
                height=300
            )

            edited_summary = st.text_area(
                "Summary",
                key=summary_key,
                height=150
            )

            save_character_changes = (
                st.form_submit_button(
                    "Save character changes"
                )
            )

        if save_character_changes:
            profile_value = profile_value_from_state(
                selected_profiles_key
            )

            name_changed = (
                edited_name.strip().lower()
                != (name or "").strip().lower()
            )

            if name_changed and name_exists(edited_name):
                st.error(
                    f"A character named '{edited_name}' already exists. "
                    "Choose another name."
                )
                return

            edit_character(
                record_id,
                profile_value,
                edited_name,
                edited_age,
                edited_gender,
                edited_physical_traits,
                edited_personality_traits,
                edited_notes,
                edited_response,
                edited_summary
            )

            st.success("Character updated.")
            st.rerun()

        st.divider()

        render_regeneration_section(
            record_id,
            profile_value_from_state(
                selected_profiles_key
            ),
            name,
            age,
            gender,
            st.session_state[physical_key],
            st.session_state[personality_key],
            st.session_state[notes_key],
            description_key,
            summary_key
        )

        st.divider()

        col_clone, col_delete = st.columns(2)

        with col_clone:
            if st.button(
                "Clone character",
                key=f"clone_character_{record_id}"
            ):
                new_id = clone_existing_character(
                    record_id
                )

                st.success(
                    f"Character cloned as ID {new_id}."
                )

                st.rerun()

        with col_delete:
            if st.button(
                "Delete character",
                key=f"delete_character_{record_id}"
            ):
                delete_existing_character(record_id)

                st.success("Character deleted.")
                st.rerun()


def initialise_session_value(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def render_summary_generation_section(
    record_id,
    description_key,
    summary_key
):
    st.subheader(
        "Generate summary from description"
    )

    summary_length = st.number_input(
        "Summary length in words",
        min_value=25,
        max_value=500,
        value=50,
        step=25,
        key=f"summary_length_{record_id}"
    )

    if st.button(
        "Generate summary from description",
        key=f"generate_summary_{record_id}"
    ):
        description = st.session_state.get(
            description_key,
            ""
        )

        if not description.strip():
            st.error(
                "Description is empty. "
                "Add a description first."
            )

            return

        with st.spinner("Generating summary..."):
            generated_summary = (
                generate_character_summary(
                    description,
                    summary_length
                )
            )

        if generated_summary:
            st.session_state[
                summary_key
            ] = generated_summary

            st.success(
                "Summary generated. Review it below, "
                "then click "
                "'Save character changes' to store it."
            )

            st.rerun()


def profile_value_from_state(
    selected_profiles_key
):
    selected_profiles = st.session_state.get(
        selected_profiles_key,
        []
    )

    if not selected_profiles:
        return None

    return ", ".join(selected_profiles)


def render_regeneration_section(
    record_id,
    profile_name,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes,
    description_key,
    summary_key
):
    st.subheader("Regenerate description")

    regen_length = st.number_input(
        "Regenerated description length in words",
        min_value=50,
        max_value=2000,
        value=300,
        step=50,
        key=f"regen_length_{record_id}"
    )

    regen_summary_length = st.number_input(
        "Regenerated summary length in words",
        min_value=25,
        max_value=500,
        value=50,
        step=25,
        key=f"regen_summary_length_{record_id}"
    )

    if st.button(
        "Regenerate description",
        key=f"regenerate_character_{record_id}"
    ):
        with st.spinner(
            "Regenerating description..."
        ):
            regenerate_prompt, regenerated_text = (
                generate_character_description(
                    regen_length,
                    name,
                    age,
                    gender,
                    physical_traits,
                    personality_traits,
                    notes
                )
            )

        if regenerated_text:
            with st.spinner(
                "Regenerating summary..."
            ):
                regenerated_summary = (
                    generate_character_summary(
                        regenerated_text,
                        regen_summary_length
                    )
                )

            st.session_state[
                f"regenerated_character_{record_id}"
            ] = regenerated_text

            st.session_state[
                f"regenerated_summary_{record_id}"
            ] = regenerated_summary or ""

    regenerated_key = (
        f"regenerated_character_{record_id}"
    )

    regenerated_summary_key = (
        f"regenerated_summary_{record_id}"
    )

    if regenerated_key not in st.session_state:
        return

    regenerated_text = st.text_area(
        "New description preview",
        value=st.session_state[regenerated_key],
        height=300,
        key=f"regenerated_text_area_{record_id}"
    )

    regenerated_summary = st.text_area(
        "New summary preview",
        value=st.session_state.get(
            regenerated_summary_key,
            ""
        ),
        height=150,
        key=f"regenerated_summary_text_area_{record_id}"
    )

    st.info(
        "You can manually copy or merge text "
        "from this preview into the main "
        "description or summary fields above, "
        "or replace both fields completely."
    )

    if st.button(
        "Replace old summary and description "
        "with regenerated version",
        key=f"replace_description_{record_id}"
    ):
        st.session_state[
            description_key
        ] = regenerated_text

        st.session_state[
            summary_key
        ] = regenerated_summary

        del st.session_state[regenerated_key]

        if regenerated_summary_key in st.session_state:
            del st.session_state[
                regenerated_summary_key
            ]

        st.success(
            "Summary and description replaced "
            "in the editor. Click "
            "'Save character changes' to "
            "store them."
        )

        st.rerun()
