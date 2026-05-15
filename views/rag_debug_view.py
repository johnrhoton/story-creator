import streamlit as st

from services.rag_indexing_service import rebuild_rag_index_from_sqlite
from services.rag_service import search_memory


def render_rag_debug_panel():
    with st.expander("RAG / Story Memory"):
        query = st.text_input(
            "Test query",
            key="rag_debug_query"
        )

        col_search, col_rebuild = st.columns(2)

        with col_search:
            search = st.button(
                "Search memory",
                key="rag_debug_search"
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
