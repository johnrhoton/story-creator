from datetime import datetime

import streamlit as st

from database import export_database_to_json, import_database_from_json


def render_export_import_tab():
    st.header("Export / Import Database")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"character_database_export_{timestamp}.json"

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
                imported_profiles, imported_characters = import_database_from_json(
                    uploaded_file
                )

                st.success(
                    f"Import complete: {imported_profiles} profiles and "
                    f"{imported_characters} characters imported."
                )

                st.rerun()

            except Exception as error:
                st.error(f"Import failed: {error}")