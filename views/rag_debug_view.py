import streamlit as st

from database import get_story_beats, get_story_chapters
from services.rag_indexing_service import rebuild_rag_index_from_sqlite
from services.rag_service import (
    build_story_generation_memory,
    group_memory_items_by_type,
    safe_list_memory_items,
    search_memory,
)
from services.story_beat_service import (
    safe_extract_missing_story_beats_for_story,
    safe_extract_save_and_index_story_beats,
)


def render_rag_tab():
    st.header("RAG")

    render_rebuild_section()

    st.divider()

    render_search_section()

    st.divider()

    render_index_section()

    st.divider()

    render_story_beats_debug_section()


def render_rebuild_section():
    st.subheader("Chroma index")

    if st.button(
        "Rebuild Chroma index from SQLite",
        key="rag_rebuild_index"
    ):
        try:
            with st.spinner("Rebuilding Chroma index from SQLite..."):
                counts = rebuild_rag_index_from_sqlite()
            st.success("Chroma index rebuilt from SQLite.")
            st.write(
                "Indexed "
                f"{counts.get('stories', 0)} stories, "
                f"{counts.get('chapter_summaries', 0)} chapter summaries, "
                f"{counts.get('story_beats', 0)} story beats, and "
                f"{counts.get('characters', 0)} characters."
            )
        except Exception as error:
            st.error(f"RAG rebuild failed: {error}")


def render_search_section():
    st.subheader("Search memory")

    query = st.text_input(
        "Query",
        key="rag_search_query"
    )

    col_results, col_story = st.columns(2)

    with col_results:
        n_results = st.number_input(
            "Results",
            min_value=1,
            max_value=25,
            value=5,
            step=1,
            key="rag_search_n_results"
        )

    with col_story:
        story_id_input = st.text_input(
            "Story ID for injected memory preview",
            key="rag_story_id"
        )

    user_request = st.text_area(
        "Generation request preview",
        key="rag_user_request",
        height=120,
    )

    col_search, col_preview = st.columns(2)

    with col_search:
        search = st.button(
            "Search memory",
            key="rag_search"
        )

    with col_preview:
        show_memory = st.button(
            "Preview injected STORY MEMORY",
            key="rag_show_memory"
        )

    if search:
        render_search_results(query, int(n_results))

    if show_memory:
        render_story_memory_preview(
            story_id_input,
            user_request or query,
            int(n_results)
        )


def render_search_results(query, n_results):
    try:
        matches = search_memory(query, n_results=n_results)
    except Exception as error:
        st.error(f"RAG search failed: {error}")
        return

    if not matches:
        st.info("No matches found.")
        return

    for index, match in enumerate(matches, start=1):
        metadata = match.get("metadata", {})
        label = build_memory_item_label(
            index,
            metadata,
            match.get("distance")
        )

        with st.expander(label):
            st.write(match.get("text", ""))
            st.json(metadata)


def render_story_memory_preview(story_id_input, user_request, n_results):
    try:
        story_id = (
            int(story_id_input)
            if story_id_input and story_id_input.strip()
            else None
        )
    except ValueError:
        st.error("Story ID must be a number.")
        return

    try:
        rag_context = build_story_generation_memory(
            story_id=story_id,
            user_request=user_request or "",
            n_results=n_results,
        )
    except Exception as error:
        st.error(f"Failed to build story memory: {error}")
        return

    if not rag_context:
        st.info("No story memory would be injected.")
        return

    st.markdown("**STORY MEMORY injected into prompt**")
    st.code(rag_context)


def render_index_section():
    st.subheader("Inspect index")

    limit = st.number_input(
        "Maximum items to load",
        min_value=1,
        max_value=500,
        value=100,
        step=25,
        key="rag_index_limit"
    )

    items = safe_list_memory_items(limit=int(limit))

    if not items:
        st.info("No Chroma memory items found.")
        return

    grouped_items = order_memory_groups(group_memory_items_by_type(items))

    st.caption(f"{len(items)} item(s) loaded from Chroma.")

    tabs = st.tabs([
        f"{format_memory_type_label(item_type)} ({len(grouped)})"
        for item_type, grouped in grouped_items.items()
    ])

    for tab, (item_type, grouped) in zip(tabs, grouped_items.items()):
        with tab:
            st.markdown(f"### {format_memory_type_label(item_type)}")

            for index, item in enumerate(grouped, start=1):
                metadata = item.get("metadata", {})
                label = build_memory_item_label(index, metadata)

                with st.expander(label):
                    st.write(f"**ID:** {item.get('id', '')}")
                    st.write(item.get("text", ""))
                    st.json(metadata)


def render_story_beats_debug_section():
    st.subheader("Story beats")

    col_story, col_chapter = st.columns(2)

    with col_story:
        story_id_input = st.text_input(
            "Story ID",
            key="rag_beats_story_id"
        )

    with col_chapter:
        chapter_number = st.number_input(
            "Chapter number",
            min_value=0,
            value=0,
            step=1,
            key="rag_beats_chapter_number"
        )

    col_view, col_extract, col_missing = st.columns(3)

    with col_view:
        view_beats = st.button(
            "View extracted beats",
            key="rag_view_story_beats"
        )

    with col_extract:
        run_extraction = st.button(
            "Run beat extraction",
            key="rag_run_story_beats"
        )

    with col_missing:
        run_missing = st.button(
            "Extract missing beats",
            key="rag_run_missing_story_beats"
        )

    story_id = parse_optional_int(story_id_input)

    if story_id_input and story_id is None:
        st.error("Story ID must be a number.")
        return

    if run_extraction:
        run_manual_beat_extraction(story_id, int(chapter_number))

    if run_missing:
        run_missing_beat_extraction(story_id)

    if view_beats:
        render_saved_story_beats(story_id, int(chapter_number))

    st.markdown("**Search story beats**")
    beat_query = st.text_input(
        "Beat query",
        key="rag_story_beat_search_query"
    )
    beat_results = st.number_input(
        "Beat results",
        min_value=1,
        max_value=25,
        value=5,
        step=1,
        key="rag_story_beat_search_results"
    )

    if st.button("Search story beats", key="rag_search_story_beats"):
        render_story_beat_search_results(
            beat_query,
            int(beat_results),
            story_id
        )


