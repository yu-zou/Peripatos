"""Dialogue generator — converts parsed paper text into a DialogueScript."""
from __future__ import annotations
import json
import logging
import peripatos_core.archetypes as archetypes
from peripatos_core.exceptions import LLMError
from peripatos_core.providers.llm import LLMProvider
from peripatos_core.types import DialogueScript, DialogueTurn

logger = logging.getLogger(__name__)

# Maximum characters of paper content to send to LLM (avoid token overflow)
MAX_PAPER_CHARS = 12_000


class DialogueGenerator:
    """Generates a Socratic dialogue from paper text using an LLM."""

    def __init__(
        self,
        llm: LLMProvider,
        archetype_loader: archetypes.ArchetypeLoader | None = None,
    ) -> None:
        self._llm = llm
        self._loader = archetype_loader or archetypes.ArchetypeLoader()

    def generate(
        self,
        paper_content: str,
        archetype: archetypes.ArchetypeId | str = archetypes.ArchetypeId.PEER,
        title: str = "Untitled Paper",
    ) -> DialogueScript:
        """Generate a dialogue script from paper content.

        Args:
            paper_content: Markdown or plain text of the paper.
            archetype: Which archetype to use for the dialogue style.
            title: Paper title (used as fallback episode title).

        Returns:
            DialogueScript with turns populated.
        """
        archetype_id = archetypes.ArchetypeId(archetype) if isinstance(archetype, str) else archetype
        prompt_data = self._loader.load(archetype_id)

        # Truncate paper content to avoid token overflow
        truncated = paper_content[:MAX_PAPER_CHARS]
        if len(paper_content) > MAX_PAPER_CHARS:
            logger.warning(
                "Paper content truncated from %d to %d chars",
                len(paper_content),
                MAX_PAPER_CHARS,
            )

        user_prompt = prompt_data.dialogue_prompt.format(paper_content=truncated)

        logger.debug("Calling LLM for dialogue generation (archetype=%s)", archetype_id.value)
        raw_response = self._llm.complete(
            system_prompt=prompt_data.system_prompt,
            user_prompt=user_prompt,
        )

        return self._parse_response(raw_response, title, archetype_id)

    def _parse_response(
        self,
        raw: str,
        title: str,
        archetype: archetypes.ArchetypeId,
    ) -> DialogueScript:
        """Parse LLM JSON response into a DialogueScript."""
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON: {exc}\nRaw: {raw[:200]}") from exc

        episode_title = data.get("title", title)
        turns_data = data.get("turns", [])
        if not isinstance(turns_data, list):
            raise LLMError("LLM response 'turns' is not a list")

        turns = []
        for i, turn in enumerate(turns_data):
            if not isinstance(turn, dict):
                raise LLMError(f"Turn {i} is not a dict: {turn}")
            speaker = turn.get("speaker", "Unknown")
            text = turn.get("text", "")
            turns.append(DialogueTurn(speaker=speaker, text=text, archetype=archetype))

        return DialogueScript(title=episode_title, turns=turns)
