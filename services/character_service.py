import streamlit as st

from database import (
    character_name_exists,
    clone_character,
    delete_character,
    get_characters,
    get_profiles,
    save_character,
    suggest_character_name,
    update_character,
)
from llm_client import generate_text
from prompts import build_character_summary_prompt, build_prompt


def list_characters():
    return get_characters()


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
    save_character(
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


def clone_existing_character(record_id):
    return clone_character(record_id)


def delete_existing_character(record_id):
    delete_character(record_id)