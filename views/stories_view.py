# views/stories_view.py

import json

import streamlit as st

from services.story_service import (
    build_full_story_markdown,
    clone_existing_story,
    create_and_generate_story_chapter,
    create_from_template,
    create_story_chapter,
    delete_existing_stories,
    delete_existing_story,
    delete_existing_story_chapter,
    edit_story,
    edit_story_chapter,
    generate_story_chapter_body_and_summary,
    list_female_characters,
    list_male_characters,
    list_stories_for_export,
    list_stories,
    list_story_chapters,
    list_templates,
)
from services.template_service import parse_character_roles
from views.bulk_actions import render_bulk_actions
from ui_helpers import format_display_timestamp


def render_stories_tab():
    st.header("Stories")

    templates = list_templates()

    template_options = {
        template[0]: template[2]
        for template in templates
    }

    template_rows_by_id = {
        template[0]: template
        for template in templates
    }

    stories = list_stories()
    existing_story_names = {
        story[2].strip().lower()
        for story in stories
        if story[2]
    }

    male_character_rows = list_male_characters()
    female_character_rows = list_female_characters()

    male_character_options = [
        row[1]
        for row in male_character_rows
    ]
    male_character_labels = build_character_option_labels(
        male_character_rows
    )
    male_character_by_name = {
        row[1]: row
        for row in male_character_rows
    }

    female_character_options = [
        row[1]
        for row in female_character_rows
    ]
    female_character_labels = build_character_option_labels(
        female_character_rows
    )

    st.subheader("Create story from template")

    selected_template_id = st.selectbox(
        "Template",
        list(template_options.keys()) if template_options else [],
        format_func=lambda template_id: template_options.get(template_id, ""),
        key="selected_template_id"
    )

    selected_template = (
        template_rows_by_id.get(selected_template_id)
        if selected_template_id else None
    )

    male_roles = []
    female_roles = []

    if selected_template:
        male_roles = parse_character_roles(selected_template[6])
        female_roles = parse_character_roles(selected_template[7])

    with st.form("create_story_form"):
        story_name = st.text_input("Story name")

        selected_male_characters = []
        if male_roles:
            st.markdown("**Male character slots**")
            for idx, role in enumerate(male_roles, start=1):
                selected_male_characters.append(
                    st.selectbox(
                        f"M{idx} — {role}",
                        [""] + male_character_options,
                        format_func=lambda name: male_character_labels.get(name, name),
                        key=f"male_slot_{idx}"
                    )
                )
        else:
            selected_male_characters = st.multiselect(
                "Male characters",
                male_character_options,
                format_func=lambda name: male_character_labels.get(name, name)
            )

        selected_female_characters = []
        if female_roles:
            st.markdown("**Female character slots**")
            for idx, role in enumerate(female_roles, start=1):
                selected_female_characters.append(
                    st.selectbox(
                        f"F{idx} — {role}",
                        [""] + female_character_options,
                        format_func=lambda name: female_character_labels.get(name, name),
                        key=f"female_slot_{idx}"
                    )
                )
        else:
            selected_female_characters = st.multiselect(
                "Female characters",
                female_character_options,
                format_func=lambda name: female_character_labels.get(name, name)
            )

        create_story = st.form_submit_button(
            "Create story and generate chapters"
        )

    if create_story:
        story_name = story_name.strip()

        if not story_name:
            st.error("Story name is required.")
        elif not selected_template_id:
            st.error("A template is required.")
        elif story_name.lower() in existing_story_names:
            st.error(
                f"A story named '{story_name}' already exists. "
                "Choose another name."
            )
        else:
            template_id = selected_template_id
            template = template_rows_by_id[selected_template_id]
            male_roles = parse_character_roles(template[6])
            female_roles = parse_character_roles(template[7])
            missing_male = [
                idx + 1 for idx, value in enumerate(selected_male_characters)
                if male_roles and not value
            ]
            missing_female = [
                idx + 1 for idx, value in enumerate(selected_female_characters)
                if female_roles and not value
            ]

            if missing_male:
                st.error(
                    f"Please fill all male character slots: "
                    f"{', '.join('M' + str(i) for i in missing_male)}."
                )
            elif missing_female:
                st.error(
                    f"Please fill all female character slots: "
                    f"{', '.join('F' + str(i) for i in missing_female)}."
                )
            else:
                try:
                    status_placeholder = st.empty()

                    def progress_callback(chapter_number):
                        status_placeholder.info(
                            f"Generating Chapter {chapter_number}..."
                        )

                    with st.spinner("Creating story and generating chapters..."):
                        story_id = create_from_template(
                            template_id,
                            story_name,
                            selected_male_characters,
                            selected_female_characters,
                            progress_callback=progress_callback
                        )

                    st.success(f"Story created with ID {story_id}.")
                    st.rerun()

                except Exception as error:
                    st.error(f"Story creation failed: {error}")

    st.divider()

    st.subheader("Stories")

    if not stories:
        st.info("No stories created yet.")
        return

    render_story_bulk_actions(stories)

    for story in stories:
        render_story_expander(story)


