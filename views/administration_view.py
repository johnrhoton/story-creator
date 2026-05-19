import logging

import streamlit as st

from services.admin_service import (
    ROLE_OPTIONS,
    create_authorized_user,
    delete_existing_authorized_user,
    edit_authorized_user,
    list_authorized_users,
)


logger = logging.getLogger(__name__)


def render_administration_tab():
    st.header("Administration")
    st.subheader("Authorized users")

    render_create_authorized_user_form()

    st.divider()

    users = list_authorized_users()

    if not users:
        st.info("No authorized users found.")
        return

    st.dataframe(
        [
            {
                "ID": user_id,
                "Email": email,
                "Role": role,
                "Google user ID": google_sub or "",
                "Last updated": updated_at,
            }
            for user_id, email, role, google_sub, updated_at in users
        ],
        use_container_width=True,
        hide_index=True,
    )

    for user in users:
        render_authorized_user_editor(user)


def render_create_authorized_user_form():
    with st.form("create_authorized_user_form"):
        email = st.text_input("Email")
        role = st.selectbox("Role", ROLE_OPTIONS)
        submitted = st.form_submit_button("Add user")

    if not submitted:
        return

    if not email.strip():
        st.error("Email is required.")
        return

    try:
        create_authorized_user(email, role)
        st.success("Authorized user added.")
        st.rerun()
    except Exception as error:
        logger.exception("Could not add authorized user.")
        st.error(f"Could not add authorized user: {error}")


def render_authorized_user_editor(user):
    user_id, email, role, google_sub, updated_at = user

    with st.expander(f"{email} - {role}"):
        st.write(f"**ID:** {user_id}")
        st.write(f"**Google user ID:** {google_sub or ''}")
        st.write(f"**Last updated:** {updated_at}")

        with st.form(f"edit_authorized_user_{user_id}"):
            edited_email = st.text_input(
                "Email",
                value=email,
                key=f"authorized_user_email_{user_id}"
            )
            edited_role = st.selectbox(
                "Role",
                ROLE_OPTIONS,
                index=find_role_index(role),
                key=f"authorized_user_role_{user_id}"
            )
            save = st.form_submit_button("Save user")

        if save:
            if not edited_email.strip():
                st.error("Email is required.")
            else:
                try:
                    edit_authorized_user(
                        user_id,
                        edited_email,
                        edited_role
                    )
                    st.success("Authorized user updated.")
                    st.rerun()
                except Exception as error:
                    logger.exception("Could not update authorized user.")
                    st.error(f"Could not update authorized user: {error}")

        if st.button(
            "Delete user",
            key=f"delete_authorized_user_{user_id}"
        ):
            try:
                delete_existing_authorized_user(user_id)
                st.success("Authorized user deleted.")
                st.rerun()
            except Exception as error:
                logger.exception("Could not delete authorized user.")
                st.error(f"Could not delete authorized user: {error}")


def find_role_index(role):
    if role in ROLE_OPTIONS:
        return ROLE_OPTIONS.index(role)

    return 0
