import copy
import json
import re
from datetime import datetime, timezone

import yaml

from database.authorized_users import (
    ADMINISTRATOR_ROLE,
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_ADMIN_ROLE,
)
from database.common_names import FEMALE_NAMES, MALE_NAMES
from database.export_crypto import decrypt_export_values, encrypt_export_values
from database.mongodb_connection import get_collection, get_mongo_database, get_next_id
from services.observability_service import (
    EVENT_DATABASE_SAVE_COMPLETED,
    EVENT_DATABASE_SAVE_FAILED,
    timed_operation,
)


TABLE_COLLECTIONS = {
    "authorized_users": "authorized_users",
    "characters": "characters",
    "profiles": "profiles",
    "story_templates": "story_templates",
    "story_template_chapters": "story_template_chapters",
    "stories": "stories",
    "story_chapters": "story_chapters",
    "story_beats": "story_beats",
    "llm_calls": "llm_calls",
    "failed_llm_calls": "failed_llm_calls",
    "llm_models": "llm_models",
    "object_history": "object_history",
    "app_events": "app_events",
    "sync_metadata": "sync_metadata",
}

DATABASE_ENCRYPTION_EXPORT_KEY = "__database_encryption"


def now():
    return datetime.now().isoformat(timespec="seconds")


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_tables():
    ensure_mongo_indexes()
    seed_default_authorized_user()
    seed_common_names()


def run_migrations():
    create_tables()


def ensure_mongo_indexes():
    get_collection("authorized_users").create_index("email", unique=True)
    get_collection("authorized_users").create_index("google_sub", unique=True, sparse=True)
    get_collection("profiles").create_index("profile_name", unique=True)
    get_collection("story_templates").create_index("template_name", unique=True)
    get_collection("stories").create_index("story_name", unique=True)
    get_collection("llm_models").create_index([("provider", 1), ("model", 1)], unique=True)
    get_collection("common_names").create_index([("gender", 1), ("name", 1)], unique=True)
    get_collection("app_events").create_index([("timestamp", -1), ("id", -1)])


def reinitialize_database():
    db = get_mongo_database()
    for name in TABLE_COLLECTIONS.values():
        db[name].delete_many({})
    db["common_names"].delete_many({})
    db["counters"].delete_many({})
    create_tables()
    from database.load_seed import seed_database_from_load_folder

    seed_database_from_load_folder()


def mark_local_data_modified(_cursor=None, timestamp=None):
    set_metadata_value("local_data_modified_at", timestamp or utc_now())


def set_metadata_value(key, value):
    get_collection("sync_metadata").update_one(
        {"_id": key},
        {"$set": {"key": key, "value": value}},
        upsert=True,
    )


def get_metadata_value(key):
    doc = get_collection("sync_metadata").find_one({"_id": key})
    return doc.get("value") if doc else None


def get_sync_metadata():
    return {
        "local_data_modified_at": get_metadata_value("local_data_modified_at"),
        "last_synced_at": get_metadata_value("last_synced_at"),
        "last_synced_content_hash": get_metadata_value("last_synced_content_hash"),
    }


def set_sync_metadata(last_synced_at, content_hash, data_modified_at=None):
    set_metadata_value("last_synced_at", last_synced_at)
    set_metadata_value("last_synced_content_hash", content_hash)
    if data_modified_at:
        set_metadata_value("local_data_modified_at", data_modified_at)


def seed_default_authorized_user(_cursor=None):
    existing = get_collection("authorized_users").find_one({
        "email": DEFAULT_ADMIN_EMAIL,
    })

    if existing:
        if existing.get("id") is None:
            get_collection("authorized_users").update_one(
                {"_id": existing["_id"]},
                {"$set": {"id": existing["_id"]}},
            )
        return

    timestamp = utc_now()
    user_id = get_next_id("authorized_users")
    get_collection("authorized_users").insert_one({
        "_id": user_id,
        "id": user_id,
        "email": DEFAULT_ADMIN_EMAIL,
        "role": DEFAULT_ADMIN_ROLE,
        "google_sub": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    })


def get_authorized_users():
    return [
        tuple_from_doc(doc, ["id", "email", "role", "google_sub", "updated_at"])
        for doc in get_collection("authorized_users").find().sort("email", 1)
    ]


def get_authorized_user_by_identity(google_sub=None, email=None):
    doc = None
    if google_sub:
        doc = get_collection("authorized_users").find_one({"google_sub": google_sub})
    if doc is None and email:
        doc = get_collection("authorized_users").find_one({"email": normalize_email(email)})
    return tuple_from_doc(doc, ["id", "email", "role", "google_sub", "updated_at"]) if doc else None


def bind_authorized_user_google_sub(user_id, google_sub):
    result = get_collection("authorized_users").update_one(
        {"id": user_id, "$or": [{"google_sub": None}, {"google_sub": ""}]},
        {"$set": {"google_sub": google_sub, "updated_at": utc_now()}},
    )
    if result.modified_count:
        mark_local_data_modified()
    return result.modified_count > 0


