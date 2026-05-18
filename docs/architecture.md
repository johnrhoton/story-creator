# Architecture

## Overview

Story Builder is built as a Streamlit desktop-style web application. The architecture follows a layered approach to separate concerns and maintain clarity for learning purposes.

## Main Layers

### 1. Views (`views/`)
- **Purpose**: Streamlit UI components and screens
- **Contents**: 
  - `characters_view.py`: Character management interface
  - `profiles_view.py`: Profile creation and editing
  - `templates_view.py`: Story template management
  - `stories_view.py`: Story generation and viewing
  - `story_memory_view.py`: Chroma Story Memory rebuild, search, index inspection, story-memory preview, and story-beat tools
  - `language_aids_view.py`: Standalone Language Aids page for glossary and comprehension question generation
  - `models_view.py`: LLM model configuration
  - `history_view.py`: Object history and LLM call history
  - `export_import_view.py`: Data import/export functionality
  - `administration_view.py`: Administrator-only authorized user management
  - `sidebar_view.py`: Shared UI components like LLM settings
  - `bulk_actions.py`: Bulk operation interfaces
- **Technology**: Streamlit components and forms

### 2. Services (`services/`)
- **Purpose**: Application workflow logic and business rules
- **Contents**:
  - `character_service.py`: Character generation and management logic
  - `profile_service.py`: Profile CRUD operations
  - `story_service.py`: Story creation and chapter management
  - `story_generation_service.py`: LLM-powered story generation
  - `story_beat_service.py`: Story-memory beat extraction, validation, SQLite persistence, and Chroma indexing
  - `story_memory_service.py`: Chroma access, search, and injected STORY MEMORY formatting
  - `story_memory_indexing_service.py`: Rebuildable Chroma indexing from SQLite
  - `glossary_service.py`: Glossary generation, JSON parsing, table formatting, and CSV export
  - `reading_comprehension_service.py`: Reading comprehension question generation, JSON parsing, and CSV export
  - `template_service.py`: Template management
  - `model_service.py`: LLM model operations
  - `auth_service.py`: Google OIDC login and SQLite authorization checks
  - `admin_service.py`: Authorized user CRUD workflow
  - `sync_service.py`: MongoDB synchronization
- **Technology**: Python business logic, integrates with database and LLM client

### 3. Database (`database/`)
- **Purpose**: Data persistence and access layer
- **Contents**:
  - `__init__.py`: Provider selection layer exporting the active repository functions
  - `schema.py`: SQLite table definitions
  - `connection.py`: Database connection management
  - `mongodb_connection.py`: MongoDB Atlas connection and ID counters
  - `mongodb_repositories.py`: MongoDB-backed repositories matching the SQLite function surface
  - `characters.py`, `profiles.py`, `stories.py`, etc.: Table-specific operations
  - `import_export.py`: Data serialization/deserialization
  - `db_encryption.py`: Field-level encryption
  - `migrations.py`: Schema migration logic
  - `llm_calls.py`: LLM interaction logging
  - `object_history.py`: CRUD history records for user-visible objects
  - `story_beats.py`: Persisted story-memory beats extracted from chapters
  - `authorized_users.py`: Authorized Google user whitelist and roles
- **Technology**: Configurable provider: SQLite locally by default, or MongoDB Atlas with `DB_PROVIDER=mongodb`

### 4. LLM Integration
- **Purpose**: External AI service integration
- **Files**:
  - `llm_client.py`: Main LLM interaction interface
  - `llm_providers.py`: Provider-specific implementations (Gemini, Groq, OpenRouter)
  - `llm_logging.py`: Request/response logging
  - `llm_throttle.py`: Rate limiting and throttling
  - `prompts.py`: Prompt template loading/rendering from the `prompts/` folder
- **Technology**: REST API calls to LLM providers

### 5. Configuration and Utilities
- **Purpose**: App configuration and helper functions
- **Files**:
  - `config.py`: Application configuration
  - `ui_helpers.py`: Shared UI utility functions
  - `scripts/`: Command-line utilities for maintenance

## Data Flow

1. **User Interaction**: Views capture user input via Streamlit components
2. **Business Logic**: Services process requests, validate data, and orchestrate operations
3. **Data Persistence**: Database layer handles CRUD operations on SQLite
4. **External Integration**: LLM client handles AI-powered content generation
5. **Memory Indexing**: Chapter summaries, story records, characters, and story beats are indexed in Chroma for retrieval
6. **Response**: Results flow back through services to update views

## Prompt Templates

Prompt text is stored in the `prompts/` folder and rendered by `prompts.py`.
Templates include character generation, chapter generation, chapter summaries,
story-memory insertion, story-beat extraction, glossary generation, and reading
comprehension question generation. Some prompt files contain named sections such
as `[section]`, `[characters]`, or `[item]`; Python selects the relevant section
and supplies dynamic values.

## Story Memory

Story Memory uses Chroma with a persistent local path, `data/chroma_db`. SQLite
remains the source of truth for stories, chapters, characters, and story beats.
Chroma can be rebuilt from SQLite from the Story Memory tab. During chapter generation,
the app retrieves relevant story-specific records and global characters, formats
them through `prompts/story_memory_section.txt`, and injects them into the story
chapter prompt.

For the end-to-end flow, see `docs/story_memory.md`.

## Language Aids

Glossaries and reading comprehension questions are generated on demand from full
stories or individual chapters. They use editable prompt templates, service-layer
JSON parsing, Streamlit display tables, and CSV downloads.

For the end-to-end flow, see `docs/language_aids.md`.

## Entry Point

- `app.py`: Main Streamlit application file that wires together all components
- Runs migrations and initializes database on startup
- Manages tab-based navigation between different views

## Technology Stack

- **Frontend/UI**: Streamlit
- **Backend**: Python
- **Database**: SQLite
- **Vector Store**: Chroma, persisted under `data/chroma_db`
- **LLM Providers**: Google Gemini, Groq, OpenRouter
- **Additional**: PyMongo for optional MongoDB sync, Cryptography for encryption
