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
  - LLM generates story chapters based on template
- **View Stories**: Read generated stories with chapter navigation
- **Edit Chapters**: Modify individual chapter content

### Models Tab
- **Configure LLM Models**: Add/edit available AI models
  - Provider (Gemini, Groq, OpenRouter)
  - Model name and best use description
  - Mark default models

### History Tab
- **View LLM Calls**: Browse all AI interactions
  - Successful and failed calls
  - Request/response details
  - Error information for debugging

### Export/Import Tab
- **Export Data**: Download app data as JSON/YAML
  - Select records to export
  - Optional encryption
- **Import Data**: Upload and merge data from files
  - Supports JSON/YAML formats
  - Handles encrypted imports

## LLM Configuration

### Sidebar Settings
- **Provider Selection**: Choose between Gemini, Groq, OpenRouter
- **API Key**: Enter your API key for the selected provider
- **Model Selection**: Pick from available models
- **Temperature**: Control creativity (0.0-1.0)
- **Max Tokens**: Limit response length

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

## Troubleshooting

- **LLM Errors**: Check API keys and model availability
- **Database Issues**: Run migrations manually: `python scripts/migrate.py`
- **Import Problems**: Ensure file format matches export format
- **Performance**: Monitor LLM call history for rate limiting