def add_authorized_user(email, role):
    user_id = get_next_id("authorized_users")
    timestamp = utc_now()
    get_collection("authorized_users").insert_one({
        "_id": user_id,
        "id": user_id,
        "email": normalize_email(email),
        "role": normalize_role(role),
        "google_sub": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    })
    mark_local_data_modified()
    return user_id


def update_authorized_user(user_id, email, role):
    result = get_collection("authorized_users").update_one(
        {"id": user_id},
        {"$set": {"email": normalize_email(email), "role": normalize_role(role), "updated_at": utc_now()}},
    )
    if result.modified_count:
        mark_local_data_modified()
    return result.matched_count > 0


def delete_authorized_user(user_id):
    result = get_collection("authorized_users").delete_one({"id": user_id})
    if result.deleted_count:
        mark_local_data_modified()
    return result.deleted_count > 0


def normalize_email(email):
    return str(email or "").strip().lower()


def normalize_role(role):
    return str(role or "").strip() or "User"


def seed_common_names():
    for gender, names in (("female", FEMALE_NAMES), ("male", MALE_NAMES)):
        for sequence_number, name in enumerate(names, start=1):
            get_collection("common_names").update_one(
                {"gender": gender, "name": name},
                {"$setOnInsert": {"gender": gender, "name": name, "sequence_number": sequence_number}},
                upsert=True,
            )


def get_common_names(gender):
    return [
        (doc.get("sequence_number"), doc.get("name"))
        for doc in get_collection("common_names").find({"gender": gender}).sort("sequence_number", 1)
    ]


def character_name_exists(name):
    if not name:
        return False
    return get_collection("characters").find_one({"name_lower": str(name).strip().lower()}) is not None


def suggest_character_name(age, gender):
    from database.common_names import age_to_name_index, find_nearest_free_name

    names = get_common_names(gender)
    if not names:
        return ""
    target_index = age_to_name_index(age, len(names))
    existing_names = {
        doc.get("name_lower")
        for doc in get_collection("characters").find({}, {"name_lower": 1})
        if doc.get("name_lower")
    }
    return find_nearest_free_name(names, target_index, existing_names) or ""


def save_character(profile_name, name, age, gender, physical_traits, personality_traits, notes, prompt, response, summary):
    character_id = get_next_id("characters")
    get_collection("characters").insert_one({
        "_id": character_id,
        "id": character_id,
        "created_at": now(),
        "profile_name": profile_name.lower() if profile_name else None,
        "name": name,
        "name_lower": str(name or "").strip().lower(),
        "age": age,
        "gender": gender,
        "physical_traits": physical_traits,
        "personality_traits": personality_traits,
        "notes": notes,
        "prompt": prompt,
        "response": response,
        "summary": summary,
    })
    mark_local_data_modified()
    return character_id


def update_character(record_id, profile_name, name, age, gender, physical_traits, personality_traits, notes, response, summary):
    result = get_collection("characters").update_one(
        {"id": record_id},
        {"$set": {
            "profile_name": profile_name.lower() if profile_name else None,
            "name": name,
            "name_lower": str(name or "").strip().lower(),
            "age": age,
            "gender": gender,
            "physical_traits": physical_traits,
            "personality_traits": personality_traits,
            "notes": notes,
            "response": response,
            "summary": summary,
        }},
    )
    if result.modified_count:
        mark_local_data_modified()


def clone_character(record_id):
    doc = get_collection("characters").find_one({"id": record_id})
    if not doc:
        return None
    data = copy_doc(doc)
    new_id = get_next_id("characters")
    data.update({"_id": new_id, "id": new_id, "created_at": now()})
    get_collection("characters").insert_one(data)
    mark_local_data_modified()
    return new_id


def delete_character(record_id):
    if get_collection("characters").delete_one({"id": record_id}).deleted_count:
        mark_local_data_modified()


def delete_characters(record_ids):
    result = get_collection("characters").delete_many({"id": {"$in": list(record_ids or [])}})
    if result.deleted_count:
        mark_local_data_modified()
    return result.deleted_count


def get_characters():
    return [
        tuple_from_doc(doc, ["id", "created_at", "profile_name", "name", "age", "gender", "physical_traits", "personality_traits", "notes", "response", "summary"])
        for doc in get_collection("characters").find().sort("id", -1)
    ]


def get_characters_for_export(record_ids, decrypt_values=True):
    return [
        dict_from_doc(doc, ["id", "created_at", "profile_name", "name", "age", "gender", "physical_traits", "personality_traits", "notes", "prompt", "response", "summary"])
        for doc in get_collection("characters").find({"id": {"$in": list(record_ids or [])}}).sort("id", 1)
    ]


