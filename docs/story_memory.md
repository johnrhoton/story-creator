# Story Memory and RAG

## Purpose

Story Memory helps generated chapters stay consistent with earlier story facts,
character state, relationship changes, unresolved threads, and chapter events.
It combines SQLite source data with a local Chroma vector index.

SQLite is the source of truth. Chroma is the retrieval index and can be rebuilt
from SQLite from the RAG tab.

## Main User Workflows

### During Story Generation

1. The user creates or regenerates a story chapter.
2. `services/story_generation_service.py` builds a chapter prompt.
3. Before the prompt is sent to the LLM, it calls
   `build_story_generation_memory(...)` in `services/rag_service.py`.
4. RAG searches Chroma for records relevant to the current chapter request.
5. Retrieved records are filtered so unrelated story-specific records do not
   leak into the current story.
6. The memory block is rendered through `prompts/story_memory_section.txt`.
7. The result is inserted into `{story_memory_section}` in:
   - `prompts/story_chapter.txt`
   - `prompts/story_chapter_zero.txt`

### In the RAG Tab

The RAG tab supports:
- Rebuilding the Chroma index from SQLite
- Searching memory
- Previewing the exact STORY MEMORY block that would be injected
- Inspecting indexed records grouped by object type
- Viewing, manually extracting, and searching story beats

## Indexed Memory Types

### Stories

Story records are indexed from SQLite stories. They include high-level metadata
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

1. The chapter body is saved to SQLite.
2. A chapter summary is generated and indexed.
3. `services/story_beat_service.py` calls the LLM with
   `prompts/story_beats.txt`.
4. The response must be JSON. The parser accepts standard JSON, fenced JSON, and
   bare JSON lists.
5. Valid beats are saved to SQLite in `story_beats`.
6. Beats are indexed in Chroma with IDs like:
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

## Persistence and Rebuilds

Chroma is persisted under:

```text
data/chroma_db
```

The current collection is named:

```text
story_memory
```

The index can be rebuilt from SQLite using the RAG tab. Rebuild counts include:
- Stories
- Chapter summaries
- Story beats
- Characters

Use rebuild after importing data, changing indexing behavior, or if the index
appears stale.

## Important Files

- `services/rag_service.py`: Chroma access, retrieval, filtering, and memory formatting
- `services/rag_indexing_service.py`: Rebuildable indexing from SQLite
- `services/story_beat_service.py`: Beat extraction, validation, persistence, and indexing
- `database/story_beats.py`: SQLite access for story beats
- `prompts/story_memory_section.txt`: STORY MEMORY prompt format
- `prompts/story_beats.txt`: Beat extraction prompt
- `views/rag_debug_view.py`: RAG UI

## Failure Behavior

- Chroma operations use safe wrappers where appropriate.
- Missing or failed RAG retrieval results in no STORY MEMORY block rather than a
  failed chapter generation.
- Failed beat extraction returns no beats and does not break normal story saving.
