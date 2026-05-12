# AGENTS.md

## Project purpose

This is a hobby and learning project for building a Streamlit-based fiction/story creation app.

The project has two goals:

1. Provide a usable app for creating characters, reusable profiles, story templates, and generated stories.
2. Serve as a learning platform for LLM-assisted development, LLM integration, storage design, MongoDB, local infrastructure, and eventually Kubernetes/Raspberry Pi deployment experiments.

Prefer changes that support learning, clarity, and architectural evolution over highly optimised production complexity.

## Current architecture

The current application is a Streamlit desktop-style app.

Main layers:

- `views/`: Streamlit UI
- `services/`: application/service logic
- `database/`: SQLite persistence
- `prompts.py`: prompt construction
- `llm_client.py`: LLM integration
- utility/legacy scripts: migration, regeneration, smoke tests

The main entry point is:

```bash
streamlit run app.py