def get_characters_by_gender(gender):
    return [
        tuple_from_doc(doc, ["id", "name", "age", "gender", "summary", "profile_name"])
        for doc in get_collection("characters").find({"gender": gender}).sort("name", 1)
    ]


def get_character_summaries_by_names(names):
    lookup = {
        str(name).strip().lower()
        for name in names or []
    }
    return {
        doc.get("name_lower"): doc.get("summary") or ""
        for doc in get_collection("characters").find({"name_lower": {"$in": list(lookup)}})
        if doc.get("name_lower")
    }


def add_profile(profile_name, gender, physical_traits, personality_traits, notes):
    normalized_name = str(profile_name or "").strip().lower()
    delete_profiles([normalized_name])
    profile_id = get_next_id("profiles")
    get_collection("profiles").insert_one({
        "_id": profile_id,
        "id": profile_id,
        "profile_name": normalized_name,
        "gender": gender,
        "physical_traits": physical_traits,
        "personality_traits": personality_traits,
        "notes": notes,
    })
    mark_local_data_modified()
    return profile_id


def update_profile(profile_name, gender, physical_traits, personality_traits, notes):
    result = get_collection("profiles").update_one(
        {"profile_name": str(profile_name or "").strip().lower()},
        {"$set": {"gender": gender, "physical_traits": physical_traits, "personality_traits": personality_traits, "notes": notes}},
    )
    if result.modified_count:
        mark_local_data_modified()


def rename_profile(old_profile_name, new_profile_name):
    old_name = str(old_profile_name or "").strip().lower()
    new_name = str(new_profile_name or "").strip().lower()
    profile_result = get_collection("profiles").update_one({"profile_name": old_name}, {"$set": {"profile_name": new_name}})
    character_result = get_collection("characters").update_many({"profile_name": old_name}, {"$set": {"profile_name": new_name}})
    if profile_result.modified_count or character_result.modified_count:
        mark_local_data_modified()


def clone_profile(profile_name):
    normalized_name = str(profile_name or "").strip().lower()
    doc = get_collection("profiles").find_one({"profile_name": normalized_name})
    if not doc:
        return None
    base_name = f"{normalized_name}_copy"
    new_name = build_unique_name("profiles", "profile_name", base_name)
    add_profile(new_name, doc.get("gender"), doc.get("physical_traits"), doc.get("personality_traits"), doc.get("notes"))
    return new_name


def delete_profile(profile_name):
    return delete_profiles([profile_name])


def delete_profiles(profile_names):
    names = [str(name or "").strip().lower() for name in profile_names or []]
    result = get_collection("profiles").delete_many({"profile_name": {"$in": names}})
    if result.deleted_count:
        mark_local_data_modified()
    return result.deleted_count


def get_profiles():
    return [
        tuple_from_doc(doc, ["profile_name", "gender", "physical_traits", "personality_traits", "notes"])
        for doc in get_collection("profiles").find().sort([("gender", 1), ("profile_name", 1)])
    ]


def get_profiles_for_export(profile_names, decrypt_values=True):
    names = [str(name or "").strip().lower() for name in profile_names or []]
    return [
        dict_from_doc(doc, ["id", "profile_name", "gender", "physical_traits", "personality_traits", "notes"])
        for doc in get_collection("profiles").find({"profile_name": {"$in": names}}).sort("profile_name", 1)
    ]


def add_story_template(template_name, overview, setting_background, tone_style, male_character_roles=None, female_character_roles=None):
    template_id = get_next_id("story_templates")
    get_collection("story_templates").insert_one({
        "_id": template_id,
        "id": template_id,
        "created_at": now(),
        "template_name": template_name,
        "overview": overview,
        "setting_background": setting_background,
        "tone_style": tone_style,
        "male_character_roles": male_character_roles,
        "female_character_roles": female_character_roles,
    })
    mark_local_data_modified()
    return template_id


def update_story_template(template_id, template_name, overview, setting_background, tone_style, male_character_roles=None, female_character_roles=None):
    result = get_collection("story_templates").update_one(
        {"id": template_id},
        {"$set": {
            "template_name": template_name,
            "overview": overview,
            "setting_background": setting_background,
            "tone_style": tone_style,
            "male_character_roles": male_character_roles,
            "female_character_roles": female_character_roles,
        }},
    )
    if result.modified_count:
        mark_local_data_modified()


def clone_story_template(template_id):
    doc = get_collection("story_templates").find_one({"id": template_id})
    if not doc:
        return None
    new_id = get_next_id("story_templates")
    new_name = build_unique_name("story_templates", "template_name", f"{doc.get('template_name')}_copy")
    data = copy_doc(doc)
    data.update({"_id": new_id, "id": new_id, "created_at": now(), "template_name": new_name})
    get_collection("story_templates").insert_one(data)
    for chapter in get_collection("story_template_chapters").find({"template_id": template_id}).sort("chapter_number", 1):
        add_story_template_chapter(new_id, chapter.get("chapter_number"), chapter.get("chapter_description"))
    mark_local_data_modified()
    return new_id


