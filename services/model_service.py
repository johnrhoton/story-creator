from database import (
    add_llm_model,
    delete_llm_model,
    delete_llm_models,
    get_llm_models,
    get_llm_models_for_export,
    get_llm_models_by_provider,
    set_default_llm_model,
)


def list_llm_models():
    return get_llm_models()


def list_llm_models_for_export(model_ids):
    return get_llm_models_for_export(model_ids)


def list_llm_models_by_provider(provider):
    return get_llm_models_by_provider(provider)


def create_llm_model(provider, model, best_use, is_default=False):
    add_llm_model(
        provider,
        model,
        best_use,
        is_default
    )


def delete_existing_llm_model(model_id):
    delete_llm_model(model_id)


def delete_existing_llm_models(model_ids):
    return delete_llm_models(model_ids)


def set_existing_llm_model_as_default(model_id):
    return set_default_llm_model(model_id)