def run_manual_beat_extraction(story_id, chapter_number):
    if story_id is None:
        st.error("Story ID is required to run beat extraction.")
        return

    chapter = find_chapter(story_id, chapter_number)

    if not chapter:
        st.error("No matching chapter found.")
        return

    chapter_body = chapter[4]

    if not chapter_body:
        st.info("Chapter has no body to analyse.")
        return

    with st.spinner("Extracting story beats..."):
        beats = safe_extract_save_and_index_story_beats(
            story_id,
            chapter_number,
            chapter_body
        )

    st.success(f"Extracted and indexed {len(beats)} beat(s).")
    render_beat_rows(beats)


def run_missing_beat_extraction(story_id):
    if story_id is None:
        st.error("Story ID is required to extract missing beats.")
        return

    with st.spinner("Extracting missing story beats..."):
        counts = safe_extract_missing_story_beats_for_story(story_id)

    st.success(
        "Checked "
        f"{counts.get('chapters_checked', 0)} chapter(s), extracted "
        f"{counts.get('beats_extracted', 0)} beat(s) across "
        f"{counts.get('chapters_extracted', 0)} chapter(s)."
    )


def render_saved_story_beats(story_id, chapter_number):
    if story_id is None:
        st.error("Story ID is required to view extracted beats.")
        return

    beats = get_story_beats(
        story_id=story_id,
        chapter_number=chapter_number
    )

    if not beats:
        st.info("No story beats found for this chapter.")
        return

    render_beat_rows(beats)


def render_story_beat_search_results(query, n_results, story_id=None):
    if not query or not query.strip():
        st.info("Enter a beat query.")
        return

    try:
        matches = search_memory(
            query,
            n_results=n_results,
            where={"type": "story_beat"}
        )
    except Exception as error:
        st.error(f"Story beat search failed: {error}")
        return

    if story_id is not None:
        matches = [
            match
            for match in matches
            if match.get("metadata", {}).get("story_id") == story_id
        ]

    if not matches:
        st.info("No story beat matches found.")
        return

    for index, match in enumerate(matches, start=1):
        metadata = match.get("metadata", {})
        label = build_memory_item_label(
            index,
            metadata,
            match.get("distance")
        )

        with st.expander(label):
            st.write(match.get("text", ""))
            st.json(metadata)


def render_beat_rows(beats):
    for beat in beats:
        title = beat.get("title") or "Untitled beat"
        label = (
            f"{beat.get('sequence_number')}. "
            f"{title} ({beat.get('beat_type')})"
        )

        with st.expander(label):
            st.json(beat)


def find_chapter(story_id, chapter_number):
    for chapter in get_story_chapters(story_id):
        if chapter[2] == chapter_number:
            return chapter

    return None


def parse_optional_int(value):
    if not value or not str(value).strip():
        return None

    try:
        return int(value)
    except ValueError:
        return None


def build_memory_item_label(index, metadata, distance=None):
    item_type = metadata.get("type") or "memory"
    label = build_memory_item_identity_label(item_type, metadata)

    if not label:
        label = f"{index}: {format_memory_type_label(item_type)}"

    if distance is not None:
        label = f"{label} | distance {distance:.4f}"

    return label


def build_memory_item_identity_label(item_type, metadata):
    if item_type == "story":
        return build_colon_label(
            metadata.get("story_id"),
            metadata.get("name") or metadata.get("title")
        )

    if item_type == "chapter_summary":
        prefix = join_present_values([
            metadata.get("story_id"),
            metadata.get("chapter_number"),
        ])
        return build_colon_label(prefix, metadata.get("title"))

    if item_type == "story_beat":
        prefix = join_present_values([
            metadata.get("story_id"),
            metadata.get("chapter_number"),
            metadata.get("sequence_number"),
        ])
        return build_colon_label(prefix, metadata.get("title"))

    if item_type == "character":
        return build_colon_label(
            metadata.get("character_id"),
            metadata.get("name")
        )

    return ""


def build_colon_label(prefix, name):
    if prefix in (None, "") and not name:
        return ""

    if prefix in (None, ""):
        return str(name)

    if not name:
        return str(prefix)

    return f"{prefix}: {name}"


def join_present_values(values):
    return " / ".join(
        str(value)
        for value in values
        if value not in (None, "")
    )


def format_memory_type_label(item_type):
    labels = {
        "story": "Stories",
        "chapter_summary": "Chapter Summaries",
        "story_beat": "Story Beats",
        "character": "Characters",
        "unknown": "Unknown",
        "memory": "Memory",
    }

    if item_type in labels:
        return labels[item_type]

    return str(item_type).replace("_", " ").capitalize()


def order_memory_groups(grouped_items):
    preferred_order = [
        "story",
        "chapter_summary",
        "story_beat",
        "character",
    ]
    ordered = {}

    for item_type in preferred_order:
        if item_type in grouped_items:
            ordered[item_type] = grouped_items[item_type]

    for item_type in sorted(grouped_items):
        if item_type not in ordered:
            ordered[item_type] = grouped_items[item_type]

    return ordered
