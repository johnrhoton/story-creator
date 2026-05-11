def build_prompt(
    length,
    name,
    age,
    gender,
    physical_traits,
    personality_traits,
    notes
):
    name_instruction = (
        f"The character's name is {name}."
        if name
        else "If no name is provided, invent a fitting name."
    )

    return (
        f"Write a vivid approximately {length}-word character introduction "
        "suitable for fiction.\n\n"
        f"{name_instruction}\n"
        f"Age: {age}\n"
        f"Gender: {gender}\n"
        f"Physical traits: {physical_traits}\n"
        f"Personality traits: {personality_traits}\n"
        f"Additional notes: {notes}\n\n"
        "Use the physical traits to shape the character's visible appearance, "
        "presence, body language, and atmosphere. Use the personality traits to "
        "shape temperament, habits, emotional tone, and inner tendencies. Use the "
        "notes to incorporate additional context, actions, history, motivations, "
        "or other relevant details naturally into the introduction. Do not merely "
        "list the information. Turn it into a natural literary character "
        "introduction. Avoid directly referencing any specific named persons other "
        "than the character themselves. Other people, if mentioned, should only be "
        "referred to anonymously or generically."
    )


def build_character_summary_prompt(length, description):
    return (
        f"Summarise the following character description in approximately "
        f"{length} words.\n\n"
        "Use succinct factual notes, not polished prose. Include only key facts "
        "useful as context for future LLM prompts: identity, age, gender, "
        "appearance, personality, motivations, behaviour, background, and notable "
        "details. Avoid decorative language.\n\n"
        f"Character description:\n{description}"
    )