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

active_view = st.radio(
    "View",
    [
        "Characters",
        "Profiles",
        "Templates",
        "Stories",
        "Models",
        "History",
        "Export / Import"
    ],
    horizontal=True,
    label_visibility="collapsed",
    key="active_view"
)

if active_view == "Characters":
    render_characters_tab()

elif active_view == "Profiles":
    render_profiles_tab()

elif active_view == "Templates":
    render_templates_tab()

elif active_view == "Stories":
    render_stories_tab()

elif active_view == "Models":
    render_models_tab()

elif active_view == "History":
    render_history_tab()

elif active_view == "Export / Import":
    render_export_import_tab()
