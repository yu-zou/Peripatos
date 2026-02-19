"""Tests for bilingual code-switching functionality."""

import pytest
from pathlib import Path

from peripatos.brain.bilingual import BilingualProcessor, get_bilingual_prompt_modifier
from peripatos.models import (
    DialogueScript,
    DialogueTurn,
    LanguageMode,
    PaperMetadata,
    PersonaType,
    SectionInfo,
    SectionType,
    SpeakerRole,
)


@pytest.fixture
def paper_metadata() -> PaperMetadata:
    """Create sample paper metadata for testing."""
    return PaperMetadata(
        title="Attention Is All You Need",
        authors=["Vaswani et al."],
        abstract="We propose a new architecture called the Transformer.",
        source_path=Path("/fake/paper.pdf"),
        sections=[
            SectionInfo(
                title="Introduction",
                content="The Transformer uses Attention Mechanism...",
                section_type=SectionType.INTRODUCTION,
            )
        ],
        arxiv_id="1706.03762",
    )


@pytest.fixture
def zh_en_script(paper_metadata: PaperMetadata) -> DialogueScript:
    """Create a Chinese-English bilingual dialogue script."""
    return DialogueScript(
        paper_metadata=paper_metadata,
        turns=[
            DialogueTurn(
                speaker=SpeakerRole.HOST,
                text="今天我们讨论 Transformer 模型。它使用 Attention Mechanism 来处理序列数据。",
                section_ref="introduction",
            ),
            DialogueTurn(
                speaker=SpeakerRole.EXPERT,
                text="是的，Transformer 的核心是 Self-Attention。它通过 Query、Key 和 Value 矩阵计算注意力权重。",
                section_ref="methodology",
            ),
            DialogueTurn(
                speaker=SpeakerRole.HOST,
                text="在训练时，我们使用 Gradient Descent 优化 Loss Function，对吗？",
                section_ref="methodology",
            ),
        ],
        persona_type=PersonaType.TUTOR,
        language_mode=LanguageMode.ZH_EN,
    )


@pytest.fixture
def en_script(paper_metadata: PaperMetadata) -> DialogueScript:
    """Create an English-only dialogue script."""
    return DialogueScript(
        paper_metadata=paper_metadata,
        turns=[
            DialogueTurn(
                speaker=SpeakerRole.HOST,
                text="Today we discuss the Transformer model. It uses the Attention Mechanism to process sequential data.",
                section_ref="introduction",
            ),
            DialogueTurn(
                speaker=SpeakerRole.EXPERT,
                text="Yes, the core of the Transformer is Self-Attention. It computes attention weights using Query, Key, and Value matrices.",
                section_ref="methodology",
            ),
        ],
        persona_type=PersonaType.PEER,
        language_mode=LanguageMode.EN,
    )


def test_bilingual_prompt_modifier_for_zh_en():
    """Test that ZH_EN mode generates bilingual instruction."""
    modifier = get_bilingual_prompt_modifier(LanguageMode.ZH_EN)
    
    # Should contain both Chinese and English references
    assert "中文" in modifier or "Chinese" in modifier or "Mandarin" in modifier
    assert "English" in modifier
    assert "technical term" in modifier.lower()
    
    # Should provide an example of mixed usage
    assert "Transformer" in modifier or "example" in modifier.lower()
    
    # Should be non-empty
    assert len(modifier) > 50


def test_bilingual_prompt_modifier_for_en():
    """Test that EN mode returns empty string (no modification)."""
    modifier = get_bilingual_prompt_modifier(LanguageMode.EN)
    
    # English mode needs no bilingual instruction
    assert modifier == ""


def test_technical_terms_preserved(zh_en_script: DialogueScript):
    """Test that technical terms in whitelist remain in English."""
    processor = BilingualProcessor()
    processed_script = processor.process(zh_en_script)
    
    # Verify all turns are processed
    assert len(processed_script.turns) == len(zh_en_script.turns)
    
    # Technical terms should remain in English (already in source, should be preserved)
    combined_text = " ".join(turn.text for turn in processed_script.turns)
    
    # These terms appear in the fixture and should remain English
    assert "Transformer" in combined_text
    assert "Attention Mechanism" in combined_text or "Self-Attention" in combined_text
    assert "Gradient Descent" in combined_text
    assert "Loss Function" in combined_text
    
    # Verify Chinese text is still present (not stripped)
    assert "今天" in combined_text or "是的" in combined_text or "对吗" in combined_text


def test_en_mode_returns_unchanged(en_script: DialogueScript):
    """Test that EN mode script passes through without modification."""
    processor = BilingualProcessor()
    processed_script = processor.process(en_script)
    
    # Should be identical to input for EN mode
    assert processed_script.turns == en_script.turns
    assert processed_script.language_mode == LanguageMode.EN
    assert processed_script.persona_type == en_script.persona_type


def test_processor_maintains_speaker_order(zh_en_script: DialogueScript):
    """Test that turn order and speaker roles are preserved after processing."""
    processor = BilingualProcessor()
    processed_script = processor.process(zh_en_script)
    
    # Same number of turns
    assert len(processed_script.turns) == len(zh_en_script.turns)
    
    # Speaker order preserved
    for original, processed in zip(zh_en_script.turns, processed_script.turns):
        assert original.speaker == processed.speaker
        assert original.section_ref == processed.section_ref


def test_processor_preserves_metadata(zh_en_script: DialogueScript):
    """Test that paper metadata and dialogue settings are preserved."""
    processor = BilingualProcessor()
    processed_script = processor.process(zh_en_script)
    
    # Metadata should be unchanged
    assert processed_script.paper_metadata == zh_en_script.paper_metadata
    assert processed_script.persona_type == zh_en_script.persona_type
    assert processed_script.language_mode == zh_en_script.language_mode


def test_technical_term_case_sensitivity():
    """Test that technical terms are preserved with correct capitalization."""
    processor = BilingualProcessor()
    
    # Create a script with lowercase technical terms (edge case)
    paper_metadata = PaperMetadata(
        title="Test Paper",
        authors=["Test Author"],
        abstract="Test abstract",
        source_path=Path("/fake/test.pdf"),
        sections=[],
    )
    
    script = DialogueScript(
        paper_metadata=paper_metadata,
        turns=[
            DialogueTurn(
                speaker=SpeakerRole.HOST,
                text="我们使用 transformer 和 attention mechanism 来训练模型。",
                section_ref="intro",
            )
        ],
        persona_type=PersonaType.TUTOR,
        language_mode=LanguageMode.ZH_EN,
    )
    
    processed = processor.process(script)
    
    # Term should still be present (case-insensitive preservation)
    text = processed.turns[0].text
    assert "transformer" in text.lower()
    assert "attention" in text.lower()
