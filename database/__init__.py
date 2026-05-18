from database.provider import get_active_db_provider, using_mongodb


if using_mongodb():
    from database.mongodb_repositories import (
        ADMINISTRATOR_ROLE,
        DATABASE_ENCRYPTION_EXPORT_KEY,
        add_authorized_user,
        add_llm_model,
        add_profile,
        add_story,
        add_story_chapter,
        add_story_template,
        add_story_template_chapter,
        apply_database_encryption_export_metadata,
        bind_authorized_user_google_sub,
        character_name_exists,
        clone_character,
        clone_profile,
        clone_story,
        clone_story_template,
        create_story_from_template,
        create_tables,
        decrypt_database_row,
        decrypt_database_rows,
        decrypt_database_tuple,
        delete_authorized_user,
        delete_character,
        delete_characters,
        delete_llm_model,
        delete_llm_models,
        delete_profile,
        delete_profiles,
        delete_stories,
        delete_story,
        delete_story_beats,
        delete_story_chapter,
        delete_story_template,
        delete_story_template_chapter,
        delete_story_templates,
        enable_database_encryption,
        encrypt_database_field,
        encrypt_database_row,
        export_database_to_dict,
        export_database_to_json,
        export_database_to_yaml,
        get_authorized_user_by_identity,
        get_authorized_users,
        get_characters,
        get_characters_by_gender,
        get_characters_for_export,
        get_character_summaries_by_names,
        get_database_encryption_export_metadata,
        get_database_encryption_status,
        get_database_provider_status,
        get_failed_llm_calls,
        get_llm_calls,
        get_llm_models,
        get_llm_models_by_provider,
        get_llm_models_for_export,
        get_object_history,
        get_profiles,
        get_profiles_for_export,
        get_stories,
        get_stories_for_export,
        get_story,
        get_story_beats,
        get_story_chapter,
        get_story_chapters,
        get_story_template,
        get_story_template_chapters,
        get_story_templates,
        get_story_templates_for_export,
        get_sync_metadata,
        import_database_from_dict,
        import_database_from_json,
        import_database_from_yaml,
        initialize_database_encryption,
        is_database_encrypted_value,
        is_database_encryption_enabled,
        log_object_history,
        mark_local_data_modified,
        prepare_export_data,
        reinitialize_database,
        rename_profile,
        replace_story_beats,
        run_migrations,
        save_character,
        save_failed_llm_call,
        save_llm_call,
        seed_common_names,
        seed_default_authorized_user,
        serialize_export_to_json,
        serialize_export_to_yaml,
        set_active_database_password,
        set_default_llm_model,
        set_sync_metadata,
        suggest_character_name,
        update_authorized_user,
        update_character,
        update_profile,
        update_story,
        update_story_chapter,
        update_story_template,
        update_story_template_chapter,
    )
else:
    from database.characters import (
        clone_character,
        delete_character,
        delete_characters,
        get_characters,
        get_characters_for_export,
        get_characters_by_gender,
        get_character_summaries_by_names,
        save_character,
        update_character,
    )

    from database.authorized_users import (
        ADMINISTRATOR_ROLE,
        add_authorized_user,
        bind_authorized_user_google_sub,
        delete_authorized_user,
        get_authorized_user_by_identity,
        get_authorized_users,
        seed_default_authorized_user,
        update_authorized_user,
    )

    from database.import_export import (
        export_database_to_dict,
        export_database_to_json,
        export_database_to_yaml,
        import_database_from_dict,
        import_database_from_json,
        import_database_from_yaml,
        prepare_export_data,
        serialize_export_to_json,
        serialize_export_to_yaml,
    )

    from database.llm_calls import (
        get_failed_llm_calls,
        get_llm_calls,
        save_failed_llm_call,
        save_llm_call,
    )

    from database.llm_models import (
        add_llm_model,
        delete_llm_model,
        delete_llm_models,
        get_llm_models,
        get_llm_models_for_export,
        get_llm_models_by_provider,
        set_default_llm_model,
    )

    from database.maintenance import reinitialize_database

    from database.metadata import (
        get_sync_metadata,
        mark_local_data_modified,
        set_sync_metadata,
    )

    from database.object_history import (
        get_object_history,
        log_object_history,
    )

    from database.migrations import run_migrations

    from database.profiles import (
        add_profile,
        clone_profile,
        delete_profile,
        delete_profiles,
        get_profiles,
        get_profiles_for_export,
        rename_profile,
        update_profile,
    )

    from database.schema import create_tables

    from database.templates import (
        add_story_template,
        add_story_template_chapter,
        clone_story_template,
        delete_story_template,
        delete_story_template_chapter,
        delete_story_templates,
        get_story_template,
        get_story_template_chapters,
        get_story_templates_for_export,
        get_story_templates,
        update_story_template,
        update_story_template_chapter,
    )

    from database.stories import (
        add_story,
        add_story_chapter,
        clone_story,
        create_story_from_template,
        delete_story,
        delete_story_chapter,
        delete_stories,
        get_stories,
        get_stories_for_export,
        get_story,
        get_story_chapter,
        get_story_chapters,
        update_story,
        update_story_chapter,
    )

    from database.story_beats import (
        delete_story_beats,
        get_story_beats,
        replace_story_beats,
    )

    from database.common_names import (
        character_name_exists,
        seed_common_names,
        suggest_character_name,
    )

    from database.db_encryption import (
        DATABASE_ENCRYPTION_EXPORT_KEY,
        decrypt_database_row,
        decrypt_database_rows,
        decrypt_database_tuple,
        enable_database_encryption,
        encrypt_database_field,
        encrypt_database_row,
        apply_database_encryption_export_metadata,
        get_database_encryption_export_metadata,
        get_database_encryption_status,
        initialize_database_encryption,
        is_database_encrypted_value,
        is_database_encryption_enabled,
        set_active_database_password,
    )


    def get_database_provider_status():
        return {
            "provider": "sqlite",
            "label": "SQLite",
        }
