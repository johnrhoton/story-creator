import os
import sqlite3
from datetime import datetime

from dotenv import load_dotenv
from google import genai

DB_NAME = "character_generations_v2.db"

LAST_VALUES = {
    "length": "300",
    "name": "",
    "age": "",
    "gender": "",
    "adjectives": "",
    "verbs": ""
}


def check_exit(value):
    if value.strip().lower() == "exit":
        print("Goodbye.")
        raise SystemExit


def input_or_exit(prompt):
    value = input(prompt)
    check_exit(value)
    return value.strip()


def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS character_generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            name TEXT,
            age TEXT,
            gender TEXT,
            adjectives TEXT,
            verbs TEXT,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_name TEXT NOT NULL UNIQUE,
            name TEXT,
            age TEXT,
            gender TEXT,
            adjectives TEXT,
            verbs TEXT
        )
    """)

    conn.commit()
    conn.close()


def build_prompt(length, name, age, gender, adjectives, verbs):
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
        f"Static descriptive adjectives: {adjectives}\n"
        f"Dynamic action verbs: {verbs}\n\n"
        "Use the adjectives to shape the character's visible qualities, temperament, "
        "and atmosphere. Use the verbs to add a dynamic sense of how the character "
        "acts in the world. Do not merely list the traits. Turn them into a natural "
        "literary introduction. Avoid directly referencing any specific named persons "
        "other than the character themselves. Other people, if mentioned, should only "
        "be referred to anonymously or generically."
    )


def save_generation(name, age, gender, adjectives, verbs, prompt, response):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO character_generations
        (created_at, name, age, gender, adjectives, verbs, prompt, response)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().isoformat(timespec="seconds"),
        name,
        age,
        gender,
        adjectives,
        verbs,
        prompt,
        response
    ))

    record_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return record_id


def add_profile():
    print("\n--- Add Profile ---")

    profile_name = input_or_exit("Profile name:\n> ").lower()
    name = input_or_exit("Default character name, optional:\n> ")
    age = input_or_exit("Default age:\n> ")
    gender = input_or_exit("Default gender:\n> ")
    adjectives = input_or_exit("Default adjectives, separated by commas:\n> ")
    verbs = input_or_exit("Default verbs, separated by commas:\n> ")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO profiles
            (profile_name, name, age, gender, adjectives, verbs)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            profile_name,
            name,
            age,
            gender,
            adjectives,
            verbs
        ))

        conn.commit()
        print(f"\nProfile '{profile_name}' saved.")

    except sqlite3.IntegrityError:
        print(f"\nA profile named '{profile_name}' already exists.")

    finally:
        conn.close()


def list_profiles():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, profile_name, name, age, gender, adjectives, verbs
        FROM profiles
        ORDER BY profile_name
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("\nNo profiles saved yet.")
        return

    print("\n--- Profiles ---")

    for row in rows:
        profile_id, profile_name, name, age, gender, adjectives, verbs = row

        print(f"\nID: {profile_id}")
        print(f"Profile: {profile_name}")
        print(f"Name: {name or '(not provided)'}")
        print(f"Age: {age}")
        print(f"Gender: {gender}")
        print(f"Adjectives: {adjectives}")
        print(f"Verbs: {verbs}")
        print("-" * 60)


def get_profile_by_name(profile_name):
    profile_name = profile_name.lower()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, age, gender, adjectives, verbs
        FROM profiles
        WHERE profile_name = ?
    """, (profile_name,))

    row = cursor.fetchone()
    conn.close()

    return row


def choose_profile_defaults():
    profile_name = input_or_exit(
        "\nProfile name, optional. Press Enter for current defaults:\n> "
    ).lower()

    if not profile_name:
        return

    profile = get_profile_by_name(profile_name)

    if not profile:
        print(f"No profile named '{profile_name}' found. Using current defaults.")
        return

    name, age, gender, adjectives, verbs = profile

    LAST_VALUES["name"] = name or ""
    LAST_VALUES["age"] = age or ""
    LAST_VALUES["gender"] = gender or ""
    LAST_VALUES["adjectives"] = adjectives or ""
    LAST_VALUES["verbs"] = verbs or ""

    print(f"Loaded profile '{profile_name}'.")


def prompt_with_default(label, key):
    current = LAST_VALUES[key]

    if current:
        value = input_or_exit(f"{label} [{current}]:\n> ")
        if not value:
            value = current
    else:
        value = input_or_exit(f"{label}:\n> ")

    LAST_VALUES[key] = value
    return value


def generate_character(api_key):
    choose_profile_defaults()

    length = prompt_with_default("Description length in words", "length")
    name = prompt_with_default("Name, optional", "name")
    age = prompt_with_default("Age", "age")
    gender = prompt_with_default("Gender", "gender")
    adjectives = prompt_with_default("Adjectives, separated by commas", "adjectives")
    verbs = prompt_with_default("Verbs, separated by commas", "verbs")

    prompt = build_prompt(
        length,
        name,
        age,
        gender,
        adjectives,
        verbs
    )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    generated_text = response.text

    record_id = save_generation(
        name=name,
        age=age,
        gender=gender,
        adjectives=adjectives,
        verbs=verbs,
        prompt=prompt,
        response=generated_text
    )

    print("\n--- Generated Character Introduction ---\n")
    print(generated_text)

    print("\nSaved to SQLite.")
    print(f"Record ID: {record_id}")


def list_all_generations():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, created_at, name, age, gender, adjectives, verbs, response
        FROM character_generations
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("\nNo saved generations yet.")
        return

    print("\n--- All Saved Character Generations ---")

    for row in rows:
        record_id, created_at, name, age, gender, adjectives, verbs, response = row

        print(f"\nID: {record_id}")
        print(f"Created: {created_at}")
        print(f"Name: {name or '(not provided)'}")
        print(f"Age: {age}")
        print(f"Gender: {gender}")
        print(f"Adjectives: {adjectives}")
        print(f"Verbs: {verbs}")
        print(f"Response:\n{response}")
        print("-" * 60)


def show_single_generation():
    record_id_text = input_or_exit("\nEnter record ID:\n> ")

    try:
        record_id = int(record_id_text)
    except ValueError:
        print("Invalid ID.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, created_at, name, age, gender, adjectives, verbs, prompt, response
        FROM character_generations
        WHERE id = ?
    """, (record_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        print("Record not found.")
        return

    print("\n--- Character Generation ---")
    print(f"\nID: {row[0]}")
    print(f"Created: {row[1]}")
    print(f"Name: {row[2] or '(not provided)'}")
    print(f"Age: {row[3]}")
    print(f"Gender: {row[4]}")
    print(f"Adjectives: {row[5]}")
    print(f"Verbs: {row[6]}")
    print(f"\nPrompt:\n{row[7]}")
    print(f"\nResponse:\n{row[8]}")


def main():
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY not found. Check your .env file.")

    create_tables()

    while True:
        print("\n==============================")
        print("Character Generator")
        print("==============================")
        print("1 - Generate new character")
        print("2 - List all generations")
        print("3 - View generation by ID")
        print("4 - Add profile")
        print("5 - List profiles")
        print("6 - Exit")

        choice = input_or_exit("\nChoose an option:\n> ")

        if choice == "1":
            generate_character(api_key)
        elif choice == "2":
            list_all_generations()
        elif choice == "3":
            show_single_generation()
        elif choice == "4":
            add_profile()
        elif choice == "5":
            list_profiles()
        elif choice == "6":
            print("Goodbye.")
            break
        else:
            print("Invalid option.")


if __name__ == "__main__":
    main()