from database import (
    add_profile,
    clone_profile,
    delete_profile,
    get_profiles,
    rename_profile,
    update_profile,
)


def list_profiles():
    return get_profiles()


def create_profile(
    profile_name,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    add_profile(
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes
    )


def edit_profile(
    profile_name,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    update_profile(
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes
    )


def rename_existing_profile(
    old_profile_name,
    new_profile_name
):
    rename_profile(
        old_profile_name,
        new_profile_name
    )


def clone_existing_profile(profile_name):
    return clone_profile(profile_name)


def delete_existing_profile(profile_name):
    delete_profile(profile_name)