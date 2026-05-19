import logging
import time

import streamlit as st
from google.genai import errors as genai_errors

from llm_logging import (
    log_failed_llm_call,
    log_failed_llm_exception,
    log_llm_call,
    log_no_response,
)
from llm_providers import SUPPORTED_PROVIDERS, generate_with_provider
from llm_throttle import throttle_llm_call
from services.observability_service import (
    EVENT_LLM_CALL_COMPLETED,
    EVENT_LLM_CALL_FAILED,
    EVENT_LLM_CALL_STARTED,
    elapsed_ms,
    estimate_tokens,
    record_event,
)


logger = logging.getLogger(__name__)


def generate_text(provider, model, prompt):
    event_fields = {
        "provider": provider,
        "model": model,
        "token_estimate": estimate_tokens(prompt),
    }

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
            record_unsupported_provider_event(provider, model, prompt)

            return None

        start_time = time.perf_counter()
        record_event(
            EVENT_LLM_CALL_STARTED,
            status="started",
            **event_fields,
        )

        throttle_llm_call(provider, model)

        response = generate_with_provider(provider, model, prompt)

        if response is None:
            log_no_response(provider, model, prompt)
            record_event(
                EVENT_LLM_CALL_FAILED,
                status="failed",
                duration_ms=elapsed_ms(start_time),
                error_type="NoResponse",
                error_message=f"{provider} did not return a response.",
                **event_fields,
            )
            return None

        log_llm_call(provider, model, prompt, response)
        record_event(
            EVENT_LLM_CALL_COMPLETED,
            status="completed",
            duration_ms=elapsed_ms(start_time),
            **event_fields,
        )
        return response

    except genai_errors.ServerError as error:
        logger.exception("Gemini server error during LLM call.")
        record_llm_exception_event(error, event_fields, start_time)
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
        logger.exception("Gemini client error during LLM call.")
        record_llm_exception_event(error, event_fields, start_time)
        log_failed_llm_exception(provider, model, prompt, error)

        st.error(
            "The LLM request was rejected. Check your API key, model name, "
            "quota, or request format."
        )

        with st.expander("Technical details"):
            st.code(str(error))

        return None

    except Exception as error:
        logger.exception("Unexpected error during LLM call.")
        record_llm_exception_event(error, event_fields, start_time)
        log_failed_llm_exception(provider, model, prompt, error)

        st.error("Unexpected error while calling the LLM.")

        with st.expander("Technical details"):
            st.code(str(error))

        return None


def record_llm_exception_event(error, event_fields, start_time=None):
    duration_ms = elapsed_ms(start_time) if start_time is not None else None

    record_event(
        EVENT_LLM_CALL_FAILED,
        status="failed",
        duration_ms=duration_ms,
        error_type=type(error).__name__,
        error_message=str(error),
        **event_fields,
    )


def record_unsupported_provider_event(provider, model, prompt):
    record_event(
        EVENT_LLM_CALL_FAILED,
        status="failed",
        provider=provider,
        model=model,
        token_estimate=estimate_tokens(prompt),
        error_type="UnsupportedProvider",
        error_message=f"Unsupported LLM provider: {provider}",
    )
