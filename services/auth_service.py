from collections.abc import Mapping
import logging

import streamlit as st
from streamlit.errors import StreamlitAuthError

from database import (
    ADMINISTRATOR_ROLE,
    bind_authorized_user_google_sub,
    get_authorized_user_by_identity,
)


logger = logging.getLogger(__name__)


def require_login():
    if not st.user.is_logged_in:
        st.title("Story Builder")
        st.info("Sign in with Google to continue.")

        if st.button("Sign in with Google"):
            try:
                provider = get_login_provider(st.secrets.get("auth", {}))
                if provider:
                    st.login(provider)
                else:
                    st.login()
            except StreamlitAuthError as error:
                if "Authlib" not in str(error):
                    logger.exception("Streamlit authentication failed.")
                    raise

                logger.exception("Authlib is missing for Streamlit authentication.")
                st.error(
                    "Authentication requires Authlib. Install dependencies "
                    "with `venv/bin/pip install -r requirements.txt`, then "
                    "restart Streamlit."
                )

        st.stop()

    st.session_state["google_user_id"] = st.user.sub

    authorized_user = get_authorized_user_by_identity(
        google_sub=st.user.sub,
        email=st.user.email,
    )

    if not authorized_user:
        st.error("Not authorised")
        st.write(f"Signed in as: {st.user.email}")

        if st.button("Log out"):
            st.logout()

        st.stop()

    (
        user_id,
        email,
        role,
        google_sub,
        _updated_at,
    ) = authorized_user

    if not google_sub:
        bind_authorized_user_google_sub(user_id, st.user.sub)

    st.session_state["authorized_user_id"] = user_id
    st.session_state["authorized_user_email"] = email
    st.session_state["authorized_user_role"] = role


def render_auth_sidebar():
    with st.sidebar:
        email = st.session_state.get("authorized_user_email", st.user.email)
        role = st.session_state.get("authorized_user_role", "")

        st.caption(f"Signed in as {email}")

        if role:
            st.caption(f"Role: {role}")

        if st.button("Log out", key="auth_logout"):
            st.logout()

        st.divider()


def current_user_is_administrator():
    return st.session_state.get("authorized_user_role") == ADMINISTRATOR_ROLE


def get_login_provider(auth_config):
    if (
        isinstance(auth_config, Mapping)
        and isinstance(auth_config.get("google"), Mapping)
    ):
        return "google"

    return None
