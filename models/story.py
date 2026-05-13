from dataclasses import dataclass


@dataclass
class StoryTemplate:
    id: int | None
    template_name: str
    overview: str
    setting_background: str
    tone_style: str
    created_at: str | None = None


@dataclass
class StoryTemplateChapter:
    id: int | None
    template_id: int
    chapter_number: int
    chapter_description: str
    chapter_body: str
    chapter_summary: str


@dataclass
class Story:
    id: int | None
    story_name: str
    template_id: int | None
    overview: str
    setting_background: str
    tone_style: str
    male_characters: str
    female_characters: str
    created_at: str | None = None


@dataclass
class StoryChapter:
    id: int | None
    story_id: int
    chapter_number: int
    chapter_description: str
    chapter_body: str
    chapter_summary: str
