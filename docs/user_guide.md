# User Guide

## Getting Started

1. **Installation**: Clone the repository and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **Running the App**:
   ```bash
   streamlit run app.py
   ```

3. **First Time Setup**:
   - The app will automatically run database migrations
   - Configure LLM settings in the sidebar
   - Seed LLM models if needed: `python scripts/seed_llm_models.py`

## Main Interface

The app uses a tab-based interface with the following sections:

### Characters Tab
- **View Characters**: Browse existing generated characters
- **Create Character**: Generate new characters using LLM
  - Select a profile as base (optional)
  - Provide character details or use random generation
  - LLM generates detailed character description
- **Edit Character**: Modify existing character details
- **Delete Character**: Remove characters (with confirmation)

### Profiles Tab
- **Create Profile**: Define reusable character archetypes
  - Profile name, gender, physical traits, personality traits, notes
- **View Profiles**: Browse and select profiles for character generation
- **Edit/Delete Profiles**: Manage existing profiles

### Templates Tab
- **Create Template**: Define story structures
  - Template name, overview, setting/background, tone/style
  - Add chapter descriptions
- **View Templates**: Browse available story templates
- **Use in Stories**: Templates serve as blueprints for story generation

### Stories Tab
- **Create Story**: Generate complete stories
  - Select a template
  - Choose male/female characters
  - Optionally provide additional instructions
  - Optionally choose target language and CEFR level
  - LLM generates story chapters based on template
- **View Stories**: Read generated stories with chapter navigation
- **Edit Chapters**: Modify individual chapter content
- **Glossary**: Generate a CSV glossary for a full story or a chapter
  - Choose number of entries (default 15)
  - Enter dictionary languages such as `German, Spanish`
  - Headwords are kept in the story language and translations are added per dictionary language
- **Reading Comprehension**: Generate CSV comprehension questions for a full story or chapter
  - Choose number of questions (default 15)
  - Optional question language adds a translated-question column

### Story Memory Tab
- **Rebuild Story Memory Index**: Rebuild story memory from the active database provider
- **Search Memory**: Search configured vector memory records
- **Preview STORY MEMORY**: See the exact memory block that would be injected into a chapter prompt
- **Inspect Index**: Browse persisted vector entries grouped by Stories, Chapter Summaries, Story Beats, and Characters
- **Story Beats**: View, extract, or search structured story-memory beats
- For an end-to-end explanation, see `docs/story_memory.md`.

### Language Aids Tab
- Open a standalone language-aids generator for a selected story or chapter
- Choose between Glossary and Reading comprehension
- Can be opened via URL/query parameters from story/chapter controls
- Useful as a browser-tab "pop-out" while keeping the story open elsewhere
- For glossary and reading comprehension details, see `docs/language_aids.md`.

### Models Tab
- **Configure LLM Models**: Add/edit available AI models
  - Provider (Gemini, Groq, OpenRouter)
  - Model name and best use description
  - Mark default models

### History Tab
- **Objects**: Browse CRUD history for Characters, Profiles, Templates, and Stories
- **LLM Calls**: Browse successful and failed AI interactions
- Filter history type without scrolling through unrelated sections

### Export/Import Tab
- **Export Data**: Download app data as JSON/YAML
  - Select records to export
  - Optional encryption
- **Import Data**: Upload and merge data from files
  - Supports JSON/YAML formats
  - Handles encrypted imports

### Administration Tab
- Visible only to users with the `Administrator` role
- Manage the authorized Google user whitelist
- Create, edit, and delete users with roles
- Review each user's last-updated timestamp and bound Google user ID

## LLM Configuration

### Sidebar Settings
- **Provider Selection**: Choose between Gemini, Groq, OpenRouter
- **Model Selection**: Pick from available models
- **Saved Defaults**: The last selected provider/model is saved to `.streamlit/secrets.toml` as `DEFAULT_LLM_PROVIDER` and `DEFAULT_LLM_MODEL`
- **Throttle Interval**: Optional delay between calls for the selected provider/model

### Database Encryption
- **Enable Encryption**: Protect sensitive data with password
- **Password Management**: Set/unlock database encryption
- **Export Security**: Encrypt exported data

## Tips and Best Practices

1. **Start with Profiles**: Create reusable profiles for consistent character generation
2. **Use Templates**: Define story structures before generating content
3. **Monitor Usage**: Check the History tab for API usage and costs
4. **Regular Backups**: Use Export/Import for data safety
5. **Experiment**: Try different models and settings for varied results
6. **Rebuild Story Memory After Imports**: Rebuild the Story Memory index after importing data or when memory looks stale

## Troubleshooting

- **LLM Errors**: Check API keys and model availability
- **Database Issues**: Run migrations manually: `python scripts/migrate.py`
- **Import Problems**: Ensure file format matches export format
- **Performance**: Monitor LLM call history for rate limiting
- **Story Memory Looks Empty**: Rebuild the index from the Story Memory tab; persisted source data remains in the active database provider
