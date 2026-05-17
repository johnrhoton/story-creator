import streamlit as st

from database import (
    character_name_exists,
    clone_character,
    delete_character,
    delete_characters,
    get_characters,
    get_characters_for_export,
    get_profiles,
    save_character,
    suggest_character_name,
    update_character,
    log_object_history,
)
from llm_client import generate_text
from prompts import build_character_summary_prompt, build_prompt
from services.rag_indexing_service import (
    delete_character_memory,
    index_character,
)


def list_characters():
    return get_characters()


def list_characters_for_export(record_ids, decrypt_values=True):
    return get_characters_for_export(record_ids, decrypt_values=decrypt_values)


def list_profiles_for_character_creation():
    return get_profiles()


def name_exists(name):
    return character_name_exists(name)


def suggest_name(age, gender):
    return suggest_character_name(age, gender)


def call_selected_llm(prompt):
    return generate_text(
        st.session_state["llm_provider"],
        st.session_state["llm_model"],
        prompt
    )


def generate_character_description(
    length,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    prompt = build_prompt(
        length,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes
    )

    response = call_selected_llm(prompt)

    return prompt, response


def generate_character_summary(description, length=50):
    prompt = build_character_summary_prompt(
        length,
        description
    )

    return call_selected_llm(prompt)


def create_character(
    profile_name,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes,
    prompt,
    response,
    summary
):
    contents = build_character_history_contents(
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        response,
        summary
    )
    character_id = save_character(
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        prompt,
        response,
        summary
    )
    index_character({
        "id": character_id,
        "profile_name": profile_name,
        "name": name,
        "age": age,
        "gender": gender,
        "physical_traits": physical_traits,
        "personality_traits": personality_traits,
        "notes": notes,
        "response": response,
        "summary": summary,
    })
    log_object_history(
        "Characters",
        character_id,
        name,
        "Create",
        contents
    )

    return character_id


def edit_character(
    record_id,
    profile_name,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes,
    response,
    summary
):
    contents = build_character_history_contents(
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        response,
        summary
    )
    update_character(
        record_id,
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        response,
        summary
    )
    index_character({
        "id": record_id,
        "profile_name": profile_name,
        "name": name,
        "age": age,
        "gender": gender,
        "physical_traits": physical_traits,
        "personality_traits": personality_traits,
        "notes": notes,
        "response": response,
        "summary": summary,
    })
    log_object_history(
        "Characters",
        record_id,
        name,
        "Update",
        contents
    )


def clone_existing_character(record_id):
    new_id = clone_character(record_id)

    if new_id:
        matching_characters = [
            character
            for character in get_characters()
            if character[0] == new_id
        ]
        if matching_characters:
            index_character(matching_characters[0])
            log_character_history_from_row(
                matching_characters[0],
                "Clone"
            )

    return new_id


def delete_existing_character(record_id):
    matching_characters = [
        character
        for character in get_characters()
        if character[0] == record_id
    ]
    delete_character(record_id)
    delete_character_memory(record_id)
    if matching_characters:
        log_character_history_from_row(
            matching_characters[0],
            "Delete"
        )


def delete_existing_characters(record_ids):
    matching_characters = [
        character
        for character in get_characters()
        if character[0] in record_ids
    ]
    deleted_count = delete_characters(record_ids)

    for record_id in record_ids:
        delete_character_memory(record_id)

    for character in matching_characters:
        log_character_history_from_row(character, "Delete")

    return deleted_count


def build_character_history_contents(
    profile_name,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes,
    response,
    summary
):
    return {
        "profile_name": profile_name,
        "name": name,
        "age": age,
        "gender": gender,
        "physical_traits": physical_traits,
        "personality_traits": personality_traits,
        "notes": notes,
        "summary": summary,
        "description": response,
    }


def log_character_history_from_row(row, operation):
    (
        record_id,
        _created_at,
        profile_name,
        name,
        age,
        gender,
        physical_traits,
        personality_traits,
        notes,
        response,
        summary
    ) = row

    log_object_history(
        "Characters",
        record_id,
        name or "Unnamed character",
        operation,
        build_character_history_contents(
            profile_name,
            name,
            age,
            gender,
            physical_traits,
            personality_traits,
            notes,
            response,
            summary
        )
    )
