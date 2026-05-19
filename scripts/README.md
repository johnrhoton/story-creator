# Command-Line Utilities

These scripts are manual maintenance tools. Run them from the project root so
they use the same Streamlit secrets, database path, and imports as the
Streamlit app.

```bash
./venv/bin/python scripts/migrate.py
```

Runs database migrations without starting Streamlit. The app already runs
migrations at startup, so this is mostly useful for checking migration behavior.

```bash
./venv/bin/python scripts/seed_llm_models.py
```

Prefills the Models tab with the starter Gemini, Groq, and OpenRouter models.
It is safe to run again because models are inserted or replaced by provider and
model name.

```bash
./venv/bin/python scripts/regenerate_characters.py --dry-run
```

Shows planned character name regeneration without updating the database or
calling Gemini. Remove `--dry-run` only when you intentionally want to update
existing character descriptions and summaries.
