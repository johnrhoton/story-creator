# Language Aids

## Purpose

Language aids are optional tools for turning generated stories or chapters into
learning material. They currently include:
- Glossaries
- Reading comprehension questions

Both can be generated for an individual chapter or for the full story. Both are
LLM-powered, displayed in the UI, and downloadable as CSV.

## Glossary Workflow

### User Flow

1. Open a story or chapter in the Stories tab, or open the standalone Glossary tab.
2. Choose the number of glossary entries. The default is 15.
3. Enter one or more dictionary languages, such as `German, Spanish`.
4. Click Create glossary.
5. Review the generated table.
6. Download the result as CSV.

### Prompt Behavior

The app sends the selected story/chapter text to the LLM using
`prompts/glossary.txt`.

The prompt asks for:
- The most difficult or least common words in the passage
- Entries in order of first appearance
- Lemma/headword forms, not inflected forms
- Headwords in the original story language
- Translations in each requested dictionary language
- JSON-only output

Example concept:

```text
mirror, der Spiegel, el espejo
break, brechen/zerbrechen, romper
```

For a non-English story, the headwords should remain in the story language.
The story language is passed from the story's optional Language field when
available.

### Output

The CSV columns are:
- `headword`
- one column per dictionary language

## Reading Comprehension Workflow

### User Flow

1. Open a story or chapter in the Stories tab.
2. Choose the number of questions. The default is 15.
3. Optionally enter an interrogative language.
4. Click Create questions.
5. Review the generated table.
6. Download the result as CSV.

### Prompt Behavior

The app sends the selected story/chapter text to the LLM using
`prompts/reading_comprehension.txt`.

The prompt asks for:
- Questions about important events, motivations, relationships, revealed
  information, and consequences
- Questions and answers in the original textual language
- Optional translated questions in the interrogative language
- JSON-only output

### Output

If no interrogative language is supplied, the CSV columns are:
- `question`
- `answer`

If an interrogative language is supplied, the CSV columns are:
- `question`
- `answer`
- `translated_question`

## Standalone Glossary Tab

The Glossary tab can be opened directly or from story/chapter controls. It can
serve as a browser-tab pop-out while the Stories tab remains open elsewhere.

Example URLs:

```text
?view=Glossary&story_id=7
?view=Glossary&story_id=7&chapter_number=3
```

## Important Files

- `prompts/glossary.txt`: Glossary prompt
- `prompts/reading_comprehension.txt`: Reading comprehension prompt
- `services/glossary_service.py`: Glossary generation, parsing, table formatting, CSV export
- `services/reading_comprehension_service.py`: Question generation, parsing, table formatting, CSV export
- `views/stories_view.py`: Embedded story/chapter controls
- `views/glossary_view.py`: Standalone glossary page

## Storage

Language aids are generated on demand and downloaded as CSV. They are not
currently stored in SQLite.

LLM calls are still logged in the normal LLM history tables.
