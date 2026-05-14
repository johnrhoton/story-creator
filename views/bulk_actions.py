import json
from datetime import datetime

import streamlit as st


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

    if not selected_values:
        return

    export_data = build_export_data(
        build_export_payload(selected_values)
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{export_filename_prefix}_{timestamp}.json"

    col_delete, col_export = st.columns(2)

    with col_delete:
        if st.button(
            delete_button_label,
            key=delete_button_key
        ):
            deleted_count = delete_selected(selected_values)
            st.success(f"Deleted {deleted_count} {item_label}(s).")
            st.rerun()

    with col_export:
        st.download_button(
            export_button_label,
            data=export_data,
            file_name=file_name,
            mime="application/json",
            key=export_button_key
        )


def build_export_data(payload):
    export_data = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        **payload
    }

    return json.dumps(
        export_data,
        indent=2,
        ensure_ascii=False
    )
