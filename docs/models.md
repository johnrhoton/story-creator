# Models Technical Description

## Overview

Story Builder does not use traditional object-relational mapping (ORM) models or separate model classes. Instead, it employs a direct database access pattern where data operations are handled through dedicated database modules.

## Architecture Approach

### No Separate Model Layer

Unlike frameworks like Django or SQLAlchemy, this project maintains simplicity by:

- **Direct SQL Operations**: Database interactions use raw SQL queries
- **Dictionary-Based Data**: Records returned as Python dictionaries
- **Service Layer Logic**: Business rules implemented in service modules
- **No ORM Overhead**: Reduced complexity for learning purposes

### Data Representation

Data is represented as:
- **Dictionaries**: Query results as `dict` objects
- **Named Tuples**: Occasional use for structured data
- **JSON Serialization**: For import/export operations
- **String Formatting**: For display in UI components

## Database Modules as Pseudo-Models

Each database table has a corresponding module that serves as a data access layer:

### `database/characters.py`
- `get_characters()`: Retrieve all characters
- `save_character(data)`: Insert new character
- `update_character(id, data)`: Modify existing character
- `delete_character(id)`: Remove character

### `database/profiles.py`
- `get_profiles()`: List all profiles
- `add_profile(...)`: Create profile
- `update_profile(...)`: Edit profile
- `delete_profile(...)`: Remove profile

### `database/stories.py`
- `get_stories()`: Retrieve stories
- `add_story(...)` / `create_story_from_template(...)`: Create stories
- `get_story_chapters(story_id)`: Get chapters for story
- `add_story_chapter(...)`: Add chapter
- `update_story_chapter(...)`: Edit chapter

### `database/llm_calls.py`
- `save_llm_call(...)`: Record successful interaction
- `save_failed_llm_call(...)`: Record failed interaction
- `get_llm_calls()`: Retrieve call history

## Data Validation

Validation occurs at the service layer rather than model layer:

- **Service Methods**: Input validation in `services/*.py`
- **UI Validation**: Basic checks in Streamlit forms
- **Database Constraints**: Foreign keys and unique constraints
- **Import Validation**: Data integrity checks during import

## Serialization

### Export Format
```json
{
  "characters": [...],
  "profiles": [...],
  "stories": [...],
  "story_chapters": [...],
  "story_beats": [...],
  "llm_calls": [...]
}
```

### Record Structure
Each record includes:
- Primary key (`id`)
- Timestamps (`created_at`)
- Data fields (varies by table)
- Foreign key references

## Prompt and Memory Data

The project also uses text-based prompt templates rather than model classes for
generation behavior. Prompt templates live in `prompts/` and are loaded by
`prompts.py`. story memory records are represented as Chroma documents plus
metadata dictionaries. SQLite remains the source of truth for rebuildable memory
such as story beats.

## Advantages of Current Approach

1. **Simplicity**: Easy to understand for learning
2. **Direct Control**: Full SQL query visibility
3. **Performance**: Minimal abstraction overhead
4. **Flexibility**: Easy schema modifications
5. **Debugging**: Transparent database operations

## Potential Future Evolution

While the current approach serves learning goals, future enhancements could include:

- **Pydantic Models**: Type validation and serialization
- **SQLAlchemy Integration**: ORM for complex queries
- **Data Classes**: Python 3.7+ dataclass models
- **Repository Pattern**: Abstracted data access layer

## Type Safety

Current implementation relies on:
- **Runtime Checks**: Dictionary key validation
- **SQL Constraints**: Database-level integrity
- **Manual Testing**: Unit tests for data operations
- **Documentation**: Clear field specifications

## Migration Considerations

When evolving to a model-based approach:
- Maintain backward compatibility
- Gradual refactoring of database modules
- Preserve existing API contracts
- Update import/export functionality
