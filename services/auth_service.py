from collections.abc import Mapping
import logging

import streamlit as st
from streamlit.errors import StreamlitAuthError

from config import get_config_bool
from database import (
    ADMINISTRATOR_ROLE,
    bind_authorized_user_google_sub,
    get_authorized_user_by_identity,
)


logger = logging.getLogger(__name__)


def require_login():
    user = getattr(st, "user", None)
    auth_config = st.secrets.get("auth", {})
    auth_debug = get_auth_debug_enabled(auth_config)

    if not getattr(user, "is_logged_in", False):
        st.title("Story Builder")
        st.info("Sign in with Google to continue.")
        render_auth_debug_panel(auth_config, user, auth_debug)

        if st.button("Log in with Google"):
            try:
                provider = get_login_provider(auth_config)
                log_auth_debug(
                    "Starting Streamlit login.",
                    auth_config,
                    user,
                    auth_debug,
                    login_provider=provider or "default",
                )
                if provider:
                    st.login(provider)
                else:
                    st.login()
            except StreamlitAuthError as error:
                log_auth_debug(
                    "Streamlit authentication error.",
                    auth_config,
                    user,
                    auth_debug,
                    login_provider=get_login_provider(auth_config) or "default",
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
                if "Authlib" not in str(error):
                    logger.exception("Streamlit authentication failed.")
                    st.error(
                        "Streamlit authentication is not configured. "
                        "Configure Google credentials under `[auth.google]` "
                        "or provide default `[auth]` credentials."
                    )
                else:
                    logger.exception("Authlib is missing for Streamlit authentication.")
                    st.error(
                        "Authentication requires Authlib. Install dependencies "
                        "with `venv/bin/pip install -r requirements.txt`, then "
                        "restart Streamlit."
                    )
            except Exception as error:
                log_auth_debug(
                    "Unexpected Streamlit login error.",
                    auth_config,
                    user,
                    auth_debug,
                    login_provider=get_login_provider(auth_config) or "default",
                    error_type=type(error).__name__,
                    error_message=str(error),
                )
                logger.exception("Streamlit login failed.")
                st.error(f"Could not start Google login: {error}")

        st.stop()

    login_google_sub = getattr(user, "sub", "")
    email = getattr(user, "email", "")

    log_auth_debug(
        "Streamlit user is logged in.",
        auth_config,
        user,
        auth_debug,
        user_email=email,
        has_user_sub=bool(login_google_sub),
    )

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
        log_auth_debug(
            "Logged-in user is not authorized in database.",
            auth_config,
            user,
            auth_debug,
            user_email=email,
            has_user_sub=bool(login_google_sub),
        )
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

    log_auth_debug(
        "Logged-in user authorized.",
        auth_config,
        user,
        auth_debug,
        user_email=email,
        role=role,
    )

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


def get_auth_debug_enabled(auth_config):
    if isinstance(auth_config, Mapping):
        value = auth_config.get("debug")
        if isinstance(value, bool):
            return value
        if value not in (None, ""):
            return str(value).strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }

    return get_config_bool("AUTH_DEBUG", False)


def render_auth_debug_panel(auth_config, user, enabled):
    if not enabled:
        return

    with st.expander("Authentication debug", expanded=True):
        st.json(build_auth_debug_summary(auth_config, user))


def log_auth_debug(message, auth_config, user, enabled, **extra):
    if not enabled:
        return

    logger.info(
        "%s %s",
        message,
        build_auth_debug_summary(auth_config, user, **extra),
    )


def build_auth_debug_summary(auth_config, user=None, **extra):
    auth_config = auth_config if isinstance(auth_config, Mapping) else {}
    google_config = auth_config.get("google", {})
    google_config = google_config if isinstance(google_config, Mapping) else {}
    redirect_uri = auth_config.get("redirect_uri", "")

    summary = {
        "auth_debug_enabled": get_auth_debug_enabled(auth_config),
        "auth_section_present": bool(auth_config),
        "cookie_secret_configured": bool(auth_config.get("cookie_secret")),
        "default_provider_credentials_configured": required_auth_keys_present(
            auth_config
        ),
        "google_provider_configured": required_auth_keys_present(google_config),
        "login_provider": get_login_provider(auth_config) or "default",
        "named_provider_sections": sorted([
            key
            for key, value in auth_config.items()
            if isinstance(value, Mapping)
        ]),
        "redirect_uri": redirect_uri,
        "redirect_uri_contains_cloud_path_prefix": "/~/+/" in redirect_uri,
        "user_has_email": bool(getattr(user, "email", "")),
        "user_has_is_logged_in": hasattr(user, "is_logged_in"),
        "user_has_sub": bool(getattr(user, "sub", "")),
        "user_is_logged_in": bool(getattr(user, "is_logged_in", False)),
    }

    summary.update(extra)

    return summary


def required_auth_keys_present(config):
    return all(
        bool(config.get(key))
        for key in [
            "client_id",
            "client_secret",
            "server_metadata_url",
        ]
    )
