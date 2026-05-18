from dotenv import load_dotenv


load_dotenv()

import streamlit as st

from database import (
    create_tables,
    get_database_encryption_status,
    get_database_provider_status,
    run_migrations,
    seed_common_names,
)
from services.auth_service import current_user_is_administrator, require_login


def get_view_index_from_query_params(view_options):
    view = st.query_params.get("view")

    if isinstance(view, list):
        view = view[0] if view else None

    if view == "Glossary":
        view = "Language Aids"

    if view == "RAG":
        view = "Story Memory"

    if view in view_options:
        return view_options.index(view)

    return view_options.index("Stories")


st.set_page_config(
    page_title="Story Builder",
    page_icon="✍️",
    layout="wide"
)

database_provider_status = get_database_provider_status()
st.caption(
    "Database provider: "
    f"{database_provider_status['label']}"
)

try:
    run_migrations()
    create_tables()
    seed_common_names()
except Exception as error:
    st.error(
        "Database startup failed for "
        f"{database_provider_status['label']}: {error}"
    )
    st.stop()

require_login()

from views.administration_view import render_administration_tab
from views.characters_view import render_characters_tab
from views.export_import_view import render_export_import_tab
from views.language_aids_view import render_language_aids_tab
from views.history_view import render_history_tab
from views.models_view import render_models_tab
from views.profiles_view import render_profiles_tab
from views.story_memory_view import render_story_memory_tab
from views.sidebar_view import render_llm_settings_sidebar
from views.stories_view import render_stories_tab
from views.templates_view import render_templates_tab


st.title("Story Builder")

render_llm_settings_sidebar()

database_encryption_status = get_database_encryption_status()

if (
    database_encryption_status["enabled"]
    and not database_encryption_status["unlocked"]
):
    st.warning("Database fields are encrypted and currently locked.")
    st.info("Enter the database password in the sidebar to continue.")
    st.stop()

VIEW_OPTIONS = [
    "Characters",
    "Profiles",
    "Templates",
    "Stories",
    "Story Memory",
    "Language Aids",
    "Models",
    "History",
    "Export / Import"
]

if current_user_is_administrator():
    VIEW_OPTIONS.append("Administration")

active_view = st.radio(
    "View",
    VIEW_OPTIONS,
    horizontal=True,
    index=get_view_index_from_query_params(VIEW_OPTIONS),
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

elif active_view == "Story Memory":
    render_story_memory_tab()

elif active_view == "Language Aids":
    render_language_aids_tab()

elif active_view == "Models":
    render_models_tab()

elif active_view == "History":
    render_history_tab()

elif active_view == "Export / Import":
    render_export_import_tab()

elif active_view == "Administration":
    render_administration_tab()
