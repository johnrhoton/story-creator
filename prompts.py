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


def build_story_chapter_prompt(
    overview,
    setting_background,
    tone_style,
    additional_instructions,
    language,
    language_level,
    outline,
    previous_summaries,
    chapter_number,
    chapter_description,
    story_memory_context=""
):
    previous_summary_text = (
        "\n\n".join(previous_summaries)
        if previous_summaries
        else "None yet."
    )

    return (
        "Write the full body for the current story chapter.\n\n"
        f"{build_story_instruction_section(additional_instructions, language, language_level)}"
        f"Template overview:\n{overview or ''}\n\n"
        f"Template setting/background:\n{setting_background or ''}\n\n"
        f"Template tone/style:\n{tone_style or ''}\n\n"
        f"Outline:\n{outline}\n\n"
        f"Previous chapter summaries:\n{previous_summary_text}\n\n"
        f"{build_story_memory_section(story_memory_context)}"
        f"USER REQUEST:\n{chapter_description or ''}\n\n"
        f"Current chapter: Chapter {chapter_number}\n"
        f"Current chapter description:\n{chapter_description or ''}\n\n"
        "Write only the chapter body. Follow the outline, maintain continuity "
        "with previous summaries, and match the requested tone/style. Use the "
        "story memory for continuity. Do not contradict it unless the user "
        "explicitly asks for a change."
    )


def build_story_chapter_zero_prompt(
    overview,
    setting_background,
    tone_style,
    additional_instructions,
    language,
    language_level,
    outline,
    characters,
    chapter_description,
    story_memory_context=""
):
    return (
        "Write Chapter 0 for this story.\n\n"
        f"{build_story_instruction_section(additional_instructions, language, language_level)}"
        f"Template overview:\n{overview or ''}\n\n"
        f"Template setting/background:\n{setting_background or ''}\n\n"
        f"Template tone/style:\n{tone_style or ''}\n\n"
        f"Outline:\n{outline}\n\n"
        f"Characters:\n{characters}\n\n"
        f"{build_story_memory_section(story_memory_context)}"
        f"USER REQUEST:\n{chapter_description or ''}\n\n"
        f"Chapter 0 purpose:\n{chapter_description or ''}\n\n"
        "Write only the chapter body. Establish the setting, introduce the "
        "main characters naturally, and prepare the reader for the story "
        "outlined above. Do not advance too far into the Chapter 1 events. "
        "Use the story memory for continuity. Do not contradict it unless the "
        "user explicitly asks for a change."
    )


def build_story_chapter_summary_prompt(chapter_body):
    return (
        "Summarise the following chapter body as concise continuity notes for "
        "future chapter generation.\n\n"
        "Include key events, character decisions, emotional changes, revealed "
        "information, unresolved tension, and the final state at the end of the "
        "chapter. Avoid polished prose.\n\n"
        f"Chapter body:\n{chapter_body}"
    )


def build_story_memory_section(story_memory_context):
    if not story_memory_context:
        return ""

    return (
        "STORY MEMORY:\n"
        f"{story_memory_context}\n\n"
    )


def build_story_instruction_section(
    additional_instructions,
    language,
    language_level
):
    instruction_lines = []

    if additional_instructions and additional_instructions.strip():
        instruction_lines.append(
            "Additional instructions: "
            f"{additional_instructions.strip()}"
        )

    if language and language.strip():
        instruction_lines.append(
            f"Target language: {language.strip()}"
        )

    if language_level and language_level.strip():
        instruction_lines.append(
            "Target language proficiency level: "
            f"{language_level.strip()} CEFR. Write the story at this "
            "proficiency level."
        )

    if not instruction_lines:
        return ""

    return (
        "HIGH PRIORITY STORY INSTRUCTIONS:\n"
        + "\n".join(instruction_lines)
        + "\n\n"
    )
