from config import GENDER_OPTIONS


def combine_profile_defaults(selected_profiles, profiles):
    defaults = {
        "name": "",
        "age": "",
        "gender": "female",
        "physical_traits": "",
        "personality_traits": "",
        "notes": "",
        "profile_name": None,
    }

    if not selected_profiles:
        return defaults

    selected_profile_rows = [
        profile for profile in profiles
        if profile[0] in selected_profiles
    ]

    if not selected_profile_rows:
        return defaults

    last_profile = selected_profile_rows[-1]

    defaults["name"] = last_profile[1] or ""
    defaults["age"] = last_profile[2] or ""
    defaults["gender"] = (
        last_profile[3]
        if last_profile[3] in GENDER_OPTIONS
        else "female"
    )

    defaults["physical_traits"] = ", ".join(
        profile[4] for profile in selected_profile_rows if profile[4]
    )

    defaults["personality_traits"] = ", ".join(
        profile[5] for profile in selected_profile_rows if profile[5]
    )

    defaults["notes"] = ", ".join(
        profile[6] for profile in selected_profile_rows if profile[6]
    )

    defaults["profile_name"] = ", ".join(selected_profiles)

    return defaults


def build_character_header(name, age, profile_name):
    header_parts = [
        name or "Unnamed character"
    ]

    if age:
        header_parts.append(age)

    if profile_name:
        header_parts.append(profile_name)

    return " — ".join(header_parts)

def append_profile_data_to_character(
    selected_profiles,
    profiles,
    current_physical_traits,
    current_personality_traits,
    current_notes
):
    selected_profile_rows = [
        profile for profile in profiles
        if profile[0] in selected_profiles
    ]

    profile_physical_traits = [
        profile[4] for profile in selected_profile_rows if profile[4]
    ]

    profile_personality_traits = [
        profile[5] for profile in selected_profile_rows if profile[5]
    ]

    profile_notes = [
        profile[6] for profile in selected_profile_rows if profile[6]
    ]

    combined_physical_traits = ", ".join(
        value for value in [current_physical_traits, *profile_physical_traits]
        if value
    )

    combined_personality_traits = ", ".join(
        value for value in [current_personality_traits, *profile_personality_traits]
        if value
    )

    combined_notes = ", ".join(
        value for value in [current_notes, *profile_notes]
        if value
    )

    profile_name = ", ".join(selected_profiles) if selected_profiles else None

    return (
        profile_name,
        combined_physical_traits,
        combined_personality_traits,
        combined_notes
    )