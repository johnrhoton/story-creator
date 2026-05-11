from dataclasses import dataclass


@dataclass
class Character:
    id: int | None
    created_at: str | None
    profile_name: str | None
    name: str
    age: str
    gender: str
    physical_traits: str
    personality_traits: str
    notes: str
    prompt: str
    response: str
    summary: str | None = ""