"""Prompt loading utilities for Peripatos Core."""
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_react_system(
    archetype_prompt: str, title: str, origin: str, sections: str,
    language_instruction: str = "",
    target_turns: str = "",
) -> str:
    """Load and format the ReAct system prompt template."""
    template_path = _PROMPTS_DIR / "react_system.txt"
    with template_path.open("r", encoding="utf-8") as f:
        template = f.read()

    return template.format(
        archetype_system_prompt=archetype_prompt,
        paper_title=title,
        paper_origin=origin,
        section_overview=sections,
        language_instruction=language_instruction,
        target_turns=target_turns,
    )
