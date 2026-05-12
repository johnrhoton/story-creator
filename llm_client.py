import os

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from groq import Groq

from database import save_llm_call


def generate_text(provider, model, prompt):
    try:
        if provider == "Gemini":
            response = generate_with_gemini(model, prompt)
            log_llm_call(provider, model, prompt, response)
            return response

        if provider == "Groq":
            response = generate_with_groq(model, prompt)
            log_llm_call(provider, model, prompt, response)
            return response

        st.error(f"Unsupported LLM provider: {provider}")
        return None

    except genai_errors.ServerError as error:
        error_text = str(error)

        if "503" in error_text or "UNAVAILABLE" in error_text:
            st.error(
                "The selected LLM model is currently unavailable or under high demand. "
                "Please try again, or choose a different model in the sidebar."
            )
        else:
            st.error(f"Gemini server error: {error}")

        return None

    except genai_errors.ClientError as error:
        st.error(
            "The LLM request was rejected. Check your API key, model name, "
            "quota, or request format."
        )

        with st.expander("Technical details"):
            st.code(str(error))

        return None

    except Exception as error:
        st.error("Unexpected error while calling the LLM.")

        with st.expander("Technical details"):
            st.code(str(error))

        return None


def generate_with_gemini(model, prompt):
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error("GEMINI_API_KEY not found. Check your .env file.")
        return None

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=prompt
    )

    return response.text


def generate_with_groq(model, prompt):
    load_dotenv()

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        st.error("GROQ_API_KEY not found. Check your .env file.")
        return None

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.choices[0].message.content


def log_llm_call(provider, model, prompt, response):
    if response is None:
        return

    save_llm_call(
        provider,
        model,
        prompt,
        response
    )
