from pathlib import Path


PROMPT_TEMPLATE_DIR = Path(__file__).with_name("prompts")


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

    return render_prompt_template(
        "character_description.txt",
        length=length,
        name_instruction=name_instruction,
        age=age,
        gender=gender,
        physical_traits=physical_traits,
        personality_traits=personality_traits,
        notes=notes,
    )


def build_character_summary_prompt(length, description):
    return render_prompt_template(
        "character_summary.txt",
        length=length,
        description=description,
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

    return render_prompt_template(
        "story_chapter.txt",
        story_instruction_section=build_story_instruction_section(
            additional_instructions,
            language,
            language_level
        ),
        overview=overview or "",
        setting_background=setting_background or "",
        tone_style=tone_style or "",
        outline=outline or "",
        previous_summary_text=previous_summary_text,
        story_memory_section=build_story_memory_section(story_memory_context),
        chapter_number=chapter_number,
        chapter_description=chapter_description or "",
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
    return render_prompt_template(
        "story_chapter_zero.txt",
        story_instruction_section=build_story_instruction_section(
            additional_instructions,
            language,
            language_level
        ),
        overview=overview or "",
        setting_background=setting_background or "",
        tone_style=tone_style or "",
        outline=outline or "",
        characters=characters or "",
        story_memory_section=build_story_memory_section(story_memory_context),
        chapter_description=chapter_description or "",
    )


def build_story_chapter_summary_prompt(
    chapter_body,
    language="",
    language_level=""
):
    return render_prompt_template(
        "story_chapter_summary.txt",
        story_instruction_section=build_story_instruction_section(
            "",
            language,
            language_level
        ),
        chapter_body=chapter_body,
    )


def build_story_beats_prompt(chapter_number, chapter_text):
    return render_prompt_template(
        "story_beats.txt",
        chapter_number=chapter_number,
        chapter_text=chapter_text or "",
    )


def build_glossary_prompt(
    source_text,
    dictionary_languages,
    entry_count=15,
    text_type="story section",
    source_language=""
):
    return render_prompt_template(
        "glossary.txt",
        entry_count=entry_count,
        source_language=source_language or "Use the language of the source text.",
        dictionary_languages=", ".join(dictionary_languages or []),
        text_type=text_type,
        source_text=source_text or "",
    )


def build_story_memory_section(story_memory_context):
    if not story_memory_context:
        return ""

    return (
        render_prompt_template_section(
            "story_memory_section.txt",
            "section",
            memory_sections=story_memory_context,
        )
        + "\n\n"
    )


def build_story_instruction_section(
    additional_instructions,
    language,
    language_level
):
    instruction_lines = []

    if additional_instructions and additional_instructions.strip():
        instruction_lines.append(
            render_prompt_template_section(
                "story_instruction_section.txt",
                "additional_instructions",
                additional_instructions=additional_instructions.strip(),
            ).strip()
        )

    if language and language.strip():
        instruction_lines.append(
            render_prompt_template_section(
                "story_instruction_section.txt",
                "language",
                language=language.strip(),
            ).strip()
        )

    if language_level and language_level.strip():
        instruction_lines.append(
            render_prompt_template_section(
                "story_instruction_section.txt",
                "language_level",
                language_level=language_level.strip(),
            ).strip()
        )

    if not instruction_lines:
        return ""

    return (
        render_prompt_template_section(
            "story_instruction_section.txt",
            "section",
            instruction_lines="\n".join(instruction_lines),
        )
        + "\n\n"
    )


def render_prompt_template(template_name, **values):
    template = load_prompt_template(template_name)
    return render_template_text(template, **values)


def render_prompt_template_section(template_name, section_name, **values):
    template = load_prompt_template_section(template_name, section_name)
    return render_template_text(template, **values)


def render_template_text(template, **values):
    safe_values = {
        key: "" if value is None else value
        for key, value in values.items()
    }

    return template.format(**safe_values)


def load_prompt_template(template_name):
    return (PROMPT_TEMPLATE_DIR / template_name).read_text(
        encoding="utf-8"
    )


def load_prompt_template_section(template_name, section_name):
    sections = parse_prompt_template_sections(
        load_prompt_template(template_name)
    )

    return sections[section_name]


def parse_prompt_template_sections(template):
    sections = {}
    current_section = None
    current_lines = []

    for line in template.splitlines():
        stripped = line.strip()

        if stripped.startswith("[") and stripped.endswith("]"):
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()

            current_section = stripped[1:-1]
            current_lines = []
            continue

        if current_section:
            current_lines.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()

    return sections