def render_story_bulk_actions(stories):
    render_bulk_actions(
        stories,
        "Select stories",
        "selected_story_bulk_actions",
        build_story_option_label,
        lambda row: row[0],
        list_stories_for_bulk_export,
        "exported_stories",
        delete_existing_stories,
        "Delete selected stories",
        "delete_selected_stories",
        "Export selected stories",
        "export_selected_stories",
        "story"
    )


def list_stories_for_bulk_export(story_ids):
    return list_stories_for_export(
        story_ids,
        decrypt_values=not st.session_state.get(
            "encrypt_export_downloads",
            False
        )
    )


def build_story_option_label(story):
    story_id = story[0]
    story_name = story[2] or "Untitled story"

    return f"#{story_id} - {story_name}"


def render_story_expander(story):
    (
        story_id,
        created_at,
        story_name,
        template_id,
        overview,
        setting_background,
        tone_style,
        male_characters,
        female_characters
    ) = story

    male_character_values = safe_json_loads(male_characters)
    female_character_values = safe_json_loads(female_characters)

    with st.expander(story_name):
        st.write(
            f"**Created:** {format_display_timestamp(created_at)}"
        )
        st.write(f"**Template ID:** {template_id or 'None'}")

        with st.form(f"edit_story_{story_id}"):
            edited_story_name = st.text_input(
                "Story name",
                value=story_name
            )

            edited_overview = st.text_area(
                "Overview",
                value=overview or "",
                height=150
            )

            edited_setting_background = st.text_area(
                "Setting / Background",
                value=setting_background or "",
                height=150
            )

            edited_tone_style = st.text_input(
                "Tone / Style",
                value=tone_style or ""
            )

            edited_male_characters_text = st.text_area(
                "Male characters",
                value=", ".join(male_character_values),
                height=80
            )

            edited_female_characters_text = st.text_area(
                "Female characters",
                value=", ".join(female_character_values),
                height=80
            )

            save_story_changes = st.form_submit_button(
                "Save story changes"
            )

        if save_story_changes:
            edit_story(
                story_id,
                edited_story_name,
                edited_overview,
                edited_setting_background,
                edited_tone_style,
                split_csv(edited_male_characters_text),
                split_csv(edited_female_characters_text)
            )

            st.success("Story updated.")
            st.rerun()

        st.divider()

        render_story_chapters_section(story_id)

        st.divider()

        col_clone, col_delete = st.columns(2)

        with col_clone:
            if st.button(
                "Clone story",
                key=f"clone_story_{story_id}"
            ):
                new_story_id = clone_existing_story(story_id)
                st.success(f"Story cloned as ID {new_story_id}.")
                st.rerun()

        with col_delete:
            if st.button(
                "Delete story",
                key=f"delete_story_{story_id}"
            ):
                delete_existing_story(story_id)
                st.success("Story deleted.")
                st.rerun()


