"""Archetype YAML prompt loader for Peripatos Core."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml
from peripatos_core.exceptions import ConfigError
from peripatos_core.types import ArchetypeId

_DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent / "prompts" / "archetypes"


@dataclass
class ArchetypePrompt:
    archetype: str
    host_name: str
    guest_name: str
    system_prompt: str
    dialogue_prompt: str


class ArchetypeLoader:
    """Loads archetype YAML prompt files."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._dir = prompts_dir or _DEFAULT_PROMPTS_DIR

    def load(self, archetype: ArchetypeId | str) -> ArchetypePrompt:
        """Load an archetype prompt by ID. Raises ConfigError if missing or malformed."""
        archetype_str = archetype.value if isinstance(archetype, ArchetypeId) else archetype
        yaml_path = self._dir / f"{archetype_str}.yaml"
        if not yaml_path.exists():
            raise ConfigError(f"Archetype prompt file not found: {yaml_path}")
        try:
            with yaml_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Failed to parse archetype YAML {yaml_path}: {exc}") from exc

        if not isinstance(data, dict):
            raise ConfigError(f"Archetype YAML {yaml_path} must be a mapping")

        required = {"archetype", "host_name", "guest_name", "system_prompt", "dialogue_prompt"}
        missing = required - set(data.keys())
        if missing:
            raise ConfigError(f"Archetype YAML missing fields: {missing}")

        return ArchetypePrompt(
            archetype=data["archetype"],
            host_name=data["host_name"],
            guest_name=data["guest_name"],
            system_prompt=data["system_prompt"],
            dialogue_prompt=data["dialogue_prompt"],
        )

    def list_available(self) -> list[str]:
        """Return list of available archetype IDs."""
        return [p.stem for p in self._dir.glob("*.yaml")]
