# Database Technical Description

## Overview

Story Builder uses SQLite as its primary database for local data persistence. The database design supports the core functionality of character generation, story creation, and LLM interaction tracking.

## Database Engine

- **Technology**: SQLite 3
- **File**: `story_builder.db` (created in project root)
- **Connection**: Single-writer, multi-reader concurrent access
- **Migrations**: Automatic schema updates on application startup

## Schema Design

### Core Tables

#### `characters`
Stores generated character data:
- `id`: Primary key (auto-increment)
- `created_at`: Timestamp
- `profile_name`: Reference to base profile (optional)
- `name`, `age`, `gender`: Basic demographics
- `physical_traits`, `personality_traits`, `notes`: Descriptive fields
- `prompt`: LLM generation prompt
- `response`: Raw LLM response
- `summary`: Processed character summary

#### `profiles`
Reusable character archetypes:
- `id`: Primary key
- `profile_name`: Unique identifier
- `gender`, `physical_traits`, `personality_traits`, `notes`: Template data

#### `common_names`
Pre-seeded name database for random generation:
- `id`: Primary key
- `sequence_number`: Ordering for randomization
- `gender`: Male/Female categorization
- `name`: Name string

### Story Management

#### `story_templates`
Story structure blueprints:
- `id`: Primary key
- `created_at`: Timestamp
- `template_name`: Unique name
- `overview`, `setting_background`, `tone_style`: Template metadata

#### `story_template_chapters`
Chapter outlines within templates:
- `id`: Primary key
- `template_id`: Foreign key to story_templates
- `chapter_number`: Ordering
- `chapter_description`: Chapter content guide

#### `stories`
Generated story instances:
- `id`: Primary key
- `created_at`: Timestamp
- `story_name`: Unique title
- `template_id`: Reference to template (optional)
- `overview`, `setting_background`, `tone_style`: Story metadata
- `male_characters`, `female_characters`: Character assignments

#### `story_chapters`
Individual story chapters:
- `id`: Primary key
- `story_id`: Foreign key to stories
- `chapter_number`: Ordering
- `chapter_description`: Chapter outline
- `chapter_body`: Generated content
- `chapter_summary`: Chapter summary

### LLM Integration

#### `llm_calls`
Successful AI interactions:
- `id`: Primary key
- `created_at`: Timestamp
- `provider`: AI service (Gemini, Groq, OpenRouter)
- `model`: Specific model used
- `prompt`: Input text
- `response`: AI output

#### `failed_llm_calls`
Error tracking for debugging:
- `id`: Primary key
- `created_at`: Timestamp
- `provider`, `model`: Same as llm_calls
- `prompt`, `response`: Request data
- `error_type`, `error_codes`, `error_message`, `error_details`: Error information

#### `llm_models`
Available AI models configuration:
- `id`: Primary key
- `provider`: Service provider
- `model`: Model identifier
- `best_use`: Usage description
- `is_default`: Boolean flag for default selection

### Synchronization

#### `sync_metadata`
MongoDB sync state tracking:
- `key`: Metadata key (PRIMARY KEY)
- `value`: Associated value

## Data Access Layer

### Connection Management (`database/connection.py`)
- Singleton connection pattern
- Automatic database file creation
- Connection pooling considerations

### Table Operations
Each table has dedicated module:
- `characters.py`: Character CRUD operations
- `profiles.py`: Profile management
- `stories.py`: Story and chapter handling
- `llm_calls.py`: Interaction logging
- `llm_models.py`: Model configuration

### Import/Export (`database/import_export.py`)
- JSON/YAML serialization
- Selective record export
- Data validation on import
- Foreign key relationship preservation

## Security Features

### Encryption (`database/db_encryption.py`)
- Field-level encryption for sensitive data
- AES encryption with user-provided password
- Encrypted value prefixing for identification
- Password-based key derivation

### Key Management
- Runtime password unlocking
- Encrypted export support
- Secure key storage (not persisted)

## Migration System (`database/migrations.py`)

- Version-based schema updates
- Automatic execution on startup
- Backward compatibility maintenance
- Migration logging and error handling

## Performance Considerations

- SQLite limitations: Single-writer concurrency
- Indexing strategy: Primary keys and unique constraints
- Query optimization: Efficient JOIN operations
- Memory usage: In-memory operations where possible

## Backup and Recovery

- Export functionality for full data backup
- JSON/YAML format compatibility
- Incremental sync via MongoDB (optional)
- Data integrity validation on import

## Future Enhancements

- Potential migration to PostgreSQL for multi-user scenarios
- Advanced indexing for large datasets
- Query optimization for complex story searches
- Database sharding considerations for scaling