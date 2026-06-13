from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "peripatos_core" / "prompts"


def test_intro_prompt_exists():
    p = PROMPTS_DIR / "intro.txt"
    assert p.exists()
    text = p.read_text()
    assert "{paper_title}" in text
    assert "{paper_origin}" in text
    assert "{archetype_system_prompt}" in text
    assert "{language_instruction}" in text


def test_outro_prompt_exists():
    p = PROMPTS_DIR / "outro.txt"
    assert p.exists()
    text = p.read_text()
    assert "{paper_title}" in text
    assert "{language_instruction}" in text


def test_react_system_has_conversational_instructions():
    p = PROMPTS_DIR / "react_system.txt"
    text = p.read_text()
    assert "conversational" in text.lower() or "Conversational" in text
    assert "{target_turns}" in text


def test_host_questions_has_pacing():
    p = PROMPTS_DIR / "host_questions.txt"
    text = p.read_text()
    assert "{question_count}" in text
    assert "conversational" in text.lower() or "pacing" in text.lower()


def test_react_system_includes_host_and_guest_names():
    """load_react_system should replace {host_name} and {guest_name} in template."""
    from peripatos_core.prompts import load_react_system
    result = load_react_system(
        archetype_prompt="test",
        title="Test Paper",
        origin="test",
        sections="Sections",
        language_instruction="Respond in English",
        target_turns="10",
        host_name="Alex",
        guest_name="Dr.",
    )
    assert "Alex" in result
    assert "Dr." in result
    assert "{host_name}" not in result
    assert "{guest_name}" not in result
    # The old hardcoded names should not appear
    assert "Host/Interviewee" not in result
