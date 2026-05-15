import streamlit as st

from services.rag_indexing_service import rebuild_rag_index_from_sqlite
from services.rag_service import search_memory, build_story_generation_memory


def render_rag_debug_panel():
    with st.expander("RAG / Story Memory"):
        query = st.text_input(
            "Test query",
            key="rag_debug_query"
        )

        story_id_input = st.text_input(
            "Story ID (optional)",
            key="rag_debug_story_id"
        )

        user_request = st.text_area(
            "Generation request (preview)",
            key="rag_debug_user_request",
            height=120,
        )

        col_search, col_rebuild = st.columns(2)

        with col_search:
            search = st.button(
                "Search memory",
                key="rag_debug_search"
            )

        show_memory = st.button(
            "Show STORY MEMORY",
            key="rag_debug_show_memory"
        )

        with col_rebuild:
            rebuild = st.button(
                "Rebuild Chroma index from SQLite",
                key="rag_debug_rebuild"
            )

        if rebuild:
            try:
                with st.spinner("Rebuilding story memory index..."):
                    rebuild_rag_index_from_sqlite()
                st.success("Chroma index rebuilt from SQLite.")
            except Exception as error:
                st.error(f"RAG rebuild failed: {error}")

        if search:
            try:
                matches = search_memory(query, n_results=5)
            except Exception as error:
                st.error(f"RAG search failed: {error}")
                return

            if not matches:
                st.info("No matches found.")
                return

            for index, match in enumerate(matches, start=1):
                metadata = match.get("metadata", {})
                distance = match.get("distance")

                st.markdown(f"**Match {index}**")
                st.write(match.get("text", ""))
                st.json(metadata)
                st.write(f"Distance: {distance}")

        if show_memory:
            # Attempt to parse story_id as int, fall back to None
            try:
                story_id_val = int(story_id_input) if story_id_input and story_id_input.strip() else None
            except Exception:
                story_id_val = None

            try:
                rag_context = build_story_generation_memory(
                    story_id=story_id_val,
                    user_request=(user_request or query or ""),
                    n_results=6,
                )
            except Exception as error:
                st.error(f"Failed to build story memory: {error}")
                rag_context = ""

            if not rag_context:
                st.info("No story memory would be injected.")
            else:
                st.markdown("**STORY MEMORY (injected):**")
                st.code(rag_context)
