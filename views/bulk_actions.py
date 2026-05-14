from datetime import datetime

import streamlit as st
import yaml

from config import EXPORT_FILENAME_PREFIX
from database import (
    get_database_encryption_export_metadata,
    is_database_encryption_enabled,
)
from database.db_encryption import DATABASE_ENCRYPTION_EXPORT_KEY


def render_bulk_actions(
    rows,
    selection_label,
    selection_key,
    option_label,
    option_value,
    build_export_payload,
    export_filename_prefix,
    delete_selected,
    delete_button_label,
    delete_button_key,
    export_button_label,
    export_button_key,
    item_label
):
    st.markdown("**Bulk actions**")

    options = {
        option_label(row): option_value(row)
        for row in rows
    }

    selected_labels = st.multiselect(
        selection_label,
        list(options.keys()),
        key=selection_key
    )

    selected_values = [
        options[label]
        for label in selected_labels
    ]

    selected_count = len(selected_values)
    st.caption(f"{selected_count} {item_label}(s) selected.")
    encrypt_download = st.session_state.get(
        "encrypt_export_downloads",
        False
    )
    export_disabled = not selected_values

    if selected_values and not export_disabled:
        export_data = build_export_data(
            build_export_payload(selected_values),
            include_database_encryption_metadata=encrypt_download
        )
    else:
        export_data = ""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = build_bulk_export_file_name(
        export_filename_prefix,
        timestamp,
        encrypt_download
    )

    col_delete, col_export = st.columns(2)

    with col_delete:
        if st.button(
            delete_button_label,
            key=delete_button_key,
            disabled=not selected_values
        ):
            deleted_count = delete_selected(selected_values)
            st.success(f"Deleted {deleted_count} {item_label}(s).")
            st.rerun()

    with col_export:
        st.download_button(
            export_button_label,
            data=export_data,
            file_name=file_name,
            mime="application/x-yaml",
            key=export_button_key,
            disabled=export_disabled
        )


def build_export_data(payload, include_database_encryption_metadata=False):
    export_data = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        **payload
    }

    if (
        include_database_encryption_metadata
        and is_database_encryption_enabled()
    ):
        export_data[DATABASE_ENCRYPTION_EXPORT_KEY] = (
            get_database_encryption_export_metadata()
        )

    return yaml.safe_dump(
        export_data,
        allow_unicode=True,
        sort_keys=False
    )


def build_bulk_export_file_name(export_filename_prefix, timestamp, encrypted):
    item_name = normalize_export_item_name(export_filename_prefix)
    encrypted_suffix = "_encrypted" if encrypted else ""
    return (
        f"{EXPORT_FILENAME_PREFIX}__{item_name}_{timestamp}"
        f"{encrypted_suffix}.yaml"
    )


def normalize_export_item_name(export_filename_prefix):
    item_name = export_filename_prefix
    if item_name.startswith("exported_"):
        item_name = item_name.removeprefix("exported_")
    if item_name.startswith("export_"):
        item_name = item_name.removeprefix("export_")
    return item_name
