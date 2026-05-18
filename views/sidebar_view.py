import streamlit as st

from database import (
    enable_database_encryption,
    get_database_encryption_status,
    set_active_database_password,
)
from config import DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER
from services.llm_defaults_service import save_llm_defaults
from services.model_service import list_llm_models_by_provider


PROVIDER_OPTIONS = ["Gemini", "Groq", "OpenRouter"]

DEFAULT_MODELS = {
    "Gemini": "gemini-2.5-flash",
    "Groq": "llama-3.3-70b-versatile",
    "OpenRouter": "openrouter/auto"
}


def render_llm_settings_sidebar():
    with st.sidebar:
        st.header("LLM Settings")

        previous_provider = st.session_state.get("llm_provider")
        previous_model = st.session_state.get("llm_model")

        current_provider = st.session_state.get(
            "llm_provider",
            DEFAULT_LLM_PROVIDER
        )

        selected_provider = st.selectbox(
            "Provider",
            PROVIDER_OPTIONS,
            index=PROVIDER_OPTIONS.index(current_provider)
            if current_provider in PROVIDER_OPTIONS
            else 0
        )

        st.session_state["llm_provider"] = selected_provider

        provider_models = list_llm_models_by_provider(selected_provider)
        model_options = [
            row[2]
            for row in provider_models
        ]
        provider_default_model = next(
            (
                row[2]
                for row in provider_models
                if row[4]
            ),
            DEFAULT_MODELS[selected_provider]
        )

        current_model = st.session_state.get(
            "llm_model",
            DEFAULT_LLM_MODEL
            if selected_provider == DEFAULT_LLM_PROVIDER
            else DEFAULT_MODELS[selected_provider]
        )

        if selected_provider != current_provider:
            current_model = provider_default_model

        if model_options:
            if current_model not in model_options:
                current_model = model_options[0]

            st.session_state["llm_model"] = st.selectbox(
                "Model",
                model_options,
                index=model_options.index(current_model)
            )
        else:
            st.session_state["llm_model"] = st.text_input(
                "Model",
                value=current_model
            )

        if (
            previous_provider is not None
            and previous_model is not None
            and (
                st.session_state["llm_provider"] != previous_provider
                or st.session_state["llm_model"] != previous_model
            )
        ):
            save_llm_defaults(
                st.session_state["llm_provider"],
                st.session_state["llm_model"]
            )

        throttle_settings = st.session_state.setdefault(
            "llm_throttle_intervals",
            {}
        )

        throttle_key = (
            f"{st.session_state['llm_provider']}:"
            f"{st.session_state['llm_model']}"
        )

        st.session_state["llm_throttle_interval_seconds"] = st.number_input(
            "Throttle interval in seconds",
            min_value=0.0,
            value=float(throttle_settings.get(throttle_key, 0.0)),
            step=1.0,
            key=f"llm_throttle_input_{throttle_key}"
        )

        throttle_settings[throttle_key] = (
            st.session_state["llm_throttle_interval_seconds"]
        )

        st.divider()
        st.header("Database Encryption")

        database_password = st.text_input(
            "Database password",
            type="password",
            key="database_encryption_password",
            help=(
                "Unlock encrypted fields for this session."
            )
        )

        set_active_database_password(database_password)
        encryption_status = get_database_encryption_status()

        if encryption_status["enabled"]:
            if encryption_status["unlocked"]:
                st.success("Encrypted database fields are unlocked.")
            else:
                st.warning("Encrypted database fields are locked.")
        else:
            st.info("Database field encryption is not enabled.")

        encryption_button_label = (
            "Encrypt clear fields"
            if encryption_status["enabled"]
            else "Enable field encryption"
        )
        encryption_button_disabled = not database_password
        if encryption_status["enabled"]:
            encryption_button_disabled = (
                not database_password
                or not encryption_status["unlocked"]
            )

        if st.button(
            encryption_button_label,
            disabled=encryption_button_disabled
        ):
            try:
                enable_database_encryption(database_password)
                st.success("Configured database fields encrypted.")
                st.rerun()
            except Exception as error:
                st.error(f"Could not update database encryption: {error}")

        st.divider()
        st.header("Import / Export")

        st.toggle(
            "Encrypt downloads",
            key="encrypt_export_downloads",
            help=(
                "Download encrypted values when preparing database exports."
            )
        )
