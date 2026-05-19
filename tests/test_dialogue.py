"""Tests for DialogueGenerator."""
import json
import pytest
from peripatos_core.dialogue import DialogueGenerator
from peripatos_core.providers.llm_stub import StubLLMProvider
from peripatos_core.types import ArchetypeId, DialogueScript
from peripatos_core.exceptions import LLMError


def _make_valid_response(title: str = "Test Episode", n_turns: int = 4) -> str:
    turns = []
    for i in range(n_turns):
        speaker = "Host" if i % 2 == 0 else "Guest"
        turns.append({"speaker": speaker, "text": f"Turn {i} text."})
    return json.dumps({"title": title, "turns": turns})


def test_generate_returns_dialogue_script():
    stub = StubLLMProvider(response=_make_valid_response())
    gen = DialogueGenerator(llm=stub)
    script = gen.generate("Some paper content", archetype=ArchetypeId.PEER)
    assert isinstance(script, DialogueScript)
    assert len(script.turns) == 4


def test_generate_uses_archetype_system_prompt():
    stub = StubLLMProvider(response=_make_valid_response())
    gen = DialogueGenerator(llm=stub)
    gen.generate("content", archetype=ArchetypeId.PEER)
    assert len(stub.calls) == 1
    system_prompt, user_prompt = stub.calls[0]
    assert len(system_prompt) > 10
    assert "content" in user_prompt


def test_generate_truncates_long_content():
    stub = StubLLMProvider(response=_make_valid_response())
    gen = DialogueGenerator(llm=stub)
    long_content = "x" * 20_000
    gen.generate(long_content, archetype=ArchetypeId.PEER)
    _, user_prompt = stub.calls[0]
    assert "x" * 100 in user_prompt
    assert len(user_prompt) < 15_000


def test_generate_strips_markdown_fences():
    raw = "```json\n" + _make_valid_response() + "\n```"
    stub = StubLLMProvider(response=raw)
    gen = DialogueGenerator(llm=stub)
    script = gen.generate("content", archetype=ArchetypeId.PEER)
    assert len(script.turns) == 4


def test_generate_invalid_json_raises():
    stub = StubLLMProvider(response="not valid json at all")
    gen = DialogueGenerator(llm=stub)
    with pytest.raises(LLMError, match="invalid JSON"):
        gen.generate("content", archetype=ArchetypeId.PEER)


def test_generate_by_string_archetype():
    stub = StubLLMProvider(response=_make_valid_response())
    gen = DialogueGenerator(llm=stub)
    script = gen.generate("content", archetype="tutor")
    assert isinstance(script, DialogueScript)


def test_generate_uses_title_fallback():
    response = json.dumps({"turns": [{"speaker": "A", "text": "hi"}]})
    stub = StubLLMProvider(response=response)
    gen = DialogueGenerator(llm=stub)
    script = gen.generate("content", title="My Paper Title")
    assert script.title == "My Paper Title"


def test_generate_uses_llm_title():
    response = json.dumps({"title": "LLM Title", "turns": [{"speaker": "A", "text": "hi"}]})
    stub = StubLLMProvider(response=response)
    gen = DialogueGenerator(llm=stub)
    script = gen.generate("content", title="Fallback Title")
    assert script.title == "LLM Title"
