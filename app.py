import streamlit as st

from config import DEFAULT_LLM_MODEL, DEFAULT_LLM_PROVIDER
from database import create_tables, run_migrations, seed_common_names
from services.model_service import list_llm_models_by_provider
from views.characters_view import render_characters_tab
from views.export_import_view import render_export_import_tab
from views.history_view import render_history_tab
from views.models_view import render_models_tab
from views.profiles_view import render_profiles_tab
from views.stories_view import render_stories_tab
from views.templates_view import render_templates_tab


run_migrations()
create_tables()
seed_common_names()

st.set_page_config(
    page_title="Story Builder",
    page_icon="✍️",
    layout="wide"
)

st.title("Story Builder")

with st.sidebar:
    st.header("LLM Settings")

    provider_options = ["Gemini", "Groq", "OpenRouter"]

    default_models = {
        "Gemini": "gemini-2.5-flash",
        "Groq": "llama-3.3-70b-versatile",
        "OpenRouter": "openrouter/auto"
    }

    current_provider = st.session_state.get(
        "llm_provider",
        DEFAULT_LLM_PROVIDER
    )

    selected_provider = st.selectbox(
        "Provider",
        provider_options,
        index=provider_options.index(current_provider)
        if current_provider in provider_options
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
        default_models[selected_provider]
    )

    current_model = st.session_state.get(
        "llm_model",
        DEFAULT_LLM_MODEL
        if selected_provider == DEFAULT_LLM_PROVIDER
        else default_models[selected_provider]
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

tab_characters, tab_profiles, tab_templates, tab_stories, tab_models, tab_history, tab_export_import = st.tabs(
    [
        "Characters",
        "Profiles",
        "Templates",
        "Stories",
        "Models",
        "History",
        "Export / Import"
    ]
)

with tab_characters:
    render_characters_tab()

with tab_profiles:
    render_profiles_tab()

with tab_templates:
    render_templates_tab()

with tab_stories:
    render_stories_tab()

with tab_models:
    render_models_tab()

with tab_history:
    render_history_tab()

with tab_export_import:
    render_export_import_tab()
