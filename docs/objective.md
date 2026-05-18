# Objective

## Project Purpose

Story Builder is a hobby and learning project designed to create a Streamlit-based fiction/story creation application. The project serves two primary goals:

1. **Usable Application**: Provide a functional app for creating characters, reusable profiles, story templates, and generated stories.
2. **Learning Platform**: Serve as a platform for learning LLM-assisted development, LLM integration, storage design, MongoDB, local infrastructure, and eventually Kubernetes/Raspberry Pi deployment experiments.

## Design Philosophy

The codebase prioritizes changes that support learning, clarity, and architectural evolution over highly optimized production complexity. This means:

- Clear, readable code structure
- Incremental feature development
- Educational value in implementation choices
- Flexibility for experimentation

## Key Features

- Character generation and management
- Reusable character profiles
- Story templates with chapter structures
- LLM-powered story generation
- Optional story generation instructions, target language, and CEFR level
- Chroma-backed story memory using Chroma
- Structured story beats for continuity, including transitions, revelations, emotional shifts, and unresolved threads
- Glossary generation for full stories and individual chapters, with CSV download
- Reading comprehension question generation for full stories and individual chapters, with CSV download
- JSON import/export functionality
- Optional MongoDB backup sync
- Object history plus LLM call and failure history tracking
- Multiple LLM provider support (Gemini, Groq, OpenRouter)
- Database encryption capabilities
