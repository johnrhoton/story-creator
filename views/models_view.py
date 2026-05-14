import json
from datetime import datetime

import streamlit as st

from services.model_service import (
    create_llm_model,
    delete_existing_llm_models,
    delete_existing_llm_model,
    list_llm_models_for_export,
    list_llm_models,
    set_existing_llm_model_as_default,
)


PROVIDER_OPTIONS = ["Gemini", "Groq", "OpenRouter"]


def render_models_tab():
    st.header("Models")

    with st.form("create_llm_model_form"):
        provider = st.selectbox(
            "Provider",
            PROVIDER_OPTIONS
        )

        model = st.text_input("Model")

        best_use = st.text_input("Best use")

        is_default = st.checkbox("Default for this provider")

        save_model = st.form_submit_button("Save model")

    if save_model:
        if not model.strip():
            st.error("Model is required.")
        else:
            create_llm_model(
                provider,
                model.strip(),
                best_use.strip(),
                is_default
            )
            st.success(f"Model '{model.strip()}' saved.")
            st.rerun()

    st.divider()

    models = list_llm_models()

    if not models:
        st.info(
            "No models saved yet. Run `./venv/bin/python seed_llm_models.py` "
            "to pre-fill the starter list."
        )
        return

    render_model_bulk_actions(models)

    for provider in PROVIDER_OPTIONS:
        provider_models = [
            row for row in models
            if row[1] == provider
        ]

        st.subheader(provider)

        if not provider_models:
            st.info(f"No {provider} models saved yet.")
            continue

        for row in provider_models:
            (
                model_id,
                _provider,
                model,
                best_use,
                is_default
            ) = row

            title = model

            if is_default:
                title = f"{model} (default)"

            with st.expander(title):
                st.write(f"**Best use:** {best_use or ''}")
                st.write(f"**Default:** {'Yes' if is_default else 'No'}")

                if not is_default:
                    if st.button(
                        "Make default",
                        key=f"default_llm_model_{model_id}"
                    ):
                        set_existing_llm_model_as_default(model_id)
                        st.success("Default model updated.")
                        st.rerun()

                if st.button(
                    "Delete model",
                    key=f"delete_llm_model_{model_id}"
                ):
                    delete_existing_llm_model(model_id)
                    st.success("Model deleted.")
                    st.rerun()


def render_model_bulk_actions(models):
    model_options = {
        build_model_option_label(row): row[0]
        for row in models
    }

    selected_labels = st.multiselect(
        "Select models",
        list(model_options.keys()),
        key="selected_model_bulk_actions"
    )

    selected_ids = [
        model_options[label]
        for label in selected_labels
    ]

    if not selected_ids:
        return

    export_data = build_selected_models_export(selected_ids)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"exported_models_{timestamp}.json"

    col_delete, col_export = st.columns(2)

    with col_delete:
        if st.button(
            "Delete selected models",
            key="delete_selected_models"
        ):
            deleted_count = delete_existing_llm_models(selected_ids)
            st.success(f"Deleted {deleted_count} model(s).")
            st.rerun()

    with col_export:
        st.download_button(
            "Export selected models",
            data=export_data,
            file_name=file_name,
            mime="application/json",
            key="export_selected_models"
        )


def build_model_option_label(row):
    model_id = row[0]
    provider = row[1]
    model = row[2]
    is_default = row[4]

    default_label = " default" if is_default else ""

    return f"#{model_id} - {provider} - {model}{default_label}"


def build_selected_models_export(selected_ids):
    models = list_llm_models_for_export(selected_ids)

    export_data = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "llm_models": models
    }

    return json.dumps(
        export_data,
        indent=2,
        ensure_ascii=False
    )
