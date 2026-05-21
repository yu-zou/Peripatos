"""Dialogue generator — converts parsed paper text into a DialogueScript."""
from __future__ import annotations

import hashlib
from pathlib import Path

from peripatos_core.archetypes import ArchetypeLoader
from peripatos_core.config import Settings
from peripatos_core.prompts import load_react_system
from peripatos_core.providers.llm import LLMProvider
from peripatos_core.rag.agent import run_agent
from peripatos_core.rag.chunker import chunk_text
from peripatos_core.rag.embedder import Embedder
from peripatos_core.rag.vector_store import VectorStore
from peripatos_core.types import ArchetypeId, DialogueScript, PaperMetadata


class DialogueGenerator:
    """Generates a Socratic dialogue from paper text using the ReAct RAG agent."""

    def __init__(self, llm: LLMProvider, settings: Settings | None = None) -> None:
        self._llm = llm
        self._settings = settings or Settings()
        self._loader = ArchetypeLoader()

    def generate(
        self,
        paper_content: str,
        archetype: ArchetypeId | str = ArchetypeId.PEER,
        title: str = "Untitled Paper",
        metadata: PaperMetadata | None = None,
    ) -> DialogueScript:
        """Generate a dialogue script from paper content."""
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
        )

        store = VectorStore(cache_dir=cache_dir, content_hash=content_hash)
        if not store.has_cache():
            chunks = chunk_text(
                paper_content,
                chunk_size=rag.chunk_size,
                overlap=rag.chunk_overlap,
            )
            texts = [chunk.text for chunk in chunks]
            embeddings = embedder.embed(texts)
            store.build(chunks, embeddings)
        else:
            store.load()

        sections_list = store.list_sections()
        section_overview = (
            "\n".join(f"{chunk_id}: {hint}" for chunk_id, hint in sections_list)
            or "(no sections detected)"
        )

        effective_title = (metadata.title if metadata else None) or title
        effective_origin = (metadata.source_url if metadata else None) or "unknown"
        system_prompt = load_react_system(
            archetype_prompt=prompt_data.system_prompt,
            title=effective_title,
            origin=effective_origin,
            sections=section_overview,
        )

        return run_agent(
            llm=self._llm,
            store=store,
            embedder=embedder,
            top_k=rag.top_k,
            system_prompt=system_prompt,
            user_prompt=prompt_data.dialogue_prompt,
            archetype=archetype_id,
        )