def delete_story_template(template_id):
    get_collection("story_template_chapters").delete_many({"template_id": template_id})
    result = get_collection("story_templates").delete_one({"id": template_id})
    if result.deleted_count:
        mark_local_data_modified()


def delete_story_templates(template_ids):
    ids = list(template_ids or [])
    get_collection("story_template_chapters").delete_many({"template_id": {"$in": ids}})
    result = get_collection("story_templates").delete_many({"id": {"$in": ids}})
    if result.deleted_count:
        mark_local_data_modified()
    return result.deleted_count


def get_story_templates():
    return [
        tuple_from_doc(doc, ["id", "created_at", "template_name", "overview", "setting_background", "tone_style", "male_character_roles", "female_character_roles"])
        for doc in get_collection("story_templates").find().sort("template_name", 1)
    ]


def get_story_template(template_id):
    doc = get_collection("story_templates").find_one({"id": template_id})
    return tuple_from_doc(doc, ["id", "created_at", "template_name", "overview", "setting_background", "tone_style", "male_character_roles", "female_character_roles"]) if doc else None


def get_story_templates_for_export(template_ids, decrypt_values=True):
    ids = list(template_ids or [])
    return {
        "story_templates": [
            dict_from_doc(doc, ["id", "created_at", "template_name", "overview", "setting_background", "tone_style", "male_character_roles", "female_character_roles"])
            for doc in get_collection("story_templates").find({"id": {"$in": ids}}).sort("template_name", 1)
        ],
        "story_template_chapters": [
            dict_from_doc(doc, ["id", "template_id", "chapter_number", "chapter_description"])
            for doc in get_collection("story_template_chapters").find({"template_id": {"$in": ids}}).sort([("template_id", 1), ("chapter_number", 1)])
        ],
    }


def add_story_template_chapter(template_id, chapter_number, chapter_description):
    chapter_id = get_next_id("story_template_chapters")
    get_collection("story_template_chapters").insert_one({
        "_id": chapter_id,
        "id": chapter_id,
        "template_id": template_id,
        "chapter_number": chapter_number,
        "chapter_description": chapter_description,
    })
    mark_local_data_modified()
    return chapter_id


def update_story_template_chapter(chapter_id, chapter_number, chapter_description):
    result = get_collection("story_template_chapters").update_one(
        {"id": chapter_id},
        {"$set": {"chapter_number": chapter_number, "chapter_description": chapter_description}},
    )
    if result.modified_count:
        mark_local_data_modified()


def delete_story_template_chapter(chapter_id):
    result = get_collection("story_template_chapters").delete_one({"id": chapter_id})
    if result.deleted_count:
        mark_local_data_modified()


def get_story_template_chapters(template_id):
    return [
        tuple_from_doc(doc, ["id", "template_id", "chapter_number", "chapter_description"])
        for doc in get_collection("story_template_chapters").find({"template_id": template_id}).sort("chapter_number", 1)
    ]


def replace_character_placeholders(text, male_characters, female_characters):
    if not text:
        return ""

    def replace_match(match):
        gender_code = match.group(1)
        number = int(match.group(2))
        index = number - 1

        if gender_code == "M" and index < len(male_characters):
            return male_characters[index]
        if gender_code == "F" and index < len(female_characters):
            return female_characters[index]
        return match.group(0)

    return re.sub(r"\b([MF])(\d+)\b", replace_match, text)


def add_story(story_name, template_id, overview, setting_background, tone_style, male_characters, female_characters, additional_instructions="", language="", language_level=""):
    story_id = get_next_id("stories")
    get_collection("stories").insert_one(build_story_doc(story_id, story_name, template_id, overview, setting_background, tone_style, male_characters, female_characters, additional_instructions, language, language_level))
    mark_local_data_modified()
    return story_id


def build_story_doc(story_id, story_name, template_id, overview, setting_background, tone_style, male_characters, female_characters, additional_instructions="", language="", language_level=""):
    return {
        "_id": story_id,
        "id": story_id,
        "created_at": now(),
        "story_name": story_name,
        "template_id": template_id,
        "overview": overview,
        "setting_background": setting_background,
        "tone_style": tone_style,
        "additional_instructions": additional_instructions,
        "language": language,
        "language_level": language_level,
        "male_characters": json.dumps(male_characters or [], ensure_ascii=False),
        "female_characters": json.dumps(female_characters or [], ensure_ascii=False),
    }


