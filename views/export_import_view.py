from datetime import datetime

import streamlit as st

from config import EXPORT_FILENAME_PREFIX
from database import (
    export_database_to_json,
    export_database_to_yaml,
    import_database_from_json,
    import_database_from_yaml,
    reinitialize_database,
)
from services.sync_service import (
    get_sync_status,
    pull_mongo_to_local,
    push_local_to_mongo,
    sync_now,
)
from ui_helpers import format_display_timestamp


def render_export_import_tab():
    st.header("Export / Import Database")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    st.subheader("Export")

    export_format = st.radio(
        "Export format",
        ["JSON", "YAML"],
        horizontal=True
    )

    if export_format == "YAML":
        export_data = export_database_to_yaml()
        export_filename = f"{EXPORT_FILENAME_PREFIX}_{timestamp}.yaml"
        export_mime = "application/x-yaml"
        preview_language = "yaml"
    else:
        export_data = export_database_to_json()
        export_filename = f"{EXPORT_FILENAME_PREFIX}_{timestamp}.json"
        export_mime = "application/json"
        preview_language = "json"

    st.download_button(
        label=f"Download database as {export_format}",
        data=export_data,
        file_name=export_filename,
        mime=export_mime
    )

    with st.expander(f"Preview {export_format}"):
        st.code(export_data, language=preview_language)

    st.divider()

    st.subheader("Database Maintenance")

    confirm_reinitialize = st.checkbox(
        "I understand this will archive the current database and start a new empty one."
    )

    if st.button(
        "Reinitialize database",
        disabled=not confirm_reinitialize
    ):
        try:
            archived_path = reinitialize_database()

            if archived_path:
                st.success(
                    f"Database archived as {archived_path}. "
                    "A new empty database was created."
                )
            else:
                st.success("A new empty database was created.")

            st.rerun()

        except Exception as error:
            st.error(f"Database reinitialization failed: {error}")

    st.divider()

    st.subheader("Import")

    uploaded_file = st.file_uploader(
        "Choose a JSON or YAML export file",
        type=["json", "yaml", "yml"]
    )

    if uploaded_file is not None:
        if st.button("Import file into database"):
            try:
                uploaded_name = uploaded_file.name.lower()

                if uploaded_name.endswith((".yaml", ".yml")):
                    result = import_database_from_yaml(uploaded_file)
                else:
                    result = import_database_from_json(uploaded_file)

                st.success("Import complete.")
                st.json(result)

                st.rerun()

            except Exception as error:
                st.error(f"Import failed: {error}")

    st.divider()

    st.subheader("MongoDB Sync")

    st.caption(
        "This sync compares local SQLite content with one MongoDB backup "
        "document and warns before overwriting diverged changes."
    )

    if st.button("Check sync status"):
        try:
            status = get_sync_status()

            if status["direction"] == "conflict":
                st.warning(status["message"])
            else:
                st.info(status["message"])

            st.write(
                "Local timestamp:",
                format_display_timestamp(status["local_timestamp"])
            )
            st.write(
                "MongoDB timestamp:",
                format_display_timestamp(status["mongo_timestamp"])
            )
            st.write("Direction:", status["direction"])

        except Exception as error:
            st.error(f"Could not check MongoDB sync status: {error}")

    if st.button("Sync now"):
        try:
            result = sync_now()

            if result["direction"] == "conflict":
                st.warning(result["message"])
            else:
                st.success(format_display_timestamp(result["message"]))

            if result["details"]:
                st.json(result["details"])

            st.rerun()

        except Exception as error:
            st.error(f"MongoDB sync failed: {error}")

    col_pull, col_push = st.columns(2)

    with col_pull:
        if st.button("Pull MongoDB to local"):
            try:
                result = pull_mongo_to_local()
                st.success("Pulled MongoDB backup into local SQLite.")
                st.json(result)
                st.rerun()

            except Exception as error:
                st.error(f"MongoDB pull failed: {error}")

    with col_push:
        if st.button("Push local to MongoDB"):
            try:
                timestamp = push_local_to_mongo()
                st.success(
                    "Uploaded local SQLite data to MongoDB at "
                    f"{format_display_timestamp(timestamp)}."
                )
                st.rerun()

            except Exception as error:
                st.error(f"MongoDB push failed: {error}")
