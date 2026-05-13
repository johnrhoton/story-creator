# views/templates_view.py

import streamlit as st

from services.template_service import (
    clone_template,
    create_template,
    create_template_chapter,
    delete_template,
    delete_template_chapter,
    edit_template,
    edit_template_chapter,
    list_template_chapters,
    list_templates,
)


def render_templates_tab():
    st.header("Templates")

    st.subheader("Create template")

    with st.form("create_template_form"):
        template_name = st.text_input("Template name")

        overview = st.text_area(
            "Overview",
            height=150
        )

        setting_background = st.text_area(
            "Setting / Background",
            height=150
        )

        tone_style = st.text_input("Tone / Style")

        save_template = st.form_submit_button(
            "Create template"
        )

    if save_template:
        if not template_name.strip():
            st.error("Template name is required.")
        else:
            create_template(
                template_name.strip(),
                overview,
                setting_background,
                tone_style
            )

            st.success(f"Template '{template_name}' created.")
            st.rerun()

    st.divider()

    st.subheader("Templates")

    templates = list_templates()

    if not templates:
        st.info("No templates created yet.")
        return

    for template in templates:
        render_template_expander(template)


def render_template_expander(template):
    (
        template_id,
        created_at,
        template_name,
        overview,
        setting_background,
        tone_style
    ) = template

    with st.expander(template_name):
        st.write(f"**Created:** {created_at}")

        with st.form(f"edit_template_{template_id}"):
            edited_template_name = st.text_input(
                "Template name",
                value=template_name
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

            save_changes = st.form_submit_button(
                "Save template changes"
            )

        if save_changes:
            edit_template(
                template_id,
                edited_template_name,
                edited_overview,
                edited_setting_background,
                edited_tone_style
            )

            st.success("Template updated.")
            st.rerun()

        st.divider()

        render_template_chapters_section(template_id)

        st.divider()

        col_clone, col_delete = st.columns(2)

        with col_clone:
            if st.button(
                "Clone template",
                key=f"clone_template_{template_id}"
            ):
                new_template_id = clone_template(template_id)

                st.success(
                    f"Template cloned as ID {new_template_id}."
                )

                st.rerun()

        with col_delete:
            if st.button(
                "Delete template",
                key=f"delete_template_{template_id}"
            ):
                delete_template(template_id)

                st.success("Template deleted.")
                st.rerun()


def render_template_chapters_section(template_id):
    st.subheader("Chapters")

    chapters = list_template_chapters(template_id)

    if not chapters:
        st.info("No chapters yet.")
    else:
        for chapter in chapters:
            render_template_chapter_expander(chapter)

    st.markdown("### Add next chapter")

    with st.form(f"create_chapter_{template_id}"):
        new_chapter_number = st.number_input(
            "Chapter number",
            min_value=1,
            value=len(chapters) + 1,
            step=1
        )

        new_chapter_description = st.text_area(
            "Chapter description",
            height=150
        )

        add_chapter = st.form_submit_button(
            "Add chapter"
        )

    if add_chapter:
        create_template_chapter(
            template_id,
            int(new_chapter_number),
            new_chapter_description
        )

        st.success("Chapter added.")
        st.rerun()


def render_template_chapter_expander(chapter):
    (
        chapter_id,
        template_id,
        chapter_number,
        chapter_description
    ) = chapter

    title = (
        f"Chapter {chapter_number} — "
        f"{truncate_text(chapter_description, 60)}"
    )

    with st.expander(title):
        with st.form(f"edit_chapter_{chapter_id}"):
            edited_chapter_number = st.number_input(
                "Chapter number",
                min_value=1,
                value=chapter_number,
                step=1
            )

            edited_chapter_description = st.text_area(
                "Chapter description",
                value=chapter_description or "",
                height=150
            )

            save_chapter_changes = st.form_submit_button(
                "Save chapter changes"
            )

        if save_chapter_changes:
            edit_template_chapter(
                chapter_id,
                int(edited_chapter_number),
                edited_chapter_description
            )

            st.success("Chapter updated.")
            st.rerun()

        if st.button(
            "Delete chapter",
            key=f"delete_chapter_{chapter_id}"
        ):
            delete_template_chapter(chapter_id)

            st.success("Chapter deleted.")
            st.rerun()


def truncate_text(text, max_length):
    if not text:
        return "Untitled"

    if len(text) <= max_length:
        return text

    return text[:max_length] + "..."
