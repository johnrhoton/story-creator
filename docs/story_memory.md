# Story Memory

## Purpose

Story Memory helps generated chapters stay consistent with earlier story facts,
character state, relationship changes, unresolved threads, and chapter events.
It combines persisted app data with a configurable vector index.

SQLite or MongoDB is the source of truth, depending on `DB_PROVIDER`. The vector
store is a retrieval index and can be rebuilt from the active database provider
from the Story Memory tab.

## Main User Workflows

### During Story Generation

1. The user creates or regenerates a story chapter.
2. `services/story_generation_service.py` builds a chapter prompt.
3. Before the prompt is sent to the LLM, it calls
   `build_story_generation_memory(...)` in `services/story_memory_service.py`.
4. Story Memory searches the configured vector provider for records relevant to
   the current chapter request.
5. Retrieved records are filtered so unrelated story-specific records do not
   leak into the current story.
6. The memory block is rendered through `prompts/story_memory_section.txt`.
7. The result is inserted into `{story_memory_section}` in:
   - `prompts/story_chapter.txt`
   - `prompts/story_chapter_zero.txt`

### In the Story Memory Tab

The Story Memory tab supports:
- Rebuilding the vector index from the active database provider
- Searching memory
- Previewing the exact STORY MEMORY block that would be injected
- Inspecting indexed records grouped by object type
- Viewing, manually extracting, and searching story beats

## Indexed Memory Types

### Stories

Story records are indexed from persisted stories. They include high-level metadata
such as story name, overview, setting/background, tone/style, optional language
settings, and assigned characters.

### Chapter Summaries

Chapter summaries are indexed after chapter generation or chapter editing.
They provide compact recent continuity for future chapters.

### Characters

Characters are indexed with names, profile information, traits, summaries, and
descriptive text. Characters without a story scope are marked as global and can
be retrieved for story prompts.

### Story Beats

Story beats are structured continuity records extracted from full chapter text.
They are designed to capture more than scenes. Beat types include:
- `scene`
- `transition`
- `relationship_progression`
- `emotional_shift`
- `revelation`
- `unresolved_thread`
- `time_jump`
- `world_or_setting_detail`
- `character_state_change`

Each beat can include title, characters, location, time span, summary,
continuity effect, unresolved threads, and search keywords.

## Story Beat Extraction

After a chapter is generated or updated:

1. The chapter body is saved through the active database provider.
2. A chapter summary is generated and indexed.
3. `services/story_beat_service.py` calls the LLM with
   `prompts/story_beats.txt`.
4. The response must be JSON. The parser accepts standard JSON, fenced JSON, and
   bare JSON lists.
5. Valid beats are saved through the active database provider in `story_beats`.
6. Beats are indexed in the configured vector provider with IDs like:
   `story_{story_id}_chapter_{chapter_number}_beat_{sequence_number}`.

Beat extraction is fail-safe. If extraction fails or returns invalid JSON, the
chapter generation/update still succeeds.

## Prompt Memory Formatting

`prompts/story_memory_section.txt` controls the visible prompt wording. It
contains sections such as:
- `[section]`
- `[characters]`
- `[recent_continuity]`
- `[relevant_story_beats]`
- `[unresolved_threads]`
- `[item]`

Python decides which records belong in which section. The template controls the
headings and item formatting shown to the LLM.

## Vector Providers

Story Memory uses a configurable vector provider. Set `VECTOR_PROVIDER` to:
- `none`: Disable RAG retrieval and indexing. Story generation continues without injected memory.
- `chroma`: Use the existing local Chroma persistence under `data/chroma_db`.
- `mongodb_vector`: Store memory records and embeddings in MongoDB Atlas and
  retrieve with Atlas Vector Search.

All vector providers that embed text use the same model:

```text
all-MiniLM-L6-v2
```

The default vector collection is:

```text
story_memory
```

For MongoDB Atlas Vector Search, create an Atlas vector index on the
`embedding` field in the configured collection. The app uses the index named by
`VECTOR_INDEX_NAME`, defaulting to `story_memory_vector_index`. The embedding
dimension for `all-MiniLM-L6-v2` is 384.

## Persistence and Rebuilds

The index can be rebuilt from the active database provider using the Story
Memory tab. Rebuild counts include:
- Stories
- Chapter summaries
- Story beats
- Characters

Use rebuild after importing data, changing indexing behavior, or if the index
appears stale.

## Important Files

- `services/vector_store.py`: Vector store abstraction and Chroma/MongoDB providers
- `services/story_memory_service.py`: Retrieval, filtering, and memory formatting
- `services/story_memory_indexing_service.py`: Rebuildable indexing from the active database provider
- `services/story_beat_service.py`: Beat extraction, validation, persistence, and indexing
- `database/story_beats.py` and MongoDB repositories: story-beat persistence
- `prompts/story_memory_section.txt`: STORY MEMORY prompt format
- `prompts/story_beats.txt`: Beat extraction prompt
- `views/story_memory_view.py`: Story Memory UI

## Failure Behavior

- Vector-store operations use safe wrappers where appropriate.
- Missing or failed Story Memory retrieval results in no STORY MEMORY block rather than a
  failed chapter generation.
- Failed beat extraction returns no beats and does not break normal story saving.
