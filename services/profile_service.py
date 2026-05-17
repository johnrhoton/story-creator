from database import (
    add_profile,
    clone_profile,
    delete_profile,
    delete_profiles,
    get_profiles,
    get_profiles_for_export,
    log_object_history,
    rename_profile,
    update_profile,
)


def list_profiles():
    return get_profiles()


def list_profiles_for_export(profile_names, decrypt_values=True):
    return get_profiles_for_export(profile_names, decrypt_values=decrypt_values)


def create_profile(
    profile_name,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    profile_id = add_profile(
        profile_name,
        gender,
        physical_traits,
        personality_traits,
        notes
    )
    log_object_history(
        "Profiles",
        profile_id,
        profile_name,
        "Create",
        build_profile_history_contents(
            profile_name,
            gender,
            physical_traits,
            personality_traits,
            notes
        )
    )


def edit_profile(
    profile_name,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    update_profile(
        profile_name,
        gender,
        physical_traits,
        personality_traits,
        notes
    )
    profile = get_first_profile_for_history(profile_name)
    log_object_history(
        "Profiles",
        profile.get("id", profile_name),
        profile_name,
        "Update",
        build_profile_history_contents(
            profile_name,
            gender,
            physical_traits,
            personality_traits,
            notes
        )
    )


def rename_existing_profile(
    old_profile_name,
    new_profile_name
):
    rename_profile(
        old_profile_name,
        new_profile_name
    )
    profile = get_first_profile_for_history(new_profile_name)
    if profile:
        log_object_history(
            "Profiles",
            profile.get("id", new_profile_name),
            new_profile_name,
            "Update",
            profile
        )


def clone_existing_profile(profile_name):
    new_profile_name = clone_profile(profile_name)
    profile = get_first_profile_for_history(new_profile_name)
    if profile:
        log_object_history(
            "Profiles",
            profile.get("id", new_profile_name),
            new_profile_name,
            "Clone",
            profile
        )

    return new_profile_name


def delete_existing_profile(profile_name):
    profile = get_first_profile_for_history(profile_name)
    delete_profile(profile_name)
    if profile:
        log_object_history(
            "Profiles",
            profile.get("id", profile_name),
            profile_name,
            "Delete",
            profile
        )


def delete_existing_profiles(profile_names):
    profiles = {
        profile.get("profile_name"): profile
        for profile in get_profiles_for_export(profile_names)
    }
    deleted_count = delete_profiles(profile_names)

    for profile_name in profile_names:
        profile = profiles.get(profile_name.lower()) or profiles.get(profile_name)
        if profile:
            log_object_history(
                "Profiles",
                profile.get("id", profile_name),
                profile_name,
                "Delete",
                profile
            )

    return deleted_count


def build_profile_history_contents(
    profile_name,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    return {
        "profile_name": profile_name,
        "gender": gender,
        "physical_traits": physical_traits,
        "personality_traits": personality_traits,
        "notes": notes,
    }


def get_first_profile_for_history(profile_name):
    if not profile_name:
        return {}

    profiles = get_profiles_for_export([profile_name])
    return profiles[0] if profiles else {}
