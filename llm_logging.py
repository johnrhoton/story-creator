from config import get_config_bool
from database import save_failed_llm_call, save_llm_call


LLM_CONTENT_LOGGING_FLAG = "ENABLE_LLM_CONTENT_LOGGING"


def log_llm_call(provider, model, prompt, response):
    if response is None:
        return

    stored_prompt, stored_response = prepare_llm_content_for_storage(
        prompt,
        response
    )

    save_llm_call(
        provider,
        model,
        stored_prompt,
        stored_response
    )


def log_no_response(provider, model, prompt):
    log_failed_llm_call(
        provider,
        model,
        prompt,
        None,
        "NoResponse",
        "NO_RESPONSE",
        f"{provider} did not return a response.",
        "Check the API key, model name, quota, or request format."
    )


def log_failed_llm_exception(provider, model, prompt, error):
    error_type = type(error).__name__
    error_codes = extract_error_codes(error)
    error_message = str(error)
    error_details = extract_error_details(error)

    log_failed_llm_call(
        provider,
        model,
        prompt,
        None,
        error_type,
        error_codes,
        error_message,
        error_details
    )


def log_failed_llm_call(
    provider,
    model,
    prompt,
    response,
    error_type,
    error_codes,
    error_message,
    error_details
):
    stored_prompt, stored_response = prepare_llm_content_for_storage(
        prompt,
        response or ""
    )

    save_failed_llm_call(
        provider,
        model,
        stored_prompt,
        stored_response,
        error_type or "",
        error_codes or "",
        error_message or "",
        error_details or ""
    )


def prepare_llm_content_for_storage(prompt, response):
    if get_config_bool(LLM_CONTENT_LOGGING_FLAG, False):
        return prompt or "", response or ""

    return (
        "[prompt logging disabled]",
        "[response logging disabled]" if response else "",
    )


def extract_error_codes(error):
    codes = []

    for attribute_name in [
        "code",
        "status_code",
        "status",
        "reason"
    ]:
        value = getattr(error, attribute_name, None)

        if value is not None:
            codes.append(f"{attribute_name}: {value}")

    response = getattr(error, "response", None)

    if response is not None:
        status_code = getattr(response, "status_code", None)

        if status_code is not None:
            codes.append(f"response.status_code: {status_code}")

    error_text = str(error)

    for known_code in [
        "400",
        "401",
        "403",
        "404",
        "429",
        "500",
        "503",
        "UNAVAILABLE",
        "RESOURCE_EXHAUSTED",
        "INVALID_ARGUMENT"
    ]:
        if known_code in error_text and known_code not in codes:
            codes.append(known_code)

    return ", ".join(codes)


def extract_error_details(error):
    detail_parts = []

    for attribute_name in [
        "message",
        "body",
        "response",
        "details"
    ]:
        value = getattr(error, attribute_name, None)

        if value:
            detail_parts.append(f"{attribute_name}: {value}")

    response = getattr(error, "response", None)

    if response is not None:
        response_text = getattr(response, "text", None)

        if response_text:
            detail_parts.append(f"response.text: {response_text}")

    detail_parts.append(f"text: {error}")

    return "\n\n".join(detail_parts)
