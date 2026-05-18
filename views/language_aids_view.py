import streamlit as st

from services.glossary_service import (
    build_glossary_table,
    generate_glossary,
    glossary_entries_to_csv,
    normalize_dictionary_languages,
)
from services.reading_comprehension_service import (
    build_reading_comprehension_table,
    generate_reading_comprehension_questions,
    reading_comprehension_to_csv,
)
from services.story_service import (
    build_full_story_markdown,
    list_stories,
    list_story_chapters,
)


LANGUAGE_AID_OPTIONS = [
    "Glossary",
    "Reading comprehension",
]


def render_language_aids_tab():
    st.header("Language Aids")

    initial_story_id = parse_optional_int(get_query_param("story_id"))
    initial_chapter_number = parse_optional_int(
        get_query_param("chapter_number")
    )
    initial_aid = get_query_param("aid")
    if initial_aid not in LANGUAGE_AID_OPTIONS:
        initial_aid = "Glossary"

    stories = list_stories()
    story_options = [story[0] for story in stories]
    story_names = {
        story[0]: story[2] or f"Story {story[0]}"
        for story in stories
    }
    story_languages = {
        story[0]: story[8] or ""
        for story in stories
    }

    selected_story_id = st.selectbox(
        "Story",
        story_options,
        index=find_option_index(story_options, initial_story_id),
        format_func=lambda story_id: (
            f"{story_id}: {story_names.get(story_id, '')}"
        ),
        key="language_aids_story_id"
    ) if story_options else None

    if not selected_story_id:
        st.info("No stories are available.")
        return

    chapters = list_story_chapters(selected_story_id)
    chapter_options = ["Full story"] + [
        chapter[2]
        for chapter in chapters
    ]
    initial_scope = (
        initial_chapter_number
        if initial_chapter_number is not None
        else "Full story"
    )

    selected_scope = st.selectbox(
        "Text",
        chapter_options,
        index=find_option_index(chapter_options, initial_scope),
        format_func=lambda value: (
            value
            if value == "Full story"
            else f"Chapter {value}"
        ),
        key="language_aids_scope"
    )

    source_text, text_type, file_name_prefix = resolve_language_aid_source(
        selected_story_id,
        selected_scope,
        chapters
    )

    selected_aid = st.radio(
        "Aid type",
        LANGUAGE_AID_OPTIONS,
        horizontal=True,
        index=find_option_index(LANGUAGE_AID_OPTIONS, initial_aid),
        key="language_aid_type"
    )

    source_language = story_languages.get(selected_story_id, "")

    if selected_aid == "Glossary":
        render_glossary_generator(
            source_text=source_text,
            text_type=text_type,
            file_name=f"{file_name_prefix}_glossary.csv",
            key_prefix="language_aids_glossary",
            source_language=source_language
        )
    else:
        render_reading_comprehension_generator(
            source_text=source_text,
            text_type=text_type,
            file_name=f"{file_name_prefix}_questions.csv",
            key_prefix="language_aids_questions",
            source_language=source_language
        )


def render_glossary_generator(
    source_text,
    text_type,
    file_name,
    key_prefix,
    source_language=""
):
    col_count, col_languages = st.columns([1, 3])

    with col_count:
        entry_count = st.number_input(
            "Entries",
            min_value=1,
            max_value=100,
            value=15,
            step=1,
            key=f"{key_prefix}_entry_count"
        )

    with col_languages:
        dictionary_languages = st.text_input(
            "Dictionary languages",
            placeholder="German, Spanish",
            key=f"{key_prefix}_languages"
        )

    if not source_text or not str(source_text).strip():
        st.info("No text is available for this selection.")
        return

    with st.expander("Source preview"):
        st.text(source_text[:4000])

    if st.button("Create glossary", key=f"{key_prefix}_create"):
        languages = normalize_dictionary_languages(dictionary_languages)

        if not languages:
            st.error("Enter at least one dictionary language.")
            return

        with st.spinner("Creating glossary..."):
            entries = generate_glossary(
                source_text,
                languages,
                entry_count=int(entry_count),
                text_type=text_type,
                source_language=source_language,
            )

        if not entries:
            st.warning("Glossary generation did not return entries.")
            return

        csv_data = glossary_entries_to_csv(entries, languages)
        st.dataframe(
            build_glossary_table(entries, languages),
            use_container_width=True
        )
        st.download_button(
            "Download glossary CSV",
            data=csv_data,
            file_name=file_name,
            mime="text/csv",
            key=f"{key_prefix}_download"
        )


def render_reading_comprehension_generator(
    source_text,
    text_type,
    file_name,
    key_prefix,
    source_language=""
):
    col_count, col_language = st.columns([1, 3])

    with col_count:
        question_count = st.number_input(
            "Questions",
            min_value=1,
            max_value=100,
            value=15,
            step=1,
            key=f"{key_prefix}_question_count"
        )

    with col_language:
        question_language = st.text_input(
            "Question language",
            placeholder="Optional, e.g. German",
            key=f"{key_prefix}_question_language"
        )

    if not source_text or not str(source_text).strip():
        st.info("No text is available for this selection.")
        return

    with st.expander("Source preview"):
        st.text(source_text[:4000])

    if st.button("Create questions", key=f"{key_prefix}_create"):
        with st.spinner("Creating reading comprehension questions..."):
            questions = generate_reading_comprehension_questions(
                source_text,
                question_count=int(question_count),
                source_language=source_language,
                question_language=question_language.strip(),
                text_type=text_type,
            )

        if not questions:
            st.warning("Question generation did not return entries.")
            return

        include_translation = bool(question_language.strip())
        csv_data = reading_comprehension_to_csv(
            questions,
            include_translation=include_translation
        )
        st.dataframe(
            build_reading_comprehension_table(
                questions,
                include_translation=include_translation
            ),
            use_container_width=True
        )
        st.download_button(
            "Download questions CSV",
            data=csv_data,
            file_name=file_name,
            mime="text/csv",
            key=f"{key_prefix}_download"
        )


def resolve_language_aid_source(story_id, selected_scope, chapters):
    if selected_scope == "Full story":
        return (
            build_full_story_markdown(chapters),
            "full story",
            f"story_{story_id}",
        )

    chapter = next(
        (
            chapter
            for chapter in chapters
            if chapter[2] == selected_scope
        ),
        None
    )

    if not chapter:
        return "", "chapter", f"story_{story_id}_chapter"

    chapter_number = chapter[2]
    return (
        chapter[4] or "",
        f"chapter {chapter_number}",
        f"story_{story_id}_chapter_{chapter_number}",
    )


def resolve_glossary_source(story_id, selected_scope, chapters):
    text, text_type, file_name_prefix = resolve_language_aid_source(
        story_id,
        selected_scope,
        chapters
    )
    return text, text_type, f"{file_name_prefix}_glossary.csv"


def build_language_aids_url(story_id, chapter_number=None, aid="Glossary"):
    url = f"?view=Language%20Aids&story_id={story_id}&aid={aid.replace(' ', '%20')}"

    if chapter_number is not None:
        url += f"&chapter_number={chapter_number}"

    return url


def build_glossary_url(story_id, chapter_number=None):
    return build_language_aids_url(
        story_id,
        chapter_number=chapter_number,
        aid="Glossary"
    )


def get_query_param(name):
    value = st.query_params.get(name)

    if isinstance(value, list):
        return value[0] if value else None

    return value


def parse_optional_int(value):
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def find_option_index(options, value):
    if value in options:
        return options.index(value)

    return 0
