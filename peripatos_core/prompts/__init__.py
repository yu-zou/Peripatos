"""Prompt loading utilities for Peripatos Core."""
import hashlib as _hashlib
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_react_system(
    archetype_prompt: str, title: str, origin: str, sections: str,
    language_instruction: str = "",
    target_turns: str = "",
    host_name: str = "Host",
    guest_name: str = "Guest",
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
        host_name=host_name,
        guest_name=guest_name,
    )


def prompts_version() -> str:
    """Stable short hash of all prompt templates + language instructions.

    Changes whenever any prompt file or LANGUAGE_INSTRUCTIONS entry changes,
    so the dialogue cache auto-invalidates on prompt edits.
    """
    from peripatos_core.config import LANGUAGE_INSTRUCTIONS

    hasher = _hashlib.sha256()
    for name in sorted(p.name for p in _PROMPTS_DIR.glob("*.txt")):
        hasher.update(name.encode("utf-8"))
        hasher.update((_PROMPTS_DIR / name).read_bytes())
    for lang in sorted(LANGUAGE_INSTRUCTIONS):
        hasher.update(lang.encode("utf-8"))
        hasher.update(LANGUAGE_INSTRUCTIONS[lang].encode("utf-8"))
    return hasher.hexdigest()[:12]
