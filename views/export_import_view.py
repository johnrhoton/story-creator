from datetime import datetime
import logging

import streamlit as st

from config import EXPORT_FILENAME_PREFIX
from database import (
    export_database_to_json,
    export_database_to_yaml,
    import_database_from_json,
    import_database_from_yaml,
    is_database_encryption_enabled,
    reinitialize_database,
)
from services.sync_service import (
    get_sync_status,
    pull_mongo_to_local,
    push_local_to_mongo,
    sync_now,
)
from services.observability_service import (
    EVENT_EXPORT_CREATED,
    EVENT_TEMPLATE_IMPORT,
    record_event,
)
from ui_helpers import format_display_timestamp


logger = logging.getLogger(__name__)


def render_export_import_tab():
    st.header("Export / Import Database")

    st.subheader("Export")

    export_format = st.radio(
        "Export format",
        ["YAML", "JSON"],
        horizontal=True
    )

    database_password = st.session_state.get(
        "database_encryption_password",
        ""
    )
    encrypt_values = st.session_state.get("encrypt_export_downloads", False)
    database_encryption_enabled = is_database_encryption_enabled()
    export_signature = {
        "format": export_format,
        "encrypt_values": encrypt_values,
        "database_encryption_enabled": database_encryption_enabled,
    }

    if st.button("Prepare export file"):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if export_format == "YAML":
                export_data = export_database_to_yaml(
                    encrypt_values=encrypt_values,
                    password=database_password
                )
                export_filename = build_full_export_file_name(
                    timestamp,
                    encrypt_values,
                    "yaml"
                )
                export_mime = "application/x-yaml"
                preview_language = "yaml"
            else:
                export_data = export_database_to_json(
                    encrypt_values=encrypt_values,
                    password=database_password
                )
                export_filename = build_full_export_file_name(
                    timestamp,
                    encrypt_values,
                    "json"
                )
                export_mime = "application/json"
                preview_language = "json"

            st.session_state["prepared_export"] = {
                "data": export_data,
                "filename": export_filename,
                "mime": export_mime,
                "language": preview_language,
                "signature": export_signature,
            }
            record_event(
                EVENT_EXPORT_CREATED,
                status="completed",
                metadata={
                    "format": export_format.lower(),
                    "filename": export_filename,
                    "encrypted": encrypt_values,
                    "bytes": len(export_data.encode("utf-8")),
                },
            )

        except Exception as error:
            logger.exception("Export failed.")
            st.error(f"Export failed: {error}")

    prepared_export = st.session_state.get("prepared_export")

    if (
        prepared_export
        and prepared_export.get("signature") == export_signature
    ):
        st.download_button(
            label=f"Download database as {export_format}",
            data=prepared_export["data"],
            file_name=prepared_export["filename"],
            mime=prepared_export["mime"]
        )

        with st.expander(f"Preview {export_format}"):
            st.code(
                prepared_export["data"],
                language=prepared_export["language"]
            )

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
            logger.exception("Database reinitialization failed.")
            st.error(f"Database reinitialization failed: {error}")

    st.divider()

    st.subheader("Import")

    if database_password:
        st.caption(
            "Imported plain-text values will be stored with database "
            "field encryption."
        )
    else:
        st.caption(
            "Imported plain-text values will be stored as plain text."
        )

    uploaded_file = st.file_uploader(
        "Choose a JSON or YAML export file",
        type=["json", "yaml", "yml"]
    )

    if uploaded_file is not None:
        if st.button("Import file into database"):
            try:
                uploaded_name = uploaded_file.name.lower()

                if uploaded_name.endswith((".yaml", ".yml")):
                    result = import_database_from_yaml(
                        uploaded_file,
                        password=database_password,
                        database_password=database_password
                    )
                else:
                    result = import_database_from_json(
                        uploaded_file,
                        password=database_password,
                        database_password=database_password
                    )

                st.success("Import complete.")
                st.json(result)
                record_event(
                    EVENT_TEMPLATE_IMPORT,
                    status="completed",
                    metadata={
                        "filename": uploaded_file.name,
                        "counts": result,
                    },
                )

                st.rerun()

            except Exception as error:
                logger.exception("Import failed.")
                record_event(
                    EVENT_TEMPLATE_IMPORT,
                    status="failed",
                    error_type=type(error).__name__,
                    error_message=str(error),
                    metadata={"filename": uploaded_file.name},
                )
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
            logger.exception("Could not check MongoDB sync status.")
            st.error(f"Could not check MongoDB sync status: {error}")

    if st.button("Sync now"):
        try:
            result = sync_now(database_password=database_password)

            if result["direction"] == "conflict":
                st.warning(result["message"])
            else:
                st.success(format_display_timestamp(result["message"]))

            if result["details"]:
                st.json(result["details"])

            st.rerun()

        except Exception as error:
            logger.exception("MongoDB sync failed.")
            st.error(f"MongoDB sync failed: {error}")

    col_pull, col_push = st.columns(2)

    with col_pull:
        if st.button("Pull MongoDB to local"):
            try:
                result = pull_mongo_to_local(
                    database_password=database_password
                )
                st.success("Pulled MongoDB backup into local SQLite.")
                st.json(result)
                st.rerun()

            except Exception as error:
                logger.exception("MongoDB pull failed.")
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
                logger.exception("MongoDB push failed.")
                st.error(f"MongoDB push failed: {error}")


def build_full_export_file_name(timestamp, encrypted, extension):
    encrypted_suffix = "_encrypted" if encrypted else ""
    return (
        f"{EXPORT_FILENAME_PREFIX}_full_{timestamp}"
        f"{encrypted_suffix}.{extension}"
    )
