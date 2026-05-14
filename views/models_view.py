import streamlit as st

from services.model_service import (
    create_llm_model,
    delete_existing_llm_models,
    delete_existing_llm_model,
    list_llm_models_for_export,
    list_llm_models,
    set_existing_llm_model_as_default,
)
from views.bulk_actions import render_bulk_actions


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
            "No models saved yet. Run this from the project root to "
            "pre-fill the starter list:\n\n"
            "`./venv/bin/python scripts/seed_llm_models.py`"
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
    render_bulk_actions(
        models,
        "Select models",
        "selected_model_bulk_actions",
        build_model_option_label,
        lambda row: row[0],
        build_selected_models_export_payload,
        "exported_models",
        delete_existing_llm_models,
        "Delete selected models",
        "delete_selected_models",
        "Export selected models",
        "export_selected_models",
        "model"
    )


def build_model_option_label(row):
    model_id = row[0]
    provider = row[1]
    model = row[2]
    is_default = row[4]

    default_label = " default" if is_default else ""

    return f"#{model_id} - {provider} - {model}{default_label}"


def build_selected_models_export_payload(selected_ids):
    models = list_llm_models_for_export(selected_ids)

    return {
        "llm_models": models
    }
