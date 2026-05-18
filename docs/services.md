# Services Technical Description

## Overview

The services layer contains the business logic of the application, orchestrating operations between the UI, database, and external LLM services. Services implement workflows, validation, and integration logic.

## Service Architecture

### Design Principles
- **Separation of Concerns**: Each service handles specific domain logic
- **Dependency Injection**: Services import from database and LLM modules
- **Error Handling**: Graceful failure management with user feedback
- **Validation**: Input validation and business rule enforcement

### Common Patterns
- **CRUD Operations**: Create, Read, Update, Delete for entities
- **Generation Logic**: LLM integration for content creation
- **Data Transformation**: Converting between formats
- **Bulk Operations**: Handling multiple records efficiently

## Core Services

### `character_service.py`
**Purpose**: Character generation and management

**Key Functions**:
- `list_characters()`: Retrieve all characters
- `create_character(profile_data, generation_params)`: Generate new character
- `update_character(id, data)`: Modify existing character
- `delete_character(id)`: Remove character
- `clone_character(id)`: Duplicate character

**LLM Integration**:
- Uses `prompts.build_prompt()` for character generation
- Calls `llm_client.generate_text()` for AI content
- Handles prompt construction and response processing

### `profile_service.py`
**Purpose**: Reusable character profile management

**Key Functions**:
- `list_profiles()`: Get all profiles
- `create_profile(data)`: Add new profile
- `update_profile(id, data)`: Edit profile
- `delete_profile(id)`: Remove profile

**Features**:
- Unique profile name constraints
- Template data validation
- Integration with character generation

### `story_service.py`
**Purpose**: Story and chapter management

**Key Functions**:
- `list_stories()`: Retrieve stories
- `create_from_template(...)`: Initialize and generate a story from a template
- `list_story_chapters(story_id)`: Get chapters
- `create_story_chapter(...)`: Add chapter
- `edit_story_chapter(...)`: Modify chapter
- `delete_existing_story(...)`: Remove story
- `build_full_story_markdown(chapters)`: Compile chapter bodies for reading/export/learning tools

**Relationships**:
- Manages story-template associations
- Handles chapter ordering
- Supports character assignments
- Logs object history for story operations
- Coordinates Chroma cleanup for deleted story/chapter memory

### `story_generation_service.py`
**Purpose**: LLM-powered story creation

**Key Functions**:
- `generate_story_chapters(story_id, progress_callback=None)`: Generate all chapters for a story
- `generate_story_chapter_body_and_summary(story_id, chapter_id, progress_callback=None)`: Generate one chapter body and summary

**LLM Workflow**:
- Constructs detailed prompts from templates
- Iterates through chapter generation
- Handles character integration
- Injects story memory into chapter prompts
- Aborts generation when a required body or summary LLM call fails
- Indexes chapter summaries and triggers fail-safe story-beat extraction

### `story_beat_service.py`
**Purpose**: Extract structured story-memory beats from chapter text.

**Key Functions**:
- `extract_story_beats(...)`: Calls the LLM with `prompts/story_beats.txt`
- `parse_story_beats_response(...)`: JSON-only parser with graceful failure
- `validate_story_beat(...)`: Normalizes and validates beat objects
- `safe_extract_save_and_index_story_beats(...)`: Best-effort extraction that never breaks chapter saving
- `index_story_beat(...)`: Adds beat records to Chroma

**Beat Types**:
`scene`, `transition`, `relationship_progression`, `emotional_shift`,
`revelation`, `unresolved_thread`, `time_jump`,
`world_or_setting_detail`, `character_state_change`.

### `story_memory_service.py` and `story_memory_indexing_service.py`
**Purpose**: Chroma-backed retrieval and rebuildable memory indexing.

**Key Functions**:
- `safe_search_memory(...)`: Safe Chroma search
- `safe_list_memory_items(...)`: Inspect persisted Chroma records
- `build_story_generation_memory(...)`: Retrieve and format prompt memory
- `rebuild_story_memory_index_from_sqlite()`: Rebuild Chroma from SQLite source data

**Memory Types**:
Stories, chapter summaries, characters, and story beats. The injected STORY
MEMORY prompt is grouped through `prompts/story_memory_section.txt`.

