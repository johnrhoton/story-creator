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
    user = getattr(st, "user", None)

    if not getattr(user, "is_logged_in", False):
        st.title("Story Builder")
        st.info("Sign in with Google to continue.")

        if st.button("Log in with Google"):
            try:
                st.login()
            except StreamlitAuthError as error:
                if "Authlib" not in str(error):
                    logger.exception("Streamlit authentication failed.")
                    st.error("Streamlit authentication is not configured.")
                else:
                    logger.exception("Authlib is missing for Streamlit authentication.")
                    st.error(
                        "Authentication requires Authlib. Install dependencies "
                        "with `venv/bin/pip install -r requirements.txt`, then "
                        "restart Streamlit."
                    )
            except Exception as error:
                logger.exception("Streamlit login failed.")
                st.error(f"Could not start Google login: {error}")

        st.stop()

    login_google_sub = getattr(user, "sub", "")
    email = getattr(user, "email", "")

    if not login_google_sub or not email:
        st.error("Streamlit authentication did not provide user details.")
        if st.button("Log out"):
            st.logout()
        st.stop()

    st.session_state["google_user_id"] = login_google_sub

    authorized_user = get_authorized_user_by_identity(
        google_sub=login_google_sub,
        email=email,
    )

    if not authorized_user:
        st.error("Not authorised")
        st.write(f"Signed in as: {email}")

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
        bind_authorized_user_google_sub(user_id, login_google_sub)

    st.session_state["authorized_user_id"] = user_id
    st.session_state["authorized_user_email"] = email
    st.session_state["authorized_user_role"] = role


def render_auth_sidebar():
    with st.sidebar:
        user = getattr(st, "user", None)
        email = st.session_state.get(
            "authorized_user_email",
            getattr(user, "email", "")
        )
        role = st.session_state.get("authorized_user_role", "")

        if email:
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