def update_story(story_id, story_name, overview, setting_background, tone_style, male_characters, female_characters, additional_instructions="", language="", language_level=""):
    result = get_collection("stories").update_one(
        {"id": story_id},
        {"$set": {
            "story_name": story_name,
            "overview": overview,
            "setting_background": setting_background,
            "tone_style": tone_style,
            "additional_instructions": additional_instructions,
            "language": language,
            "language_level": language_level,
            "male_characters": json.dumps(male_characters or [], ensure_ascii=False),
            "female_characters": json.dumps(female_characters or [], ensure_ascii=False),
        }},
    )
    if result.modified_count:
        mark_local_data_modified()


def delete_story(story_id):
    get_collection("story_chapters").delete_many({"story_id": story_id})
    result = get_collection("stories").delete_one({"id": story_id})
    if result.deleted_count:
        mark_local_data_modified()


def delete_stories(story_ids):
    ids = list(story_ids or [])
    get_collection("story_chapters").delete_many({"story_id": {"$in": ids}})
    result = get_collection("stories").delete_many({"id": {"$in": ids}})
    if result.deleted_count:
        mark_local_data_modified()
    return result.deleted_count


def clone_story(story_id):
    doc = get_collection("stories").find_one({"id": story_id})
    if not doc:
        return None
    new_id = get_next_id("stories")
    new_name = build_unique_name("stories", "story_name", f"{doc.get('story_name')}_copy")
    data = copy_doc(doc)
    data.update({"_id": new_id, "id": new_id, "created_at": now(), "story_name": new_name})
    get_collection("stories").insert_one(data)
    for chapter in get_collection("story_chapters").find({"story_id": story_id}).sort("chapter_number", 1):
        add_story_chapter(new_id, chapter.get("chapter_number"), chapter.get("chapter_description"), chapter.get("chapter_body"), chapter.get("chapter_summary"))
    mark_local_data_modified()
    return new_id


def get_stories():
    return [
        tuple_from_doc(doc, ["id", "created_at", "story_name", "template_id", "overview", "setting_background", "tone_style", "additional_instructions", "language", "language_level", "male_characters", "female_characters"])
        for doc in get_collection("stories").find().sort([("created_at", -1), ("id", -1)])
    ]


def get_story(story_id):
    doc = get_collection("stories").find_one({"id": story_id})
    return tuple_from_doc(doc, ["id", "created_at", "story_name", "template_id", "overview", "setting_background", "tone_style", "additional_instructions", "language", "language_level", "male_characters", "female_characters"]) if doc else None


def get_stories_for_export(story_ids, decrypt_values=True):
    ids = list(story_ids or [])
    return {
        "stories": [
            dict_from_doc(doc, ["id", "created_at", "story_name", "template_id", "overview", "setting_background", "tone_style", "additional_instructions", "language", "language_level", "male_characters", "female_characters"])
            for doc in get_collection("stories").find({"id": {"$in": ids}}).sort("story_name", 1)
        ],
        "story_chapters": [
            dict_from_doc(doc, ["id", "story_id", "chapter_number", "chapter_description", "chapter_body", "chapter_summary"])
            for doc in get_collection("story_chapters").find({"story_id": {"$in": ids}}).sort([("story_id", 1), ("chapter_number", 1)])
        ],
    }


def create_story_from_template(template_id, story_name, male_characters, female_characters, additional_instructions="", language="", language_level=""):
    template = get_story_template(template_id)
    if not template:
        return None
    _id, _created_at, _name, overview, setting_background, tone_style, _male_roles, _female_roles = template
    story_id = add_story(
        story_name,
        template_id,
        replace_character_placeholders(overview, male_characters, female_characters),
        replace_character_placeholders(setting_background, male_characters, female_characters),
        tone_style,
        male_characters,
        female_characters,
        additional_instructions,
        language,
        language_level,
    )
    add_story_chapter(story_id, 0, "Establish the setting and introduce the characters.", "", "")
    for _chapter_id, _template_id, chapter_number, chapter_description in get_story_template_chapters(template_id):
        add_story_chapter(
            story_id,
            chapter_number,
            replace_character_placeholders(chapter_description, male_characters, female_characters),
            "",
            "",
        )
    return story_id


def add_story_chapter(story_id, chapter_number, chapter_description, chapter_body, chapter_summary):
    with timed_operation(
        "database_save",
        completed_event_type=EVENT_DATABASE_SAVE_COMPLETED,
        failed_event_type=EVENT_DATABASE_SAVE_FAILED,
        story_id=story_id,
        metadata={
            "table": "story_chapters",
            "action": "insert",
            "chapter_number": chapter_number,
        },
    ):
        chapter_id = get_next_id("story_chapters")
        get_collection("story_chapters").insert_one({
            "_id": chapter_id,
            "id": chapter_id,
            "story_id": story_id,
            "chapter_number": chapter_number,
            "chapter_description": chapter_description,
            "chapter_body": chapter_body,
            "chapter_summary": chapter_summary,
        })
        mark_local_data_modified()
    return chapter_id


