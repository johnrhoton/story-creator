import time

import streamlit as st
from google.genai import errors as genai_errors

from database import save_failed_llm_call, save_llm_call
from llm_providers import SUPPORTED_PROVIDERS, generate_with_provider


def generate_text(provider, model, prompt):
    try:
        if provider not in SUPPORTED_PROVIDERS:
            st.error(f"Unsupported LLM provider: {provider}")
            log_failed_llm_call(
                provider,
                model,
                prompt,
                None,
                "UnsupportedProvider",
                "UNSUPPORTED_PROVIDER",
                f"Unsupported LLM provider: {provider}",
                ""
            )

            return None

        throttle_llm_call(provider, model)

        response = generate_with_provider(provider, model, prompt)

        if response is None:
            log_no_response(provider, model, prompt)
            return None

        log_llm_call(provider, model, prompt, response)
        return response

    except genai_errors.ServerError as error:
        error_text = str(error)
        log_failed_llm_exception(provider, model, prompt, error)

        if "503" in error_text or "UNAVAILABLE" in error_text:
            st.error(
                "The selected LLM model is currently unavailable or under high demand. "
                "Please try again, or choose a different model in the sidebar."
            )
        else:
            st.error(f"Gemini server error: {error}")

        return None

    except genai_errors.ClientError as error:
        log_failed_llm_exception(provider, model, prompt, error)

        st.error(
            "The LLM request was rejected. Check your API key, model name, "
            "quota, or request format."
        )

        with st.expander("Technical details"):
            st.code(str(error))

        return None

    except Exception as error:
        log_failed_llm_exception(provider, model, prompt, error)

        st.error("Unexpected error while calling the LLM.")

        with st.expander("Technical details"):
            st.code(str(error))

        return None


def throttle_llm_call(provider, model):
    throttle_interval = float(
        st.session_state.get(
            "llm_throttle_interval_seconds",
            0.0
        ) or 0.0
    )

    if throttle_interval <= 0:
        remember_llm_call_start(provider, model)
        return

    last_call_times = st.session_state.setdefault(
        "llm_last_call_times",
        {}
    )

    throttle_key = f"{provider}:{model}"
    now = time.monotonic()
    last_call_time = last_call_times.get(throttle_key)

    if last_call_time is not None:
        elapsed = now - last_call_time
        wait_seconds = throttle_interval - elapsed

        if wait_seconds > 0:
            st.info(
                f"Waiting {wait_seconds:.1f} seconds before calling "
                f"{provider} / {model}."
            )
            time.sleep(wait_seconds)

    remember_llm_call_start(provider, model)


def remember_llm_call_start(provider, model):
    last_call_times = st.session_state.setdefault(
        "llm_last_call_times",
        {}
    )

    last_call_times[f"{provider}:{model}"] = time.monotonic()


def log_llm_call(provider, model, prompt, response):
    if response is None:
        return

    save_llm_call(
        provider,
        model,
        prompt,
        response
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
    save_failed_llm_call(
        provider,
        model,
        prompt,
        response or "",
        error_type or "",
        error_codes or "",
        error_message or "",
        error_details or ""
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
