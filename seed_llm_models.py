from database import add_llm_model, create_tables, run_migrations


DEFAULT_MODELS = [
    ("Groq", "llama-3.3-70b-versatile", "General coding + reasoning"),
    ("Groq", "llama-3.1-8b-instant", "Very fast lightweight tasks"),
    ("Groq", "qwen-qwq-32b", "Reasoning"),
    ("Groq", "qwen3-32b", "Coding + structured output"),
    ("Groq", "deepseek-r1-distill-llama-70b", "Reasoning/coding"),
    ("Groq", "mixtral-8x7b-32768", "General assistant"),
    ("Groq", "gemma2-9b-it", "Small efficient model"),
    ("Gemini", "gemini-2.5-flash", "General fast coding/reasoning"),
    ("Gemini", "gemini-2.5-pro", "Strong reasoning (more restricted limits)"),
    ("Gemini", "gemini-2.5-flash-lite", "Cheap/high-speed tasks"),
    ("OpenRouter", "openrouter/auto", "Multi-model Routing Layer"),
    ("OpenRouter", "qwen/qwen3-coder:free", "Excellent coding"),
    ("OpenRouter", "deepseek/deepseek-r1:free", "Strong reasoning"),
    (
        "OpenRouter",
        "meta-llama/llama-3.3-70b-instruct:free",
        "General assistant"
    ),
    (
        "OpenRouter",
        "mistralai/mistral-small:free",
        "Lightweight structured tasks"
    ),
    ("OpenRouter", "google/gemma-3-27b-it:free", "Good open model"),
    ("OpenRouter", "nvidia/nemotron:free", "Strong reasoning"),
    ("OpenRouter", "openai/gpt-oss-120b:free", "OpenAI open-weight model"),
    ("OpenRouter", "poolside/laguna:free", "Agentic coding"),
    ("OpenRouter", "google/gemini-flash-1.5:free", "Gemini access"),
    ("OpenRouter", "nousresearch/hermes-3:free", "Open assistant"),
]


DEFAULT_MODEL_NAMES = {
    "Groq": "llama-3.3-70b-versatile",
    "Gemini": "gemini-2.5-flash",
    "OpenRouter": "openrouter/auto"
}


def seed_llm_models():
    run_migrations()
    create_tables()

    for provider, model, best_use in DEFAULT_MODELS:
        add_llm_model(
            provider,
            model,
            best_use,
            model == DEFAULT_MODEL_NAMES.get(provider)
        )


if __name__ == "__main__":
    seed_llm_models()
    print(f"Seeded {len(DEFAULT_MODELS)} LLM model(s).")
