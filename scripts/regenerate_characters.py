import argparse
import math
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google import genai

from config import get_config_value
from database.common_names import seed_common_names, get_common_names
from database.connection import get_database_path
from prompts import build_prompt, build_character_summary_prompt


DEFAULT_MODEL = "gemini-2.5-flash"


def backup_database():
    db_path = get_database_path()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = db_path.with_name(f"{db_path.stem}_backup_{timestamp}{db_path.suffix}")

    shutil.copy2(db_path, backup_path)
    print(f"Backup created: {backup_path}")


def get_client():
    api_key = get_config_value("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not found in Streamlit secrets")

    return genai.Client(api_key=api_key)


def call_gemini(client, model, prompt):
    response = client.models.generate_content(
        model=model,
        contents=prompt
    )

    return response.text or ""


def age_to_name_index(age, name_count):
    if name_count <= 1:
        return 0

    try:
        age_number = float(age)
    except (TypeError, ValueError):
        age_number = 18.0

    age_number = max(5.0, min(60.0, age_number))

    normalised = math.log(age_number / 5.0) / math.log(60.0 / 5.0)

    return round(normalised * (name_count - 1))


def find_available_name(age, gender, used_names):
    names = get_common_names(gender)

    if not names:
        return None

    target_index = age_to_name_index(age, len(names))

    offsets = [0]

    for distance in range(1, len(names)):
        offsets.append(distance)
        offsets.append(-distance)

    for offset in offsets:
        candidate_index = target_index + offset

        if candidate_index < 0 or candidate_index >= len(names):
            continue

        sequence_number, name = names[candidate_index]

        if name.lower() not in used_names:
            used_names.add(name.lower())
            return name

    return None


def get_characters():
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            profile_name,
            name,
            age,
            gender,
            physical_traits,
            personality_traits,
            notes
        FROM characters
        ORDER BY id
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def update_character(record_id, new_name, prompt, response, summary):
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE characters
        SET
            name = ?,
            prompt = ?,
            response = ?,
            summary = ?
        WHERE id = ?
    """, (
        new_name,
        prompt,
        response,
        summary,
        record_id
    ))

    conn.commit()
    conn.close()


def regenerate_characters(model, description_length, summary_length, dry_run):
    seed_common_names()

    characters = get_characters()

    if not characters:
        print("No characters found.")
        return

    used_names = set()
    client = None if dry_run else get_client()

    for character in characters:
        (
            record_id,
            profile_name,
            old_name,
            age,
            gender,
            physical_traits,
            personality_traits,
            notes
        ) = character

        gender = gender if gender in ["female", "male"] else "female"

        new_name = find_available_name(
            age,
            gender,
            used_names
        )

        if not new_name:
            print(f"[SKIP] Character {record_id}: no available name found.")
            continue

        print(f"[{record_id}] {old_name} -> {new_name} ({gender}, age {age})")

        prompt = build_prompt(
            description_length,
            new_name,
            age,
            gender,
            physical_traits,
            personality_traits,
            notes
        )

        if dry_run:
            continue

        description = call_gemini(
            client,
            model,
            prompt
        )

        summary_prompt = build_character_summary_prompt(
            summary_length,
            description
        )

        summary = call_gemini(
            client,
            model,
            summary_prompt
        )

        update_character(
            record_id,
            new_name,
            prompt,
            description,
            summary
        )

        print(f"    Updated description and summary.")


def main():
    parser = argparse.ArgumentParser(
        description="One-time character rename and regeneration script."
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Gemini model to use."
    )

    parser.add_argument(
        "--description-length",
        type=int,
        default=300,
        help="Target description length in words."
    )

    parser.add_argument(
        "--summary-length",
        type=int,
        default=50,
        help="Target summary length in words."
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned changes without updating database or calling Gemini."
    )

    args = parser.parse_args()

    db_path = get_database_path()

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    if not args.dry_run:
        backup_database()

    regenerate_characters(
        model=args.model,
        description_length=args.description_length,
        summary_length=args.summary_length,
        dry_run=args.dry_run
    )

    print("Done.")


if __name__ == "__main__":
    main()
