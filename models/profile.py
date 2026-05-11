from dataclasses import dataclass


@dataclass
class Profile:
    profile_name: str
    name: str
    age: str
    gender: str
    physical_traits: str
    personality_traits: str
    notes: str