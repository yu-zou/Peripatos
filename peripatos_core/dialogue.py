"""Dialogue generator — converts parsed paper text into a DialogueScript."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

from peripatos_core.archetypes import ArchetypeLoader
from peripatos_core.config import Settings, get_language_instruction
from peripatos_core.prompts import load_react_system
from peripatos_core.providers.llm import LLMProvider
from peripatos_core.rag.chunker import chunk_text
from peripatos_core.rag.embedder import Embedder
from peripatos_core.rag.vector_store import VectorStore
from peripatos_core.types import (
    ArchetypeId, Chapter, DialogueScript, DialogueTurn, PaperMetadata,
    _calculate_target_turns,
)

_logger = logging.getLogger(__name__)

_MAX_PARSE_RETRIES = 2
_MIN_CHAPTERS = 3
_MAX_CHAPTERS = 7
_MIN_QUESTIONS = 2
_MAX_QUESTIONS = 5
_MAX_TITLE_LEN = 80

_FALLBACK_CHAPTERS: list[dict] = [
    {"title": "Introduction", "questions": ["What is the paper's main contribution?"]},
    {"title": "Background", "questions": ["What prior work does this build on?"]},
    {"title": "Methodology", "questions": ["How does the proposed approach work?"]},
    {"title": "Results", "questions": ["What were the key findings?"]},
    {"title": "Outlook", "questions": ["What are the limitations and future work?"]},
]

_LATEX_PATTERNS = re.compile(
    r'\$[^$]+\$|\$\$[^$]+\$\$|'
    r'\\frac|\\sum|\\alpha|\\beta|\\gamma|\\delta|\\epsilon|\\lambda|\\mu|\\sigma|\\omega|'
    r'\\int|\\prod|\\partial|\\nabla|\\sqrt|\\text'
)


def _contains_latex(text: str) -> bool:
    """Return True if text contains LaTeX notation."""
    return bool(_LATEX_PATTERNS.search(text))


# Phase C prompt sections loaded once at module import.
_SYNTHESIS_RAW = (Path(__file__).parent / "prompts" / "synthesis.txt").read_text()
_sections = _SYNTHESIS_RAW.split("# --- LaTeX Conversion ---")
_TRANSITION_PROMPT = _sections[0].replace("# --- Transition Task ---", "").strip()
_latex_part = _sections[1] if len(_sections) > 1 else _SYNTHESIS_RAW
_LATEX_PROMPT = ("# --- LaTeX Conversion ---" + _latex_part).strip()

_TRANSITION_TEMPLATE = _TRANSITION_PROMPT

for _tmpl, _keys in [
    (_TRANSITION_TEMPLATE, ("{covered_summary}", "{next_chapter_title}")),
    (_LATEX_PROMPT, ("{turn_text}",)),
]:
    for _k in _keys:
        if _k not in _tmpl:
            raise ValueError(f"Prompt template missing placeholder: {_k}")


def _parse_phase_a_output(raw_output: str) -> list[dict]:
    """Parse and validate Phase A LLM output into a list of chapter dicts.

    Each dict has keys: 'title' (str, ≤80 chars), 'questions' (list[str], 2-5 items).
    Returns 5-chapter fallback on unrecoverable parse failure.
    """
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        _logger.warning("Phase A output is not valid JSON")
        return _FALLBACK_CHAPTERS

    chapters = data.get("chapters", [])
    if not isinstance(chapters, list):
        _logger.warning("Phase A output 'chapters' is not a list")
        return _FALLBACK_CHAPTERS

    if not (_MIN_CHAPTERS <= len(chapters) <= _MAX_CHAPTERS):
        _logger.warning(
            "Phase A produced %d chapters (expected %d-%d)",
            len(chapters), _MIN_CHAPTERS, _MAX_CHAPTERS,
        )
        return _FALLBACK_CHAPTERS

    validated = []
    for i, ch in enumerate(chapters):
        title = ch.get("title", "")
        questions = ch.get("questions", [])
        if not isinstance(title, str) or not title.strip() or len(title) > _MAX_TITLE_LEN:
            _logger.warning("Chapter %d has invalid title", i)
            return _FALLBACK_CHAPTERS
        if not isinstance(questions, list) or not (_MIN_QUESTIONS <= len(questions) <= _MAX_QUESTIONS):
            _logger.warning("Chapter %d has invalid questions count: %d", i, len(questions))
            return _FALLBACK_CHAPTERS
        if not all(isinstance(q, str) and q.strip() for q in questions):
            _logger.warning("Chapter %d has non-string or empty questions", i)
            return _FALLBACK_CHAPTERS
        validated.append({"title": title.strip(), "questions": [q.strip() for q in questions]})

    return validated


class DialogueGenerator:
    """Generates a Socratic dialogue from paper text using the ReAct RAG agent."""

    def __init__(self, llm: LLMProvider, settings: Settings | None = None) -> None:
        self._llm = llm
        self._settings = settings or Settings()
        self._loader = ArchetypeLoader()

    @staticmethod
    def _parse_turns_json(raw: str, archetype: ArchetypeId) -> list[DialogueTurn]:
        """Parse LLM JSON response into list[DialogueTurn].

        Returns empty list on parse failure.
        """
        try:
            data = json.loads(raw)
            if not isinstance(data, list):
                _logger.warning("_parse_turns_json: expected JSON array, got %s", type(data).__name__)
                return []
            turns = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                speaker = str(item.get("speaker", "Host"))
                text = item.get("text", "")
                if not text or not isinstance(text, str):
                    continue
                turns.append(DialogueTurn(speaker=speaker, text=text, archetype=archetype))
            return turns
        except (json.JSONDecodeError, TypeError, AttributeError) as exc:
            _logger.warning("_parse_turns_json: parse failed: %s", exc)
            return []

    def _run_phase_a(
        self,
        archetype_system_prompt: str,
        title: str,
        origin: str,
        section_overview: str,
    ) -> list[dict]:
        """Run Phase A: plan chapters and questions. Returns validated chapter list."""
        prompt_template = (Path(__file__).parent / "prompts" / "host_questions.txt").read_text()
        language_instruction = get_language_instruction(self._settings.defaults.language)
        user_prompt = (
            prompt_template
            .replace("{archetype_system_prompt}", archetype_system_prompt)
            .replace("{paper_title}", title)
            .replace("{paper_origin}", origin)
            .replace("{section_overview}", section_overview)
            .replace("{language_instruction}", language_instruction)
        )

        total_attempts = 1 + _MAX_PARSE_RETRIES  # 1 initial + 2 retries = 3
        for attempt in range(total_attempts):
            raw = self._llm.complete(
                system_prompt="You are a podcast host planning interview chapters.",
                user_prompt=user_prompt,
            )
            chapters = _parse_phase_a_output(raw)
            if chapters is not _FALLBACK_CHAPTERS:
                return chapters
            if attempt < _MAX_PARSE_RETRIES:
                _logger.warning(
                    "Phase A parse failed (attempt %d/%d), retrying LLM",
                    attempt + 1, total_attempts,
                )

        _logger.warning("Phase A exhausted %d attempts, using fallback", total_attempts)
        return _FALLBACK_CHAPTERS

    def _run_phase_c(
        self,
        chapters: list[Chapter],
    ) -> list[Chapter]:
        """Phase C: generate transitions and convert LaTeX.

        For each chapter i (1..N-1): generate transition_in_text bridging from
        the previous chapter. For each turn containing LaTeX: convert to spoken
        English.
        """
        for i in range(1, len(chapters)):
            prev = chapters[i - 1]
            curr = chapters[i]
            covered = prev.turns[0].text[:100] if prev.turns else "(unknown)"
            user_prompt = _TRANSITION_TEMPLATE.format(
                covered_summary=covered,
                next_chapter_title=curr.title,
            )
            raw = self._llm.complete(
                system_prompt="You are a podcast host creating natural transitions between chapters.",
                user_prompt=user_prompt,
            )
            transition = raw.strip().strip('"').strip("'")
            if len(transition) > 200:
                transition = transition[:197] + "..."
            curr.transition_in_text = transition

        for chapter in chapters:
            for turn in chapter.turns:
                if _contains_latex(turn.text):
                    user_prompt = _LATEX_PROMPT.format(turn_text=turn.text)
                    raw = self._llm.complete(
                        system_prompt="You are an expert at converting mathematical notation to spoken English. Output ONLY the converted text.",
                        user_prompt=user_prompt,
                    )
                    turn.text = raw.strip().strip('"').strip("'")

        return chapters

    def generate(
        self,
        paper_content: str,
        archetype: ArchetypeId | str = ArchetypeId.PEER,
        title: str = "Untitled Paper",
        metadata: PaperMetadata | None = None,
    ) -> DialogueScript:
        """Generate a chaptered dialogue script via three-phase pipeline."""
        from peripatos_core.rag.agent import run_agent

        archetype_id = ArchetypeId(archetype) if isinstance(archetype, str) else archetype
        prompt_data = self._loader.load(archetype_id)
        rag = self._settings.rag
        cache_dir = (
            Path(rag.cache_dir)
            if rag.cache_dir
            else Path.home() / ".cache" / "peripatos" / "rag"
        )

        content_hash = hashlib.sha256(paper_content.encode()).hexdigest()

        embedder = Embedder(
            base_url=self._settings.llm.base_url,
            api_key=self._settings.llm.api_key,
            model=rag.embedding_model,
            provider=rag.provider,
        )
        store = VectorStore(cache_dir=cache_dir, content_hash=content_hash)
        if not store.has_cache():
            chunks = chunk_text(paper_content, chunk_size=rag.chunk_size, overlap=rag.chunk_overlap)
            texts = [chunk.text for chunk in chunks]
            embeddings = embedder.embed(texts)
            store.build(chunks, embeddings)
        else:
            store.load()

        sections_list = store.list_sections()
        seen: dict[str, int] = {}
        for chunk_id, hint in sections_list:
            if hint not in seen:
                seen[hint] = chunk_id
        deduped = list(seen.items())[:20]
        section_overview = (
            "\n".join(f"{chunk_id}: {hint}" for hint, chunk_id in deduped)
            or "(no sections detected)"
        )

        effective_title = (metadata.title if metadata else None) or title
        effective_origin = (metadata.source_url if metadata else None) or "unknown"

        # Calculate pacing target based on paper length
        target_turns = _calculate_target_turns(paper_content)
        language_instruction = get_language_instruction(self._settings.defaults.language)

        # Phase 0: Generate intro turns
        intro_path = Path(__file__).parent / "prompts" / "intro.txt"
        intro_template = intro_path.read_text(encoding="utf-8")
        intro_prompt = (
            intro_template
            .replace("{paper_title}", effective_title)
            .replace("{paper_origin}", effective_origin)
            .replace("{archetype_system_prompt}", prompt_data.system_prompt)
            .replace("{language_instruction}", language_instruction)
        )
        intro_response = self._llm.complete(
            system_prompt="Generate podcast intro turns as JSON array.",
            user_prompt=intro_prompt,
        )
        intro_turns = self._parse_turns_json(intro_response, archetype_id)

        chapters_plan = self._run_phase_a(
            archetype_system_prompt=prompt_data.system_prompt,
            title=effective_title,
            origin=effective_origin,
            section_overview=section_overview,
        )

        agent_system_prompt = load_react_system(
            archetype_prompt=prompt_data.system_prompt,
            title=effective_title,
            origin=effective_origin,
            sections=section_overview,
            language_instruction=language_instruction,
            target_turns=str(target_turns),
        )

        all_chapters: list[Chapter] = []
        for plan in chapters_plan:
            chapter_title = plan["title"]
            questions = plan["questions"]
            turn_lists = run_agent(
                llm=self._llm,
                store=store,
                embedder=embedder,
                questions=questions,
                system_prompt=agent_system_prompt,
                chapter_title=chapter_title,
                top_k=rag.top_k,
                archetype=archetype_id,
            )

            chapter_turns: list[DialogueTurn] = []
            for turns in turn_lists:
                chapter_turns.extend(turns)

            all_chapters.append(Chapter(title=chapter_title, turns=chapter_turns))

        all_chapters = self._run_phase_c(all_chapters)

        # Phase 4: Generate outro turns
        outro_path = Path(__file__).parent / "prompts" / "outro.txt"
        outro_template = outro_path.read_text(encoding="utf-8")
        outro_prompt = (
            outro_template
            .replace("{paper_title}", effective_title)
            .replace("{language_instruction}", language_instruction)
        )
        outro_response = self._llm.complete(
            system_prompt="Generate podcast outro turns as JSON array.",
            user_prompt=outro_prompt,
        )
        outro_turns = self._parse_turns_json(outro_response, archetype_id)

        return DialogueScript(
            title=effective_title,
            chapters=all_chapters,
            intro_turns=intro_turns,
            outro_turns=outro_turns,
        )
