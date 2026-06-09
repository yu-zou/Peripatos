"""ReAct agent executor."""
from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, overload

from peripatos_core.exceptions import AgentError
from peripatos_core.providers.llm import AgentMessage, LLMProvider
from peripatos_core.rag.tools import AgentState, build_tools
from peripatos_core.types import ArchetypeId, Chapter, DialogueScript, DialogueTurn

if TYPE_CHECKING:
    from peripatos_core.rag.embedder import Embedder
    from peripatos_core.rag.vector_store import VectorStore


MAX_ITERATIONS = 80


LEGACY_QUESTION_PLACEHOLDERS = ("{{question}}", "{question}")
LEGACY_CHAPTER_PLACEHOLDERS = ("{{chapter_title}}", "{chapter_title}")


def _normalize_archetype(archetype: ArchetypeId | str) -> ArchetypeId:
    if isinstance(archetype, ArchetypeId):
        return archetype
    return ArchetypeId(archetype)


def _replace_focused_placeholders(
    system_prompt: str,
    question: str,
    chapter_title: str,
) -> str:
    question_system = system_prompt
    for placeholder in LEGACY_QUESTION_PLACEHOLDERS:
        question_system = question_system.replace(placeholder, question)
    for placeholder in LEGACY_CHAPTER_PLACEHOLDERS:
        question_system = question_system.replace(placeholder, chapter_title)
    return question_system


def _strip_focused_placeholders(system_prompt: str) -> str:
    legacy_system = system_prompt
    for placeholder in LEGACY_QUESTION_PLACEHOLDERS + LEGACY_CHAPTER_PLACEHOLDERS:
        legacy_system = legacy_system.replace(placeholder, "")
    return legacy_system


def _run_single_question_state(
    llm: LLMProvider,
    store: "VectorStore",
    embedder: "Embedder",
    system_prompt: str,
    user_prompt: str,
    top_k: int,
    archetype: ArchetypeId | str = ArchetypeId.PEER,
    max_turns: int | None = None,
) -> AgentState:
    archetype_id = _normalize_archetype(archetype)
    specs, dispatcher, state = build_tools(
        store,
        embedder,
        top_k,
        archetype_id,
    )
    messages = [
        AgentMessage(role="system", content=system_prompt),
        AgentMessage(role="user", content=user_prompt),
    ]

    for _ in range(MAX_ITERATIONS):
        response = llm.complete_with_tools(messages, specs)
        messages.append(response)

        if not response.tool_calls:
            if state.finalized:
                break
            messages.append(AgentMessage(
                role="user",
                content="Please use the available tools (search, draft_turn, finalize) to complete the task. Do not reply with plain text.",
            ))
            continue

        for tool_call in response.tool_calls:
            if (
                tool_call.name in ("draft_turn", "default_draft_turn")
                and max_turns is not None
                and len(state.drafted_turns) >= max_turns
            ):
                result_str = f"max turns reached ({max_turns})"
            else:
                tool_name = tool_call.name
                if tool_name.startswith("default_") and tool_name not in dispatcher:
                    tool_name = tool_name[len("default_"):]
                if tool_name not in dispatcher:
                    result_str = (
                        f"Error: unknown tool '{tool_name}'. "
                        f"Available tools: {', '.join(sorted(dispatcher.keys()))}."
                    )
                else:
                    try:
                        result_str = dispatcher[tool_name](**tool_call.arguments)
                    except TypeError as e:
                        result_str = f"Error: {e}. Please provide all required parameters."
            messages.append(
                AgentMessage(
                    role="tool",
                    content=result_str,
                    tool_call_id=tool_call.id,
                )
            )

        if state.finalized or (
            max_turns is not None and len(state.drafted_turns) >= max_turns
        ):
            break
    else:
        warnings.warn(
            f"ReAct iteration cap reached ({MAX_ITERATIONS})",
            UserWarning,
            stacklevel=2,
        )

    if len(state.drafted_turns) == 0:
        raise AgentError("agent produced no turns")

    return state


def _run_single_question(
    llm: LLMProvider,
    store: "VectorStore",
    embedder: "Embedder",
    system_prompt: str,
    user_prompt: str,
    top_k: int,
    archetype: ArchetypeId | str = ArchetypeId.PEER,
    max_turns: int = 5,
) -> list[DialogueTurn]:
    state = _run_single_question_state(
        llm=llm,
        store=store,
        embedder=embedder,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        top_k=top_k,
        archetype=archetype,
        max_turns=max_turns,
    )
    return state.drafted_turns[:max_turns]


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
        state = _run_single_question_state(
            llm=self.llm,
            store=self.store,
            embedder=self.embedder,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            top_k=self.top_k,
            archetype=self.archetype,
        )
        return DialogueScript(
            title=state.title or "Untitled",
            chapters=[Chapter(title="", turns=state.drafted_turns)],
        )


@overload
def run_agent(
    llm: LLMProvider,
    store: "VectorStore",
    embedder: "Embedder",
    questions: list[str],
    system_prompt: str,
    chapter_title: str = "",
    top_k: int = 4,
    archetype: ArchetypeId | str = ArchetypeId.PEER,
) -> list[list[DialogueTurn]]: ...


@overload
def run_agent(
    llm: LLMProvider,
    store: "VectorStore",
    embedder: "Embedder",
    *,
    top_k: int,
    system_prompt: str,
    user_prompt: str,
    archetype: ArchetypeId | str = ArchetypeId.PEER,
) -> DialogueScript: ...


def run_agent(
    llm: LLMProvider,
    store: "VectorStore",
    embedder: "Embedder",
    questions: list[str] | None = None,
    system_prompt: str = "",
    chapter_title: str = "",
    top_k: int = 4,
    archetype: ArchetypeId | str = ArchetypeId.PEER,
    **legacy_kwargs,
) -> list[list[DialogueTurn]] | DialogueScript:
    """Run per-question RAG agent sessions. Returns one turn-list per question."""
    legacy_user_prompt = legacy_kwargs.pop("user_prompt", None)
    if legacy_kwargs:
        unexpected = next(iter(legacy_kwargs))
        raise TypeError(f"run_agent() got an unexpected keyword argument '{unexpected}'")
    if questions is None:
        if legacy_user_prompt is None:
            raise TypeError("run_agent() missing required argument: 'questions'")
        agent = ReActAgent(
            llm=llm,
            store=store,
            embedder=embedder,
            top_k=top_k,
            archetype=_normalize_archetype(archetype),
        )
        return agent.run(_strip_focused_placeholders(system_prompt), legacy_user_prompt)

    all_turns: list[list[DialogueTurn]] = []
    for question in questions:
        question_system = _replace_focused_placeholders(
            system_prompt,
            question,
            chapter_title,
        )
        question_user = f"Answer this question using the paper's content:\n\n{question}"
        turns = _run_single_question(
            llm=llm,
            store=store,
            embedder=embedder,
            system_prompt=question_system,
            user_prompt=question_user,
            top_k=top_k,
            archetype=archetype,
            max_turns=5,
        )
        all_turns.append(turns)

    return all_turns


__all__ = ["MAX_ITERATIONS", "ReActAgent", "run_agent"]
