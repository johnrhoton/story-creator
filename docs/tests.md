# Tests Technical Description

## Overview

Story Builder uses Python's built-in `unittest` framework for regression testing. Tests focus on critical functionality, data integrity, and integration points.

## Test Structure

### Test Organization
- **Location**: `tests/` directory
- **Naming**: `test_*.py` files
- **Framework**: `unittest.TestCase` base class
- **Execution**: `python -m unittest discover tests/`

### Test Categories

#### Unit Tests
- Individual function testing
- Mock external dependencies
- Fast execution, isolated logic

#### Integration Tests
- Database operation testing
- LLM client integration
- End-to-end workflow validation

#### Data Tests
- Import/export functionality
- Encryption/decryption
- Schema migration validation

## Test Files

### `test_database_behaviour.py`
**Purpose**: Core database operations and integrity

**Test Cases**:
- Character CRUD operations
- Profile management
- Story and chapter handling
- LLM call logging
- Import/export round-trip testing
- Encryption functionality

**Key Features**:
- Temporary database creation
- Test data isolation
- Schema validation
- Foreign key constraint testing

### `test_database_encryption.py`
**Purpose**: Encryption feature validation

**Test Cases**:
- Password-based encryption/decryption
- Encrypted field identification
- Export with encryption
- Database unlock/lock functionality

**Security Testing**:
- Key derivation validation
- Cipher correctness
- Error handling for invalid passwords

### `test_export_crypto.py`
**Purpose**: Export encryption mechanisms

**Test Cases**:
- Encrypted export generation
- Decryption validation
- Key management
- Format compatibility

### `test_llm_helpers.py`
**Purpose**: LLM integration utilities

**Test Cases**:
- Prompt construction
- Response parsing
- Error handling
- Rate limiting logic

### `test_auth_service.py`
**Purpose**: Authentication helper behavior.

**Test Cases**:
- Named Google provider selection for Streamlit OIDC
- Default provider fallback

### `test_database_provider.py`
**Purpose**: Database provider configuration and MongoDB export surface.

**Test Cases**:
- `database.provider` / legacy `DB_PROVIDER` defaults and validation
- Mongo URI lookup from environment
- MongoDB provider facade exports expected repository functions
- `rag.provider` / legacy `VECTOR_PROVIDER` defaults and validation

### `test_vector_store.py`
**Purpose**: Vector store provider behavior.

**Test Cases**:
- Disabled vector provider no-op behavior
- MongoDB Atlas Vector Search record shape and pipeline construction
- Metadata filter conversion

### `test_story_service.py`
**Purpose**: Story generation workflows

**Test Cases**:
- Story creation from templates
- Chapter generation
- Character integration
- Template validation
- Progress reporting and abort-on-failed-LLM behavior

### `test_story_memory_helpers.py` and `test_story_memory_generation.py`
**Purpose**: Story Memory helper behavior

**Test Cases**:
- Metadata cleaning
- Memory grouping
- Rebuild counts by category
- Story-memory prompt injection
- Filtering to avoid unrelated story memory

### `test_story_beats.py`
**Purpose**: Story beat extraction and indexing helpers

**Test Cases**:
- Valid and invalid JSON parsing
- Beat validation
- Vector indexing text and metadata
- Generation memory includes story beats
- Extraction failures do not break generation

### `test_glossary_service.py`
**Purpose**: Glossary generation helpers

**Test Cases**:
- Prompt construction
- JSON response parsing
- CSV output
- Glossary source selection and pop-out URL helpers

### `test_reading_comprehension_service.py`
**Purpose**: Reading comprehension question helpers

**Test Cases**:
- Prompt construction
- JSON response parsing
- Optional translated-question column
- CSV and table output

### `test_ui_helpers.py`
**Purpose**: UI utility functions

**Test Cases**:
- Data formatting
- Display logic
- Input validation
- Streamlit integration

### `test_bulk_helpers.py`
**Purpose**: Bulk operation functionality

**Test Cases**:
- Mass data operations
- Performance validation
- Error recovery
- Resource management

### `test_common_names.py`
**Purpose**: Name database operations

**Test Cases**:
- Name seeding
- Random selection
- Gender filtering
- Database integrity

## Testing Patterns

### Test Setup
```python
class TestDatabaseBehaviour(unittest.TestCase):
    def setUp(self):
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp()
        # Initialize test data
        
    def tearDown(self):
        # Clean up test database
        os.close(self.db_fd)
        os.unlink(self.db_path)
```

### Mock Usage
- **LLM Calls**: Mock `llm_client.generate_text()`
- **Database**: Use temporary files for isolation
- **External APIs**: Simulate network responses

### Assertion Patterns
- **Data Equality**: `self.assertEqual(actual, expected)`
- **Exception Testing**: `with self.assertRaises(ExceptionType):`
- **Database State**: Query and verify record counts
- **JSON Validation**: Parse and check structure

## Test Data Management

### Fixtures
- Pre-defined test records
- Sample characters, profiles, stories
- Mock LLM responses
- Edge case data sets

### Data Isolation
- Temporary database files
- Unique identifiers for test records
- Cleanup after each test
- No shared state between tests

## Continuous Integration

### Automated Testing
- Run tests on code changes
- Pre-commit hooks
- CI/CD pipeline integration
- Coverage reporting

### Test Coverage Goals
- Core database operations: 90%+
- Service layer logic: 80%+
- UI helpers: 70%+
- Integration points: 85%+

## Test Maintenance

### Updating Tests
- Schema changes require test updates
- New features need corresponding tests
- Refactor tests with code changes
- Deprecate obsolete test cases

### Debugging Tests
- Verbose output for failures
- Database inspection tools
- LLM response logging
- Step-through debugging

## Performance Testing

### Benchmarks
- Database operation timing
- LLM call latency
- Memory usage monitoring
- Bulk operation performance

### Load Testing
- Concurrent user simulation
- Database connection pooling
- Resource utilization tracking

## Future Test Enhancements

Potential improvements:
- **Pytest Migration**: More expressive testing framework
- **Property-Based Testing**: Hypothesis for edge cases
- **UI Testing**: Selenium/Playwright for Streamlit
- **Load Testing**: Locust for performance validation
- **Coverage Tools**: Detailed coverage reporting
- **Test Parallelization**: Faster execution
- **Mock Libraries**: Advanced mocking with responses

## Quality Assurance

Tests ensure:
- **Data Integrity**: No corruption during operations
- **API Compatibility**: External service integration
- **User Workflows**: End-to-end functionality
- **Error Handling**: Graceful failure management
- **Performance**: Acceptable operation speeds
- **Security**: Encryption and access control
