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
  - `models_view.py`: LLM model configuration
  - `history_view.py`: LLM call history
  - `export_import_view.py`: Data import/export functionality
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
  - `template_service.py`: Template management
  - `model_service.py`: LLM model operations
  - `sync_service.py`: MongoDB synchronization
- **Technology**: Python business logic, integrates with database and LLM client

### 3. Database (`database/`)
- **Purpose**: Data persistence and access layer
- **Contents**:
  - `schema.py`: SQLite table definitions
  - `connection.py`: Database connection management
  - `characters.py`, `profiles.py`, `stories.py`, etc.: Table-specific operations
  - `import_export.py`: Data serialization/deserialization
  - `db_encryption.py`: Field-level encryption
  - `migrations.py`: Schema migration logic
  - `llm_calls.py`: LLM interaction logging
- **Technology**: SQLite with optional encryption

### 4. LLM Integration
- **Purpose**: External AI service integration
- **Files**:
  - `llm_client.py`: Main LLM interaction interface
  - `llm_providers.py`: Provider-specific implementations (Gemini, Groq, OpenRouter)
  - `llm_logging.py`: Request/response logging
  - `llm_throttle.py`: Rate limiting and throttling
  - `prompts.py`: Prompt template construction
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
5. **Response**: Results flow back through services to update views

## Entry Point

- `app.py`: Main Streamlit application file that wires together all components
- Runs migrations and initializes database on startup
- Manages tab-based navigation between different views

## Technology Stack

- **Frontend/UI**: Streamlit
- **Backend**: Python
- **Database**: SQLite
- **LLM Providers**: Google Gemini, Groq, OpenRouter
- **Additional**: PyMongo for optional MongoDB sync, Cryptography for encryption