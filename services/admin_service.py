from database import (
    add_authorized_user,
    delete_authorized_user,
    get_authorized_users,
    update_authorized_user,
)


ROLE_OPTIONS = ["Administrator", "User"]


def list_authorized_users():
    return get_authorized_users()


def create_authorized_user(email, role):
    return add_authorized_user(email, role)


def edit_authorized_user(user_id, email, role):
    return update_authorized_user(user_id, email, role)


def delete_existing_authorized_user(user_id):
    return delete_authorized_user(user_id)
