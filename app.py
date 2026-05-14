import streamlit as st

from database import create_tables, run_migrations, seed_common_names
from views.characters_view import render_characters_tab
from views.export_import_view import render_export_import_tab
from views.history_view import render_history_tab
from views.models_view import render_models_tab
from views.profiles_view import render_profiles_tab
from views.sidebar_view import render_llm_settings_sidebar
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

render_llm_settings_sidebar()

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
