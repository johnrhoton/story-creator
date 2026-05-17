import streamlit as st

from services.rag_indexing_service import rebuild_rag_index_from_sqlite
from services.rag_service import (
    build_story_generation_memory,
    group_memory_items_by_type,
    safe_list_memory_items,
    search_memory,
)


def render_rag_tab():
    st.header("RAG")

    render_rebuild_section()

    st.divider()

    render_search_section()

    st.divider()

    render_index_section()


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
                f"{counts.get('characters', 0)} characters, and "
                f"{counts.get('chapter_summaries', 0)} chapter summaries."
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

    grouped_items = group_memory_items_by_type(items)

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


def build_memory_item_label(index, metadata, distance=None):
    item_type = metadata.get("type") or "memory"
    name = (
        metadata.get("name")
        or metadata.get("title")
        or metadata.get("chapter_number")
        or metadata.get("character_id")
        or ""
    )

    label = f"{index}. {format_memory_type_label(item_type)}"

    if name != "":
        label = f"{label}: {name}"

    if distance is not None:
        label = f"{label} | distance {distance:.4f}"

    return label


def format_memory_type_label(item_type):
    labels = {
        "story": "Stories",
        "chapter_summary": "Chapter Summaries",
        "character": "Characters",
        "unknown": "Unknown",
        "memory": "Memory",
    }

    if item_type in labels:
        return labels[item_type]

    return str(item_type).replace("_", " ").capitalize()
