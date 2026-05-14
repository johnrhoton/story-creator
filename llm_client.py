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
