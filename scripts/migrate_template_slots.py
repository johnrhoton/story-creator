#!/usr/bin/env python3
import getpass
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import create_tables, run_migrations
from database.db_encryption import (
    get_database_encryption_status,
    is_database_encryption_enabled,
    set_active_database_password,
)
from database.templates import (
    get_story_template_chapters,
    get_story_templates,
    update_story_template,
)
from services.template_service import parse_character_roles

PLACEHOLDER_PATTERN = re.compile(r"\b([MF])(\d+)\b")


def scan_placeholders(*texts):
    highest = {"M": 0, "F": 0}

    for text in texts:
        if not text:
            continue

        for match in PLACEHOLDER_PATTERN.finditer(text):
            gender = match.group(1)
            number = int(match.group(2))
            if number > highest[gender]:
                highest[gender] = number

    return highest["M"], highest["F"]


def build_slot_labels(prefix, count, existing_roles):
    existing_count = len(existing_roles)
    slots = list(existing_roles)

    for slot_index in range(existing_count + 1, count + 1):
        slots.append(f"{prefix}{slot_index}")

    return slots


def ensure_database_unlocked():
    if not is_database_encryption_enabled():
        return

    status = get_database_encryption_status()
    if status.get("unlocked"):
        return

    password = getpass.getpass("Database is encrypted. Enter password to unlock: ")
    set_active_database_password(password)
    status = get_database_encryption_status()
    if not status.get("unlocked"):
        raise ValueError("Unable to unlock encrypted database with the provided password.")


def migrate_template_slots():
    run_migrations()
    create_tables()
    ensure_database_unlocked()

    templates = get_story_templates()
    if not templates:
        print("No templates found.")
        return

    print(f"Scanning {len(templates)} template(s) for placeholders...")
    updated_templates = 0

    for template in templates:
        template_id = template[0]
        template_name = template[2]
        overview = template[3] or ""
        setting_background = template[4] or ""
        tone_style = template[5] or ""
        male_roles = parse_character_roles(template[6])
        female_roles = parse_character_roles(template[7])

        chapters = get_story_template_chapters(template_id)
        chapter_texts = [chapter[3] or "" for chapter in chapters]
        max_male, max_female = scan_placeholders(
            overview,
            setting_background,
            tone_style,
            *chapter_texts,
        )

        new_male_roles = build_slot_labels("M", max_male, male_roles)
        new_female_roles = build_slot_labels("F", max_female, female_roles)

        if new_male_roles != male_roles or new_female_roles != female_roles:
            update_story_template(
                template_id,
                template_name,
                overview,
                setting_background,
                tone_style,
                json.dumps(new_male_roles, ensure_ascii=False)
                if new_male_roles else None,
                json.dumps(new_female_roles, ensure_ascii=False)
                if new_female_roles else None,
            )
            updated_templates += 1
            print(
                f"Updated template #{template_id} '{template_name}': "
                f"male slots {len(male_roles)}->{len(new_male_roles)}, "
                f"female slots {len(female_roles)}->{len(new_female_roles)}"
            )

    if updated_templates == 0:
        print("All templates already had the correct slot counts.")
    else:
        print(f"Updated {updated_templates} template(s).")


if __name__ == "__main__":
    try:
        migrate_template_slots()
    except Exception as error:
        print(f"Migration failed: {error}")
        sys.exit(1)
