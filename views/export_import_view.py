from datetime import datetime

import streamlit as st

from database import export_database_to_json, import_database_from_json
from services.sync_service import get_sync_status, sync_now


def render_export_import_tab():
    st.header("Export / Import Database")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"story_creator_export_{timestamp}.json"

    json_data = export_database_to_json()

    st.subheader("Export")

    st.download_button(
        label="Download database as JSON",
        data=json_data,
        file_name=export_filename,
        mime="application/json"
    )

    with st.expander("Preview JSON"):
        st.code(json_data, language="json")

    st.divider()

    st.subheader("Import")

    uploaded_file = st.file_uploader(
        "Choose a JSON export file",
        type=["json"]
    )

    if uploaded_file is not None:
        if st.button("Import JSON into database"):
            try:
                result = import_database_from_json(
                    uploaded_file
                )

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

            st.write("Local timestamp:", status["local_timestamp"])
            st.write("MongoDB timestamp:", status["mongo_timestamp"])
            st.write("Direction:", status["direction"])

        except Exception as error:
            st.error(f"Could not check MongoDB sync status: {error}")

    if st.button("Sync now"):
        try:
            result = sync_now()

            if result["direction"] == "conflict":
                st.warning(result["message"])
            else:
                st.success(result["message"])

            if result["details"]:
                st.json(result["details"])

            st.rerun()

        except Exception as error:
            st.error(f"MongoDB sync failed: {error}")