def update_story_chapter(chapter_id, chapter_number, chapter_description, chapter_body, chapter_summary):
    with timed_operation(
        "database_save",
        completed_event_type=EVENT_DATABASE_SAVE_COMPLETED,
        failed_event_type=EVENT_DATABASE_SAVE_FAILED,
        chapter_id=chapter_id,
        metadata={
            "table": "story_chapters",
            "action": "update",
            "chapter_number": chapter_number,
        },
    ):
        result = get_collection("story_chapters").update_one(
            {"id": chapter_id},
            {"$set": {
                "chapter_number": chapter_number,
                "chapter_description": chapter_description,
                "chapter_body": chapter_body,
                "chapter_summary": chapter_summary,
            }},
        )
        if result.modified_count:
            mark_local_data_modified()


def get_story_chapter(chapter_id):
    doc = get_collection("story_chapters").find_one({"id": chapter_id})
    return tuple_from_doc(doc, ["id", "story_id", "chapter_number", "chapter_description", "chapter_body", "chapter_summary"]) if doc else None


def delete_story_chapter(chapter_id):
    result = get_collection("story_chapters").delete_one({"id": chapter_id})
    if result.deleted_count:
        mark_local_data_modified()


def get_story_chapters(story_id):
    return [
        tuple_from_doc(doc, ["id", "story_id", "chapter_number", "chapter_description", "chapter_body", "chapter_summary"])
        for doc in get_collection("story_chapters").find({"story_id": story_id}).sort("chapter_number", 1)
    ]


def replace_story_beats(story_id, chapter_number, beats):
    get_collection("story_beats").delete_many({"story_id": story_id, "chapter_number": chapter_number})
    timestamp = now()
    docs = []
    for beat in beats or []:
        beat_id = get_next_id("story_beats")
        docs.append({
            "_id": beat_id,
            "id": beat_id,
            "story_id": story_id,
            "chapter_number": chapter_number,
            "sequence_number": beat.get("sequence_number"),
            "beat_type": beat.get("beat_type"),
            "title": beat.get("title"),
            "characters": beat.get("characters") or [],
            "location": beat.get("location"),
            "time_span": beat.get("time_span"),
            "summary": beat.get("summary"),
            "continuity_effect": beat.get("continuity_effect"),
            "unresolved_threads": beat.get("unresolved_threads") or [],
            "search_keywords": beat.get("search_keywords") or [],
            "created_at": timestamp,
            "updated_at": timestamp,
        })
    if docs:
        get_collection("story_beats").insert_many(docs)
    mark_local_data_modified()


def get_story_beats(story_id=None, chapter_number=None):
    query = {}
    if story_id is not None:
        query["story_id"] = story_id
    if chapter_number is not None:
        query["chapter_number"] = chapter_number
    return [
        dict_from_doc(doc, ["id", "story_id", "chapter_number", "sequence_number", "beat_type", "title", "characters", "location", "time_span", "summary", "continuity_effect", "unresolved_threads", "search_keywords", "created_at", "updated_at"])
        for doc in get_collection("story_beats").find(query).sort([("story_id", 1), ("chapter_number", 1), ("sequence_number", 1)])
    ]


def delete_story_beats(story_id, chapter_number=None):
    query = {"story_id": story_id}
    if chapter_number is not None:
        query["chapter_number"] = chapter_number
    result = get_collection("story_beats").delete_many(query)
    if result.deleted_count:
        mark_local_data_modified()


def log_object_history(object_type, object_id, object_name, operation, contents):
    history_id = get_next_id("object_history")
    get_collection("object_history").insert_one({
        "_id": history_id,
        "id": history_id,
        "created_at": now(),
        "object_type": object_type,
        "object_id": str(object_id) if object_id is not None else "",
        "object_name": object_name or "",
        "operation": operation,
        "contents": json.dumps(contents or {}, ensure_ascii=False),
    })
    mark_local_data_modified()


def get_object_history():
    return [
        tuple_from_doc(doc, ["id", "created_at", "object_type", "object_id", "object_name", "operation", "contents"])
        for doc in get_collection("object_history").find().sort([("created_at", -1), ("id", -1)])
    ]


def log_app_event(
    event_type,
    status="",
    duration_ms=None,
    story_id=None,
    chapter_id=None,
    template_id=None,
    character_id=None,
    provider="",
    model="",
    token_estimate=None,
    error_type="",
    error_message="",
    metadata_json="",
    timestamp=None,
):
    event_id = get_next_id("app_events")
    get_collection("app_events").insert_one({
        "_id": event_id,
        "id": event_id,
        "event_type": event_type,
        "timestamp": timestamp or now(),
        "status": status or "",
        "duration_ms": duration_ms,
        "story_id": story_id,
        "chapter_id": chapter_id,
        "template_id": template_id,
        "character_id": character_id,
        "provider": provider or "",
        "model": model or "",
        "token_estimate": token_estimate,
        "error_type": error_type or "",
        "error_message": error_message or "",
        "metadata_json": metadata_json or "",
    })
    return event_id


