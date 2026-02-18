"""Pytest configuration and fixtures for Peripatos tests."""

import json
import os
from pathlib import Path
from typing import Generator

import pytest
import yaml

from peripatos.config import PeripatosConfig
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


@pytest.fixture(scope="session")
def sample_pdf_path() -> Path:
    """Provide path to a small test PDF.
    
    Returns:
        Path to tests/fixtures/sample_paper.pdf
    """
    pdf_path = Path(__file__).parent / "fixtures" / "sample_paper.pdf"
    assert pdf_path.exists(), f"Test PDF not found at {pdf_path}"
    return pdf_path


@pytest.fixture(scope="session")
def sample_arxiv_id() -> str:
    """Provide a known ArXiv ID for testing.
    
    Returns:
        ArXiv ID string (Docling paper: 2408.09869)
    """
    return "2408.09869"


@pytest.fixture
def mock_openai_key(monkeypatch) -> Generator[None, None, None]:
    """Mock OpenAI API key environment variable for testing.
    
    Sets OPENAI_API_KEY to a test value, then cleans up after test.
    
    Yields:
        None (fixture handles env var management)
    """
    test_key = "test-key-sk-proj-abc123def456"
    monkeypatch.setenv("OPENAI_API_KEY", test_key)
    yield
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def mock_config() -> PeripatosConfig:
    """Provide a PeripatosConfig instance with test defaults.
    
    Returns:
        PeripatosConfig with test values
    """
    return PeripatosConfig(
        llm_provider="openai",
        llm_model="gpt-4o",
        tts_engine="openai",
        tts_voice_host="alloy",
        tts_voice_expert="onyx",
        persona="tutor",
        language="en",
        output_dir="./test_output",
        openai_api_key="test-key-123",
        anthropic_api_key=None,
    )


@pytest.fixture
def tmp_output_dir(tmp_path) -> Path:
    """Provide a temporary directory for generated audio output.
    
    Args:
        tmp_path: Pytest's built-in tmp_path fixture
        
    Returns:
        Path to a temporary directory for test output
    """
    output_dir = tmp_path / "audio_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture(scope="session")
def sample_markdown() -> str:
    """Provide a representative Markdown string in academic paper format.
    
    Returns:
        Multi-line Markdown string with paper structure (title, abstract, sections, equations)
    """
    return """# Efficient Conversational AI through Structured Dialogue

**Authors:** John Doe, Jane Smith

**ArXiv ID:** 2408.09869

## Abstract

This paper explores efficient dialogue generation for conversational AI systems using structured 
dialogue representations. We propose a novel approach combining hierarchical planning with 
context-aware response generation. Our method achieves 15% improvement in coherence metrics 
compared to baseline approaches.

Key equations:
- Loss function: $L = \\alpha L_{coherence} + \\beta L_{relevance}$
- Attention mechanism: $A = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V$

## 1. Introduction

Conversational AI has become increasingly important in recent years. Natural language understanding
and generation capabilities have improved dramatically with the advent of large language models.
However, maintaining coherent and contextually appropriate dialogue remains a significant challenge.

Our work builds on previous research in optimization and dialogue systems, particularly focusing on:
- Structured dialogue representation
- Hierarchical planning strategies
- Context-aware response generation

## 2. Methodology

We propose a novel approach to structured dialogue generation. The key innovation is our use of
hierarchical planning to structure the dialogue flow. This allows for more coherent and contextually
appropriate responses.

### 2.1 Architecture

Our architecture consists of three main components:

$$\\text{Dialogue}_{output} = \\text{Planner}(\\text{Context}) \\rightarrow \\text{Generator}(\\text{Plan}) \\rightarrow \\text{Optimizer}(\\text{Output})$$

### 2.2 Training

We train our model using supervised learning on a corpus of annotated dialogues. The training
procedure uses cross-entropy loss with gradient descent optimization.

## 3. Experiments

We evaluate our approach on three benchmark datasets: ConvAI2, PersonaChat, and DailyDialog.
Results show significant improvements in automatic metrics (BLEU, ROUGE) and human evaluations.

### 3.1 Results

| Dataset | Baseline | Proposed | Improvement |
|---------|----------|----------|-------------|
| ConvAI2 | 0.482 | 0.553 | +14.7% |
| PersonaChat | 0.395 | 0.437 | +10.6% |
| DailyDialog | 0.518 | 0.596 | +15.1% |

## 4. Conclusion

We have presented a novel approach to structured dialogue generation that significantly improves
dialogue coherence. Future work includes extending this method to multi-party conversations and
integrating real-time context from external knowledge bases.

## References

[1] Vaswani, A., et al. (2017). Attention is All You Need. NeurIPS.
[2] Devlin, J., et al. (2019). BERT: Pre-training of Deep Bidirectional Transformers. ICLR.
[3] Brown, T. M., et al. (2020). Language Models are Few-Shot Learners. NeurIPS.
"""


@pytest.fixture(scope="session")
def sample_dialogue_script(sample_pdf_path) -> DialogueScript:
    """Provide a pre-built DialogueScript object with sample data.
    
    Args:
        sample_pdf_path: Path to test PDF fixture
        
    Returns:
        DialogueScript instance with realistic but minimal dialogue (5 turns)
    """
    paper_metadata = PaperMetadata(
        title="Efficient Conversational AI through Structured Dialogue",
        authors=["John Doe", "Jane Smith"],
        abstract="This paper explores efficient dialogue generation for conversational AI systems.",
        arxiv_id="2408.09869",
        source_path=sample_pdf_path,
        sections=[
            SectionInfo(
                title="Introduction",
                content="Conversational AI has become increasingly important in recent years.",
                section_type=SectionType.INTRODUCTION,
            ),
            SectionInfo(
                title="Methodology",
                content="We propose a novel approach to structured dialogue generation.",
                section_type=SectionType.METHODOLOGY,
            ),
            SectionInfo(
                title="Experiments",
                content="We evaluate our approach on three benchmark datasets.",
                section_type=SectionType.EXPERIMENTS,
            ),
        ],
    )
    
    dialogue_turns = [
        DialogueTurn(
            speaker=SpeakerRole.HOST,
            text="Welcome to this discussion of the paper on conversational AI. Can you tell us what this paper is about?",
            section_ref="Introduction",
        ),
        DialogueTurn(
            speaker=SpeakerRole.EXPERT,
            text="Certainly! This paper presents new techniques for generating structured dialogues in conversational AI systems. The key innovation is using hierarchical planning to structure the dialogue flow.",
            section_ref="Introduction",
        ),
        DialogueTurn(
            speaker=SpeakerRole.HOST,
            text="That sounds interesting. What makes this approach novel compared to existing methods?",
            section_ref="Methodology",
        ),
        DialogueTurn(
            speaker=SpeakerRole.EXPERT,
            text="The key innovation is our use of hierarchical planning to structure the dialogue flow. This allows for more coherent and contextually appropriate responses.",
            section_ref="Methodology",
        ),
        DialogueTurn(
            speaker=SpeakerRole.HOST,
            text="Fascinating! How did you evaluate the effectiveness of your approach?",
            section_ref="Experiments",
        ),
    ]
    
    return DialogueScript(
        paper_metadata=paper_metadata,
        turns=dialogue_turns,
        persona_type=PersonaType.TUTOR,
        language_mode=LanguageMode.EN,
    )