def render_story_chapters_section(story_id):
    st.subheader("Chapters")

    chapters = list_story_chapters(story_id)
    story_markdown = build_full_story_markdown(chapters)

    if not chapters:
        st.info("No chapters yet.")
    else:
        with st.expander("Full story markdown"):
            if story_markdown:
                st.markdown(story_markdown)
                st.download_button(
                    "Download full story markdown",
                    data=story_markdown,
                    file_name=f"story_{story_id}.md",
                    mime="text/markdown",
                    key=f"download_story_markdown_{story_id}"
                )
            else:
                st.info("No chapter body text yet.")

        for chapter in chapters:
            render_story_chapter_expander(chapter)

    st.markdown("### Add next chapter")

    with st.form(f"create_story_chapter_{story_id}"):
        new_chapter_number = st.number_input(
            "Chapter number",
            min_value=1,
            value=len(chapters) + 1,
            step=1
        )

        new_chapter_description = st.text_area(
            "Chapter description",
            height=120
        )

        new_chapter_body = st.text_area(
            "Chapter body",
            height=250
        )

        new_chapter_summary = st.text_area(
            "Chapter summary",
            height=120
        )

        col_add, col_generate = st.columns(2)

        with col_add:
            add_chapter = st.form_submit_button("Add chapter")

        with col_generate:
            add_and_generate_chapter = st.form_submit_button(
                "Add and generate"
            )

    if add_chapter:
        create_story_chapter(
            story_id,
            int(new_chapter_number),
            new_chapter_description,
            new_chapter_body,
            new_chapter_summary
        )

        st.success("Chapter added.")
        st.rerun()

    if add_and_generate_chapter:
        try:
            status_placeholder = st.empty()

            def progress_callback(chapter_number):
                status_placeholder.info(
                    f"Generating Chapter {chapter_number}..."
                )

            with st.spinner("Adding and generating chapter..."):
                _chapter_id, result = create_and_generate_story_chapter(
                    story_id,
                    int(new_chapter_number),
                    new_chapter_description,
                    new_chapter_body,
                    new_chapter_summary,
                    progress_callback=progress_callback
                )

            if result:
                st.success("Chapter added and generated.")
            else:
                st.warning(
                    "Chapter was added, but generation did not return text."
                )
            st.rerun()

        except Exception as error:
            st.error(f"Chapter generation failed: {error}")


def render_story_chapter_expander(chapter):
    (
        chapter_id,
        story_id,
        chapter_number,
        chapter_description,
        chapter_body,
        chapter_summary
    ) = chapter

    title = (
        f"Chapter {chapter_number} — "
        f"{truncate_text(chapter_description, 60)}"
    )

    with st.expander(title):
        with st.form(f"edit_story_chapter_{chapter_id}"):
            edited_chapter_number = st.number_input(
                "Chapter number",
                min_value=0,
                value=chapter_number,
                step=1
            )

            edited_chapter_description = st.text_area(
                "Chapter description",
                value=chapter_description or "",
                height=120
            )

            edited_chapter_body = st.text_area(
                "Chapter body",
                value=chapter_body or "",
                height=300
            )

            edited_chapter_summary = st.text_area(
                "Chapter summary",
                value=chapter_summary or "",
                height=120
            )

            save_chapter_changes = st.form_submit_button(
                "Save chapter changes"
            )

        if save_chapter_changes:
            edit_story_chapter(
                chapter_id,
                int(edited_chapter_number),
                edited_chapter_description,
                edited_chapter_body,
                edited_chapter_summary
            )

            st.success("Chapter updated.")
            st.rerun()

        if st.button(
            "Generate body and summary",
            key=f"generate_story_chapter_{chapter_id}"
        ):
            try:
                status_placeholder = st.empty()

                def progress_callback(chapter_number):
                    status_placeholder.info(
                        f"Generating Chapter {chapter_number}..."
                    )

                with st.spinner(
                    "Generating chapter body and summary..."
                ):
                    result = generate_story_chapter_body_and_summary(
                        story_id,
                        chapter_id,
                        progress_callback=progress_callback
                    )

                if result:
                    st.success("Chapter body and summary generated.")
                    st.rerun()
                else:
                    st.warning(
                        "Chapter generation did not return any text."
                    )
            except Exception as error:
                st.error(f"Chapter generation failed: {error}")

        if st.button(
            "Delete chapter",
            key=f"delete_story_chapter_{chapter_id}"
        ):
            delete_existing_story_chapter(chapter_id)
            st.success("Chapter deleted.")
            st.rerun()


def safe_json_loads(value):
    if not value:
        return []

    try:
        return json.loads(value)
    except Exception:
        return []


def build_character_option_labels(character_rows):
    labels = {}

    for row in character_rows:
        name = row[1]
        age = row[2] or "Unknown age"
        profile_name = row[5] or "No profile"

        labels[name] = f"{name} — {age} — {profile_name}"

    return labels


def split_csv(value):
    if not value:
        return []

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def truncate_text(text, max_length):
    if not text:
        return "Untitled"

    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."
