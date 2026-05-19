import requests
from google import genai
from groq import Groq

from config import get_config_value


SUPPORTED_PROVIDERS = ["Gemini", "Groq", "OpenRouter"]


def generate_with_provider(provider, model, prompt):
    if provider == "Gemini":
        return generate_with_gemini(model, prompt)

    if provider == "Groq":
        return generate_with_groq(model, prompt)

    if provider == "OpenRouter":
        return generate_with_openrouter(model, prompt)

    raise ValueError(f"Unsupported LLM provider: {provider}")


def generate_with_gemini(model, prompt):
    api_key = get_api_key("GEMINI_API_KEY")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=prompt
    )

    return response.text


def generate_with_groq(model, prompt):
    api_key = get_api_key("GROQ_API_KEY")

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


def generate_with_openrouter(model, prompt):
    api_key = get_api_key("OPENROUTER_API_KEY")

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-Title": "Story Builder"
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]


def get_api_key(environment_variable):
    api_key = get_config_value(environment_variable)

    if not api_key:
        raise RuntimeError(
            f"{environment_variable} not found. Check Streamlit secrets."
        )

    return api_key