def get_app_events(limit=100):
    return [
        tuple_from_doc(
            doc,
            [
                "id",
                "event_type",
                "timestamp",
                "status",
                "duration_ms",
                "story_id",
                "chapter_id",
                "template_id",
                "character_id",
                "provider",
                "model",
                "token_estimate",
                "error_type",
                "error_message",
                "metadata_json",
            ]
        )
        for doc in get_collection("app_events")
        .find()
        .sort([("timestamp", -1), ("id", -1)])
        .limit(int(limit or 100))
    ]


def save_llm_call(provider, model, prompt, response):
    with timed_operation(
        "database_save",
        completed_event_type=EVENT_DATABASE_SAVE_COMPLETED,
        failed_event_type=EVENT_DATABASE_SAVE_FAILED,
        provider=provider,
        model=model,
        metadata={"table": "llm_calls", "action": "insert"},
    ):
        call_id = get_next_id("llm_calls")
        get_collection("llm_calls").insert_one({
            "_id": call_id,
            "id": call_id,
            "created_at": now(),
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "response": response,
        })
        mark_local_data_modified()


def save_failed_llm_call(provider, model, prompt, response, error_type, error_codes, error_message, error_details):
    with timed_operation(
        "database_save",
        completed_event_type=EVENT_DATABASE_SAVE_COMPLETED,
        failed_event_type=EVENT_DATABASE_SAVE_FAILED,
        provider=provider,
        model=model,
        metadata={"table": "failed_llm_calls", "action": "insert"},
    ):
        call_id = get_next_id("failed_llm_calls")
        get_collection("failed_llm_calls").insert_one({
            "_id": call_id,
            "id": call_id,
            "created_at": now(),
            "provider": provider,
            "model": model,
            "prompt": prompt,
            "response": response,
            "error_type": error_type,
            "error_codes": error_codes,
            "error_message": error_message,
            "error_details": error_details,
        })
        mark_local_data_modified()


def get_llm_calls():
    return [
        tuple_from_doc(doc, ["id", "created_at", "provider", "model", "prompt", "response"])
        for doc in get_collection("llm_calls").find().sort("id", -1)
    ]


def get_failed_llm_calls():
    return [
        tuple_from_doc(doc, ["id", "created_at", "provider", "model", "prompt", "response", "error_type", "error_codes", "error_message", "error_details"])
        for doc in get_collection("failed_llm_calls").find().sort("id", -1)
    ]


def add_llm_model(provider, model, best_use, is_default=False):
    if is_default:
        get_collection("llm_models").update_many({"provider": provider}, {"$set": {"is_default": 0}})
    existing = get_collection("llm_models").find_one({"provider": provider, "model": model})
    if existing:
        get_collection("llm_models").update_one(
            {"_id": existing["_id"]},
            {"$set": {"best_use": best_use, "is_default": 1 if is_default else existing.get("is_default", 0)}},
        )
    else:
        model_id = get_next_id("llm_models")
        get_collection("llm_models").insert_one({
            "_id": model_id,
            "id": model_id,
            "provider": provider,
            "model": model,
            "best_use": best_use,
            "is_default": 1 if is_default else 0,
        })
    mark_local_data_modified()


def set_default_llm_model(model_id):
    doc = get_collection("llm_models").find_one({"id": model_id})
    if not doc:
        return False
    get_collection("llm_models").update_many({"provider": doc.get("provider")}, {"$set": {"is_default": 0}})
    get_collection("llm_models").update_one({"id": model_id}, {"$set": {"is_default": 1}})
    mark_local_data_modified()
    return True


def delete_llm_model(model_id):
    if get_collection("llm_models").delete_one({"id": model_id}).deleted_count:
        mark_local_data_modified()


def delete_llm_models(model_ids):
    result = get_collection("llm_models").delete_many({"id": {"$in": list(model_ids or [])}})
    if result.deleted_count:
        mark_local_data_modified()
    return result.deleted_count


def get_llm_models():
    return [
        tuple_from_doc(doc, ["id", "provider", "model", "best_use", "is_default"])
        for doc in get_collection("llm_models").find().sort([("provider", 1), ("is_default", -1), ("model", 1)])
    ]


def get_llm_models_for_export(model_ids):
    return [
        dict_from_doc(doc, ["id", "provider", "model", "best_use", "is_default"])
        for doc in get_collection("llm_models").find({"id": {"$in": list(model_ids or [])}}).sort([("provider", 1), ("model", 1)])
    ]


def get_llm_models_by_provider(provider):
    return [
        tuple_from_doc(doc, ["id", "provider", "model", "best_use", "is_default"])
        for doc in get_collection("llm_models").find({"provider": provider}).sort([("is_default", -1), ("model", 1)])
    ]


