from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.rag_service import search_memory, upsert_memory


def main():
    upsert_memory(
        "smoke_character_mira",
        (
            "Name: Mira\n"
            "Summary: A careful navigator who remembers every coastline."
        ),
        {"type": "character", "name": "Mira"},
    )
    upsert_memory(
        "smoke_chapter_harbor",
        (
            "Story ID: smoke\n"
            "Chapter number: 1\n"
            "Summary: The crew reaches the old harbor at dawn."
        ),
        {"type": "chapter_summary", "story_id": "smoke", "chapter_number": 1},
    )
    upsert_memory(
        "smoke_character_ren",
        "Name: Ren\nSummary: A reluctant archivist with a dry sense of humor.",
        {"type": "character", "name": "Ren"},
    )

    matches = search_memory("Who remembers every coastline?", n_results=3)

    print("RAG smoke test matches:")
    for match in matches:
        print(match)

    if not matches:
        raise SystemExit("Expected at least one RAG match.")


if __name__ == "__main__":
    main()
