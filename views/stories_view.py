# views/stories_view.py

import json

import streamlit as st

from services.story_service import (
    clone_existing_story,
    create_from_template,
    create_story_chapter,
    delete_existing_story,
    delete_existing_story_chapter,
    edit_story,
    edit_story_chapter,
    list_stories,
    list_story_chapters,
    list_templates,
)


def render_stories_tab():
    st.header("Stories")

    templates = list_templates()

    template_options = {
        template[2]: template[0]
        for template in templates
    }

    st.subheader("Create story from template")

    with st.form("create_story_form"):
        story_name = st.text_input("Story name")

        selected_template_name = st.selectbox(
            "Template",
            list(template_options.keys()) if template_options else []
        )

        create_story = st.form_submit_button("Create story")

    if create_story:
        if not story_name.strip():
            st.error("Story name is required.")
        elif not selected_template_name:
            st.error("A template is required.")
        else:
            template_id = template_options[selected_template_name]

            story_id = create_from_template(
                template_id,
                story_name.strip()
            )

            st.success(f"Story created with ID {story_id}.")
            st.rerun()

    st.divider()

    st.subheader("Stories")

    stories = list_stories()

    if not stories:
        st.info("No stories created yet.")
        return

    for story in stories:
        render_story_expander(story)


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
        st.write(f"**Created:** {created_at}")
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

    if not chapters:
        st.info("No chapters yet.")
    else:
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

        add_chapter = st.form_submit_button("Add chapter")

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
                min_value=1,
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