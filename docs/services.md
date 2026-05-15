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
- `create_story(data)`: Initialize story
- `get_story_chapters(story_id)`: Get chapters
- `update_story_chapter(id, data)`: Modify chapter
- `delete_story(id)`: Remove story

**Relationships**:
- Manages story-template associations
- Handles chapter ordering
- Supports character assignments

### `story_generation_service.py`
**Purpose**: LLM-powered story creation

**Key Functions**:
- `generate_story(story_data, template_data)`: Create complete story
- `generate_chapter(story_context, chapter_template)`: Generate individual chapters

**LLM Workflow**:
- Constructs detailed prompts from templates
- Iterates through chapter generation
- Handles character integration
- Manages generation parameters (temperature, model)

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
- Direct imports from `database.*` modules
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