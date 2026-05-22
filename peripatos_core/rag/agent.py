"""ReAct agent executor."""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from peripatos_core.exceptions import AgentError
from peripatos_core.providers.llm import AgentMessage, LLMProvider
from peripatos_core.rag.tools import build_tools
from peripatos_core.types import ArchetypeId, DialogueScript

if TYPE_CHECKING:
    from peripatos_core.rag.embedder import Embedder
    from peripatos_core.rag.vector_store import VectorStore


MAX_ITERATIONS = 80
LEGACY_ITERATION_CAP = 40
READ_CHUNK_LIMIT = 10


class ReActAgent:
    """Tool-using agent that drafts a dialogue script from retrieved context."""

    def __init__(
        self,
        llm: LLMProvider,
        store: "VectorStore",
        embedder: "Embedder",
        top_k: int,
        archetype: ArchetypeId = ArchetypeId.PEER,
    ) -> None:
        self.llm = llm
        self.store = store
        self.embedder = embedder
        self.top_k = top_k
        self.archetype = archetype

    def run(self, system_prompt: str, user_prompt: str) -> DialogueScript:
        specs, dispatcher, state = build_tools(
            self.store,
            self.embedder,
            self.top_k,
            self.archetype,
        )
        messages = [
            AgentMessage(role="system", content=system_prompt),
            AgentMessage(role="user", content=user_prompt),
        ]

        for _ in range(MAX_ITERATIONS):
            active_specs = (
                [spec for spec in specs if spec.name in {"draft_turn", "finalize"}]
                if state.read_chunk_calls >= READ_CHUNK_LIMIT
                else specs
            )
            response = self.llm.complete_with_tools(messages, active_specs)
            messages.append(response)

            if not response.tool_calls:
                break

            for tool_call in response.tool_calls:
                result_str = dispatcher[tool_call.name](**tool_call.arguments)
                messages.append(
                    AgentMessage(
                        role="tool",
                        content=result_str,
                        tool_call_id=tool_call.id,
                    )
                )

            if state.finalized:
                break
        else:
            warnings.warn(
                f"ReAct iteration cap reached ({LEGACY_ITERATION_CAP}); "
                f"current cap is {MAX_ITERATIONS}",
                UserWarning,
                stacklevel=2,
            )

        if len(state.drafted_turns) == 0:
            raise AgentError("agent produced no turns")

        return DialogueScript(title=state.title or "Untitled", turns=state.drafted_turns)


def run_agent(
    llm: LLMProvider,
    store: "VectorStore",
    embedder: "Embedder",
    top_k: int,
    system_prompt: str,
    user_prompt: str,
    archetype: ArchetypeId = ArchetypeId.PEER,
) -> DialogueScript:
    """Run a ReActAgent without explicitly instantiating it."""
    agent = ReActAgent(
        llm=llm,
        store=store,
        embedder=embedder,
        top_k=top_k,
        archetype=archetype,
    )
    return agent.run(system_prompt, user_prompt)


__all__ = ["MAX_ITERATIONS", "ReActAgent", "run_agent"]