def export_database_to_dict(include_database_encryption_metadata=False):
    data = {}
    for key, collection_name in TABLE_COLLECTIONS.items():
        if key == "sync_metadata":
            continue
        data[key] = [
            clean_export_doc(doc)
            for doc in get_collection(collection_name).find().sort("id", 1)
        ]
    return data


def prepare_export_data(encrypt_values=False, password=""):
    data = export_database_to_dict()

    if encrypt_values:
        return encrypt_export_values(data, password)

    return data


def serialize_export_to_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False)


def serialize_export_to_yaml(data):
    import yaml

    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def export_database_to_json(encrypt_values=False, password=""):
    return serialize_export_to_json(
        prepare_export_data(
            encrypt_values=encrypt_values,
            password=password,
        )
    )


def export_database_to_yaml(encrypt_values=False, password=""):
    return serialize_export_to_yaml(
        prepare_export_data(
            encrypt_values=encrypt_values,
            password=password,
        )
    )


def import_database_from_dict(
    data,
    replace_existing=False,
    database_password=""
):
    if replace_existing:
        clear_imported_collections()

    counts = {}
    for key, rows in (data or {}).items():
        if key not in TABLE_COLLECTIONS or key == "sync_metadata":
            continue
        collection = get_collection(TABLE_COLLECTIONS[key])
        count = 0
        max_id = 0
        for row in rows or []:
            doc = dict(row)
            doc.pop("_id", None)
            doc_id = coerce_import_id(
                doc.get("id")
                or get_next_id(TABLE_COLLECTIONS[key])
            )
            doc["_id"] = doc_id
            doc["id"] = doc_id
            collection.replace_one({"id": doc["id"]}, doc, upsert=True)
            if isinstance(doc_id, int):
                max_id = max(max_id, doc_id)
            count += 1
        if max_id:
            sync_counter(TABLE_COLLECTIONS[key], max_id)
        counts[key] = count
    mark_local_data_modified()
    return counts


def import_database_from_json(
    json_data,
    replace_existing=False,
    password="",
    database_password=""
):
    data = json.loads(read_import_text(json_data) or "{}")

    if password:
        data = decrypt_export_values(data, password)

    return import_database_from_dict(
        data,
        replace_existing=replace_existing,
        database_password=database_password,
    )


def import_database_from_yaml(
    yaml_data,
    replace_existing=False,
    password="",
    database_password=""
):
    data = yaml.safe_load(read_import_text(yaml_data) or "{}") or {}

    if password:
        data = decrypt_export_values(data, password)

    return import_database_from_dict(
        data,
        replace_existing=replace_existing,
        database_password=database_password,
    )


def read_import_text(value):
    if hasattr(value, "read"):
        value = value.read()

    if isinstance(value, bytes):
        return value.decode("utf-8")

    return value or ""


def clear_imported_collections():
    for key, collection_name in TABLE_COLLECTIONS.items():
        if key == "sync_metadata":
            continue
        get_collection(collection_name).delete_many({})


def coerce_import_id(value):
    if isinstance(value, int):
        return value

    if isinstance(value, str) and value.isdigit():
        return int(value)

    return value


def sync_counter(collection_name, max_id):
    get_collection("counters").update_one(
        {"_id": collection_name},
        {"$max": {"value": max_id}},
        upsert=True,
    )


def decrypt_database_row(table_name, row, columns):
    return row


def decrypt_database_rows(table_name, rows, columns):
    return rows


def decrypt_database_tuple(table_name, row, columns):
    return row


def enable_database_encryption(password):
    return None


def encrypt_database_field(table_name, field_name, value):
    return value


def encrypt_database_row(table_name, row):
    return row


def apply_database_encryption_export_metadata(metadata):
    return None


def get_database_encryption_export_metadata():
    return None


def get_database_encryption_status():
    return {"enabled": False, "unlocked": True}


def initialize_database_encryption():
    return None


def is_database_encrypted_value(value):
    return False


def is_database_encryption_enabled():
    return False


def set_active_database_password(password):
    return None


def get_database_provider_status():
    return {
        "provider": "mongodb",
        "label": "MongoDB Atlas",
    }


def tuple_from_doc(doc, fields):
    return tuple((doc or {}).get(field) for field in fields)


def dict_from_doc(doc, fields):
    return {field: (doc or {}).get(field) for field in fields}


def copy_doc(doc):
    data = copy.deepcopy(doc)
    data.pop("_id", None)
    return data


def clean_export_doc(doc):
    data = dict(doc)
    data.pop("_id", None)
    return data


def build_unique_name(collection_name, field_name, base_name):
    collection = get_collection(collection_name)
    new_name = base_name
    counter = 1
    while collection.find_one({field_name: new_name}):
        counter += 1
        new_name = f"{base_name}_{counter}"
    return new_name
