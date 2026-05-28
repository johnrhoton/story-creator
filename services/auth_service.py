from collections.abc import Mapping
import logging
import os
from pathlib import Path

import streamlit as st
from streamlit.errors import StreamlitAuthError

from config import get_config, get_config_bool
from database import (
    ADMINISTRATOR_ROLE,
    bind_authorized_user_google_sub,
    get_authorized_user_by_identity,
)


logger = logging.getLogger(__name__)

GOOGLE_SERVER_METADATA_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)


def require_login():
    auth_config = build_auth_config()
    if auth_config_is_complete(auth_config):
        ensure_streamlit_auth_secrets_from_env(auth_config)
    user = getattr(st, "user", None)
    auth_debug = get_auth_debug_enabled(auth_config)

    if not getattr(user, "is_logged_in", False):
        st.title("Story Builder")
        st.info("Sign in with Google to continue.")
        render_auth_debug_panel(auth_config, user, auth_debug)

        if not auth_config_is_complete(auth_config):
            warn_auth_config_missing_once()
            st.warning(
                "Authentication is not configured. Set AUTH_COOKIE_SECRET, "
                "AUTH_REDIRECT_URI, GOOGLE_CLIENT_ID, and "
                "GOOGLE_CLIENT_SECRET to enable Google login."
            )
        elif st.button("Log in with Google"):
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


def build_auth_config():
    google_config = {
        "client_id": get_config("GOOGLE_CLIENT_ID", ""),
        "client_secret": get_config("GOOGLE_CLIENT_SECRET", ""),
        "server_metadata_url": get_config(
            "GOOGLE_SERVER_METADATA_URL",
            GOOGLE_SERVER_METADATA_URL,
        ),
    }

    auth_config = {
        "redirect_uri": get_config("AUTH_REDIRECT_URI", ""),
        "cookie_secret": get_config("AUTH_COOKIE_SECRET", ""),
        "debug": get_config_bool("AUTH_DEBUG", False),
        "google": google_config,
    }

    return prune_empty_auth_config(auth_config)


def prune_empty_auth_config(auth_config):
    pruned = {}

    for key, value in auth_config.items():
        if isinstance(value, Mapping):
            nested = {
                nested_key: nested_value
                for nested_key, nested_value in value.items()
                if nested_value not in (None, "")
            }
            if nested:
                pruned[key] = nested
        elif value not in (None, ""):
            pruned[key] = value

    return pruned


def auth_config_is_complete(auth_config):
    if not isinstance(auth_config, Mapping):
        return False

    google_config = auth_config.get("google", {})
    google_config = google_config if isinstance(google_config, Mapping) else {}

    return (
        bool(auth_config.get("redirect_uri"))
        and bool(auth_config.get("cookie_secret"))
        and required_auth_keys_present(google_config)
    )


def get_login_provider(auth_config):
    if (
        isinstance(auth_config, Mapping)
        and isinstance(auth_config.get("google"), Mapping)
    ):
        return "google"

    return None


def warn_auth_config_missing_once():
    if st.session_state.get("auth_config_missing_warned"):
        return

    logger.warning(
        "Authentication is not configured. Set AUTH_COOKIE_SECRET, "
        "AUTH_REDIRECT_URI, GOOGLE_CLIENT_ID, and GOOGLE_CLIENT_SECRET, "
        "or provide equivalent Streamlit secrets."
    )
    st.session_state["auth_config_missing_warned"] = True


def ensure_streamlit_auth_secrets_from_env(auth_config):
    if not env_auth_config_present():
        return None

    secrets_path = Path(".streamlit") / "secrets.toml"

    if secrets_path.exists():
        return secrets_path

    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    secrets_path.write_text(
        render_streamlit_auth_secrets(auth_config),
        encoding="utf-8",
    )
    logger.info("Created runtime Streamlit auth secrets from environment.")

    return secrets_path


def env_auth_config_present():
    return all(
        os.getenv(name)
        for name in [
            "AUTH_COOKIE_SECRET",
            "AUTH_REDIRECT_URI",
            "GOOGLE_CLIENT_ID",
            "GOOGLE_CLIENT_SECRET",
        ]
    )


def render_streamlit_auth_secrets(auth_config):
    google_config = auth_config.get("google", {})

    return "\n".join([
        "[auth]",
        f"redirect_uri={toml_string(auth_config.get('redirect_uri', ''))}",
        f"cookie_secret={toml_string(auth_config.get('cookie_secret', ''))}",
        "",
        "[auth.google]",
        f"client_id={toml_string(google_config.get('client_id', ''))}",
        f"client_secret={toml_string(google_config.get('client_secret', ''))}",
        (
            "server_metadata_url="
            f"{toml_string(google_config.get('server_metadata_url', ''))}"
        ),
        "",
    ])


def toml_string(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


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
