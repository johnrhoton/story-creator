import math

from database.connection import get_connection


FEMALE_NAMES = [
    "Abigail", "Ada", "Alice", "Amelia", "Anna", "Arabella", "Aria",
    "Aurora", "Ava", "Ayla", "Beatrice", "Bella", "Bonnie", "Charlotte",
    "Chloe", "Clara", "Daisy", "Delilah", "Eden", "Eleanor", "Eliza",
    "Elizabeth", "Ella", "Elle", "Elodie", "Eloise", "Elsie", "Emilia",
    "Emily", "Emma", "Erin", "Eva", "Evelyn", "Evie", "Florence",
    "Freya", "Georgia", "Grace", "Hallie", "Harper", "Harriet", "Hazel",
    "Heidi", "Holly", "Iris", "Isabelle", "Isla", "Ivy", "Jasmine",
    "Julia", "Layla", "Lily", "Lucy", "Luna", "Lyla", "Lyra", "Mabel",
    "Maeve", "Maisie", "Margot", "Maryam", "Matilda", "Maya", "Mia",
    "Mila", "Millie", "Nancy", "Nina", "Nova", "Olive", "Olivia",
    "Ophelia", "Orla", "Ottilie", "Penelope", "Phoebe", "Robyn", "Rose",
    "Rosie", "Ruby", "Scarlett", "Sienna", "Sophia", "Sophie", "Stella",
    "Thea", "Violet", "Zara", "Zoe"
]


MALE_NAMES = [
    "Adam", "Aiden", "Albert", "Alexander", "Alfie", "Andrew", "Anthony",
    "Archie", "Arlo", "Arthur", "Austin", "Axel", "Beau", "Benjamin",
    "Blake", "Bobby", "Caleb", "Carter", "Charlie", "Christopher",
    "Connor", "Daniel", "David", "Dexter", "Dominic", "Dylan", "Edward",
    "Elias", "Elliot", "Enzo", "Ethan", "Ezra", "Felix", "Finn",
    "Freddie", "Gabriel", "George", "Harry", "Harvey", "Henry", "Hudson",
    "Hugo", "Hunter", "Isaac", "Jack", "Jacob", "James", "Jasper",
    "Joel", "Joseph", "Joshua", "Jude", "Kai", "Leo", "Leon", "Liam",
    "Logan", "Louie", "Lucas", "Mason", "Matthew", "Max", "Michael",
    "Milo", "Musa", "Nathan", "Noah", "Oliver", "Ollie", "Oscar",
    "Otis", "Reggie", "Reuben", "Roman", "Ronnie", "Rory", "Ryan",
    "Samuel", "Sebastian", "Sonny", "Teddy", "Theo", "Thomas", "Toby",
    "Tommy", "Tyler", "Vinnie", "William"
]


def seed_common_names():
    conn = get_connection()
    cursor = conn.cursor()

    seed_names_for_gender(cursor, "female", FEMALE_NAMES)
    seed_names_for_gender(cursor, "male", MALE_NAMES)

    conn.commit()
    conn.close()


def seed_names_for_gender(cursor, gender, names):
    for index, name in enumerate(names, start=1):
        cursor.execute("""
            INSERT OR IGNORE INTO common_names
            (
                sequence_number,
                gender,
                name
            )
            VALUES (?, ?, ?)
        """, (
            index,
            gender,
            name
        ))


def get_common_names(gender):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            sequence_number,
            name
        FROM common_names
        WHERE gender = ?
        ORDER BY sequence_number
    """, (
        gender,
    ))

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_existing_character_names():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM characters
        WHERE name IS NOT NULL
          AND TRIM(name) != ''
    """)

    names = {
        row[0].strip().lower()
        for row in cursor.fetchall()
        if row[0]
    }

    conn.close()

    return names


def character_name_exists(name):
    if not name:
        return False

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 1
        FROM characters
        WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
        LIMIT 1
    """, (
        name,
    ))

    exists = cursor.fetchone() is not None

    conn.close()

    return exists


def suggest_character_name(age, gender):
    names = get_common_names(gender)

    if not names:
        return ""

    target_index = age_to_name_index(
        age,
        len(names)
    )

    existing_names = get_existing_character_names()

    free_name = find_nearest_free_name(
        names,
        target_index,
        existing_names
    )

    return free_name or ""


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


def find_nearest_free_name(names, target_index, existing_names):
    total_names = len(names)

    offsets = [0]

    for distance in range(1, total_names):
        offsets.append(distance)
        offsets.append(-distance)

    for offset in offsets:
        candidate_index = target_index + offset

        if candidate_index < 0 or candidate_index >= total_names:
            continue

        sequence_number, name = names[candidate_index]

        if name.lower() not in existing_names:
            return name

    return None