### `glossary_service.py`
**Purpose**: Generate learner glossaries from full stories or chapters.

**Key Functions**:
- `generate_glossary(...)`: Calls the LLM with `prompts/glossary.txt`
- `parse_glossary_response(...)`: Parses JSON glossary entries
- `glossary_entries_to_csv(...)`: Produces downloadable CSV
- `build_glossary_table(...)`: Formats rows for Streamlit display

See `docs/language_aids.md` for the end-to-end glossary workflow.

### `reading_comprehension_service.py`
**Purpose**: Generate reading comprehension questions from full stories or chapters.

**Key Functions**:
- `generate_reading_comprehension_questions(...)`: Calls the LLM with `prompts/reading_comprehension.txt`
- `parse_reading_comprehension_response(...)`: Parses JSON questions
- `reading_comprehension_to_csv(...)`: Produces two- or three-column CSV
- `build_reading_comprehension_table(...)`: Formats rows for Streamlit display

See `docs/language_aids.md` for the end-to-end reading comprehension workflow.

### `template_service.py`
**Purpose**: Story template CRUD operations

**Key Functions**:
- `list_templates()`: Get all templates
- `create_template(data)`: Add template with chapters
- `update_template(id, data)`: Edit template
- `delete_template(id)`: Remove template

**Features**:
- Chapter management within templates
- Template validation
- Usage tracking in stories

### `model_service.py`
**Purpose**: LLM model configuration

**Key Functions**:
- `list_models()`: Get available models
- `add_model(data)`: Register new model
- `update_model(id, data)`: Edit model
- `delete_model(id)`: Remove model
- `set_default_model(id)`: Mark as default

**Provider Support**:
- Gemini, Groq, OpenRouter integration
- Model capability descriptions
- Default model selection
- Sidebar default persistence to `.env` through `llm_defaults_service.py`

### `auth_service.py` and `admin_service.py`
**Purpose**: Google OIDC authentication and SQLite-backed authorization.

**Key Functions**:
- `require_login()`: Requires Google login and checks the authorized user table
- `current_user_is_administrator()`: Gates the Administration tab
- `list_authorized_users()`: Lists the whitelist for administrators
- `create_authorized_user(...)`, `edit_authorized_user(...)`, `delete_existing_authorized_user(...)`: Manage users and roles


### `sync_service.py`
**Purpose**: MongoDB synchronization (optional)

**Key Functions**:
- `sync_to_mongodb()`: Upload data to cloud
- `sync_from_mongodb()`: Download from cloud
- `get_sync_status()`: Check synchronization state

**Features**:
- Selective table synchronization
- Conflict resolution
- Metadata tracking

## Integration Points

### Database Layer
- Services and views import from the top-level `database` provider facade
- `DB_PROVIDER=sqlite` exports the existing SQLite repositories
- `DB_PROVIDER=mongodb` exports MongoDB Atlas repositories with matching function names
- Transaction management for complex operations
- Error handling for database constraints

### LLM Client
- `llm_client.generate_text()` for content generation
- Provider abstraction through `llm_providers.py`
- Logging via `llm_logging.py`
- Throttling via `llm_throttle.py`

### UI Layer
- Services called from `views/*.py` modules
- Streamlit session state management
- User feedback and error display

## Error Handling

### Exception Types
- `ValueError`: Invalid input data
- `RuntimeError`: LLM service failures
- `sqlite3.Error`: Database operation failures
- Custom exceptions for business logic violations

### Recovery Strategies
- Graceful degradation for LLM failures
- Transaction rollbacks for database errors
- User-friendly error messages
- Logging for debugging

## Testing

Services are tested through:
- **Unit Tests**: Individual function testing
- **Integration Tests**: Database and LLM interaction
- **Mock Objects**: Simulated external dependencies
- **Test Data**: Sample records for validation

## Performance Considerations

- **Batch Operations**: Efficient bulk data handling
- **Caching**: Session state for frequently accessed data
- **Lazy Loading**: On-demand data retrieval
- **Resource Limits**: LLM rate limiting and token management

## Future Enhancements

Potential service layer improvements:
- **Async Operations**: Non-blocking LLM calls
- **Service Interfaces**: Abstract base classes
- **Dependency Injection**: Configurable service dependencies
- **Event System**: Decoupled component communication
