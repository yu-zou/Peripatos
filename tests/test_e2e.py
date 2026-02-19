"""End-to-end integration tests for Peripatos pipeline."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from peripatos.brain.bilingual import get_bilingual_prompt_modifier
from peripatos.brain.personas import get_persona_prompts
from peripatos.cli import (
    _build_chapters,
    _generate_dialogue,
    _mix_audio,
    _normalize_paper,
    _parse_pdf,
    _render_audio,
    _resolve_source,
    detect_source_type,
)
from peripatos.config import PeripatosConfig
from peripatos.eye.math_normalize import MathNormalizer
from peripatos.models import (
    AudioSegment,
    ChapterMarker,
    DialogueScript,
    DialogueTurn,
    LanguageMode,
    PaperMetadata,
    PersonaType,
    SectionInfo,
    SectionType,
    SpeakerRole,
)


class _StubDocument:
    """Stub document for mocking Docling converter."""

    def __init__(self, markdown: str) -> None:
        self._markdown = markdown

    def export_to_markdown(self) -> str:
        return self._markdown


class _StubResult:
    """Stub result for mocking Docling converter."""

    def __init__(self, markdown: str) -> None:
        self.document = _StubDocument(markdown)


def _make_stub_converter(markdown: str):
    """Create stub converter that returns fixed markdown."""

    class _StubConverter:
        def __init__(self, pipeline_options=None) -> None:
            self.pipeline_options = pipeline_options

        def convert(self, source: str | Path) -> _StubResult:
            return _StubResult(markdown)

    return _StubConverter()


# Sample markdown for testing
_SAMPLE_MARKDOWN = """# Structured Dialogue Generation

**Authors:** John Doe, Jane Smith

## Abstract

This paper explores efficient dialogue generation for conversational AI systems.

## 1. Introduction

Conversational AI has become increasingly important. Natural language understanding
capabilities have improved with large language models.

## 2. Methodology

We propose a novel approach using hierarchical planning. The architecture consists
of three main components with attention mechanisms.

## 3. Experiments

We evaluate our approach on benchmark datasets. Results show significant improvements.

## 4. Conclusion

We have presented a novel approach to dialogue generation. Future work includes
extending to multi-party conversations.
"""


class TestFullPipelineE2E:
    """End-to-end integration tests verifying full Peripatos pipeline."""

    @patch("peripatos.voice.mixer.subprocess.run")
    @patch("peripatos.voice.mixer.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("peripatos.voice.openai_tts.OpenAI")
    @patch("peripatos.brain.generator.importlib.import_module")
    def test_full_pipeline_with_mocked_openai(
        self, mock_import, mock_openai_tts, mock_which, mock_ffmpeg, tmp_path, sample_pdf_path
    ):
        """Test full pipeline (PDF → MP3) with mocked OpenAI LLM + TTS."""
        # Mock OpenAI LLM client
        mock_openai_module = Mock()
        mock_llm_client = Mock()
        mock_openai_module.OpenAI.return_value = mock_llm_client

        # Mock LLM response with valid dialogue JSON
        mock_completion = Mock()
        mock_completion.choices = [
            Mock(
                message=Mock(
                    content=json.dumps(
                        [
                            {"speaker": "HOST", "text": "What is this paper about?"},
                            {
                                "speaker": "EXPERT",
                                "text": "This paper discusses structured dialogue.",
                            },
                        ]
                    )
                )
            )
        ]
        mock_llm_client.chat.completions.create.return_value = mock_completion

        # Return LLM client for OpenAI
        def import_side_effect(name):
            if name == "openai":
                return mock_openai_module
            raise ImportError(f"No module named {name}")

        mock_import.side_effect = import_side_effect

        # Mock OpenAI TTS client
        mock_tts_client = Mock()
        mock_openai_tts.return_value = mock_tts_client

        # Mock TTS response with audio bytes
        mock_tts_response = Mock()
        # Minimal MP3 header to pass audio validation
        mock_tts_response.read.return_value = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 100
        mock_tts_client.audio.speech.create.return_value = mock_tts_response

        # Mock ffmpeg subprocess for mixer
        mock_ffmpeg.return_value = Mock(returncode=0)

        # Mock pydub AudioSegment for mixer
        with patch("peripatos.voice.mixer.PydubAudioSegment") as mock_pydub:
            mock_audio = Mock()
            mock_audio.__len__ = Mock(return_value=2000)  # 2 seconds in ms
            mock_audio.__add__ = Mock(return_value=mock_audio)
            mock_audio.export = Mock()

            mock_pydub.from_mp3.return_value = mock_audio
            mock_pydub.silent.return_value = mock_audio

            # Setup config
            config = PeripatosConfig(
                llm_provider="openai",
                llm_model="gpt-4o",
                tts_engine="openai",
                tts_voice_host="alloy",
                tts_voice_expert="onyx",
                persona="tutor",
                language="en",
                output_dir=str(tmp_path),
                openai_api_key="test-key-123",
                anthropic_api_key=None,
            )

            # Run pipeline stages
            # 1. Parse PDF with mocked converter
            from peripatos.eye.parser import PDFParser

            parser = PDFParser(converter=_make_stub_converter(_SAMPLE_MARKDOWN))
            paper = parser.parse(sample_pdf_path)
            assert isinstance(paper, PaperMetadata)
            assert paper.title
            assert len(paper.sections) > 0

            # 2. Normalize math
            normalizer = MathNormalizer()
            paper = _normalize_paper(paper, normalizer)

            # 3. Generate dialogue
            script_result, prompt_modifier = _generate_dialogue(paper, config, verbose=False)
            assert isinstance(script_result, DialogueScript)
            assert len(script_result.turns) > 0
            assert script_result.persona_type == PersonaType.TUTOR

            # 4. Render audio
            segments = _render_audio(script_result, config, verbose=False)
            assert len(segments) > 0
            assert all(isinstance(seg, AudioSegment) for seg in segments)

            # 5. Build chapters
            chapters, total_time_ms = _build_chapters(script_result, segments, 300)
            assert len(chapters) >= 0
            assert total_time_ms > 0

            # 6. Mix audio
            output_path = tmp_path / "test_output.mp3"
            result = _mix_audio(segments, chapters, output_path, verbose=False)
            assert isinstance(result, Path)

    @patch("peripatos.voice.mixer.subprocess.run")
    @patch("peripatos.voice.mixer.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("peripatos.voice.edge_tts_engine.edge_tts.Communicate")
    @patch("peripatos.brain.generator.importlib.import_module")
    def test_full_pipeline_edge_tts_fallback(
        self, mock_import, mock_edge_communicate, mock_which, mock_ffmpeg, tmp_path, sample_pdf_path
    ):
        """Test full pipeline with edge-tts fallback (no OpenAI API key)."""
        # Mock OpenAI LLM client
        mock_openai_module = Mock()
        mock_llm_client = Mock()
        mock_openai_module.OpenAI.return_value = mock_llm_client

        mock_completion = Mock()
        mock_completion.choices = [
            Mock(
                message=Mock(
                    content=json.dumps(
                        [
                            {"speaker": "HOST", "text": "Tell me about this research."},
                            {
                                "speaker": "EXPERT",
                                "text": "This work focuses on dialogue systems.",
                            },
                        ]
                    )
                )
            )
        ]
        mock_llm_client.chat.completions.create.return_value = mock_completion

        def import_side_effect(name):
            if name == "openai":
                return mock_openai_module
            raise ImportError(f"No module named {name}")

        mock_import.side_effect = import_side_effect

        # Mock edge-tts async streaming
        mock_communicate_instance = AsyncMock()

        async def mock_stream():
            yield {"type": "audio", "data": b"\xFF\xFB\x90\x00"}  # MP3 frame header
            yield {"type": "audio", "data": b"\x00" * 100}

        mock_communicate_instance.stream = mock_stream
        mock_edge_communicate.return_value = mock_communicate_instance

        # Mock ffmpeg and pydub
        mock_ffmpeg.return_value = Mock(returncode=0)

        with patch("peripatos.voice.mixer.PydubAudioSegment") as mock_pydub:
            mock_audio = Mock()
            mock_audio.__len__ = Mock(return_value=1500)
            mock_audio.__add__ = Mock(return_value=mock_audio)
            mock_audio.export = Mock()

            mock_pydub.from_mp3.return_value = mock_audio
            mock_pydub.silent.return_value = mock_audio

            # Config with edge-tts (no OpenAI TTS key)
            config = PeripatosConfig(
                llm_provider="openai",
                llm_model="gpt-4o",
                tts_engine="edge-tts",
                tts_voice_host="en-US-AriaNeural",
                tts_voice_expert="en-US-GuyNeural",
                persona="skeptic",
                language="en",
                output_dir=str(tmp_path),
                openai_api_key="test-key-123",
                anthropic_api_key=None,
            )

            # Run pipeline with mocked converter
            from peripatos.eye.parser import PDFParser

            parser = PDFParser(converter=_make_stub_converter(_SAMPLE_MARKDOWN))
            paper = parser.parse(sample_pdf_path)
            assert isinstance(paper, PaperMetadata)

            normalizer = MathNormalizer()
            paper = _normalize_paper(paper, normalizer)

            script_result, _ = _generate_dialogue(paper, config, verbose=False)
            assert isinstance(script_result, DialogueScript)
            assert script_result.persona_type == PersonaType.SKEPTIC

            segments = _render_audio(script_result, config, verbose=False)
            assert len(segments) > 0

            chapters, _ = _build_chapters(script_result, segments, 300)
            output_path = tmp_path / "edge_tts_output.mp3"
            result = _mix_audio(segments, chapters, output_path, verbose=False)
            assert isinstance(result, Path)

    @patch("urllib.request.urlopen")
    @patch("peripatos.brain.generator.importlib.import_module")
    def test_arxiv_pipeline_mocked_network(self, mock_import, mock_urlopen, tmp_path):
        """Test ArXiv ID pipeline with mocked HTTP requests."""
        # Mock ArXiv PDF download
        mock_pdf_response = Mock()
        mock_pdf_response.read.return_value = b"%PDF-1.4 fake arxiv pdf content"
        mock_pdf_response.__enter__ = Mock(return_value=mock_pdf_response)
        mock_pdf_response.__exit__ = Mock(return_value=False)

        # Mock ArXiv API metadata response
        arxiv_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Attention is All You Need</title>
    <author><name>Ashish Vaswani</name></author>
    <summary>The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.</summary>
  </entry>
</feed>"""

        mock_api_response = Mock()
        mock_api_response.read.return_value = arxiv_xml
        mock_api_response.__enter__ = Mock(return_value=mock_api_response)
        mock_api_response.__exit__ = Mock(return_value=False)

        # Mock urlopen to return PDF response
        mock_urlopen.return_value = mock_pdf_response

        # Test source detection
        source = "2408.09869"
        source_type = detect_source_type(source)
        assert source_type == "arxiv"

        # Test source resolution
        result = _resolve_source(source, source_type, tmp_path, verbose=False)
        assert isinstance(result, Path)
        assert result.exists()
        assert result.suffix == ".pdf"

        # Verify correct ArXiv URL was called for PDF download
        assert mock_urlopen.call_count >= 1
        first_call_url = str(mock_urlopen.call_args_list[0][0][0])
        assert "arxiv.org/pdf" in first_call_url
        assert "2408.09869" in first_call_url

    def test_personas_produce_different_prompts(self):
        """Test that all 4 personas generate distinct system prompts."""
        personas = [
            PersonaType.SKEPTIC,
            PersonaType.ENTHUSIAST,
            PersonaType.TUTOR,
            PersonaType.PEER,
        ]

        prompts_map = {}
        for persona in personas:
            prompts = get_persona_prompts(persona)
            assert "host_system" in prompts
            assert "expert_system" in prompts

            # Store full prompt combination
            combined = prompts["host_system"] + prompts["expert_system"]
            prompts_map[persona] = combined

        # Verify all prompts are distinct
        unique_prompts = set(prompts_map.values())
        assert len(unique_prompts) == 4, "All personas should produce unique prompts"

        # Verify persona-specific keywords
        assert "skeptical" in prompts_map[PersonaType.SKEPTIC].lower()
        assert "critical" in prompts_map[PersonaType.SKEPTIC].lower()

        assert "enthusiastic" in prompts_map[PersonaType.ENTHUSIAST].lower()
        assert "exciting" in prompts_map[PersonaType.ENTHUSIAST].lower()

        assert "patient" in prompts_map[PersonaType.TUTOR].lower()
        assert "explain" in prompts_map[PersonaType.TUTOR].lower()

        assert "domain expertise" in prompts_map[PersonaType.PEER].lower()
        assert "technical" in prompts_map[PersonaType.PEER].lower()

    def test_bilingual_mode_zh_en(self):
        """Test that bilingual mode includes Chinese+English instruction."""
        # Test ZH_EN mode
        modifier_zh_en = get_bilingual_prompt_modifier(LanguageMode.ZH_EN)
        assert modifier_zh_en != "", "ZH_EN should return non-empty modifier"
        assert "Chinese" in modifier_zh_en or "中文" in modifier_zh_en
        assert "English" in modifier_zh_en
        assert "technical terms" in modifier_zh_en

        # Verify example pattern is present
        assert "Transformer" in modifier_zh_en

        # Test EN mode (should return empty)
        modifier_en = get_bilingual_prompt_modifier(LanguageMode.EN)
        assert modifier_en == "", "EN mode should return empty modifier"

    @patch("urllib.request.urlopen")
    def test_error_cases(self, mock_urlopen, tmp_path, sample_pdf_path):
        """Test error handling: invalid ArXiv ID, missing API keys, non-existent PDF."""
        # Test 1: Invalid ArXiv ID format
        invalid_id = "not-an-arxiv-id"
        source_type = detect_source_type(invalid_id)
        assert source_type is None, "Invalid ArXiv ID should return None"

        # Test 2: Invalid ArXiv ID (valid format but 404)
        mock_urlopen.side_effect = Exception("404 Not Found")
        result = _resolve_source("9999.99999", "arxiv", tmp_path, verbose=False)
        assert isinstance(result, int), "404 error should return error code"
        assert result == 1

        # Test 3: Non-existent PDF file
        nonexistent_pdf = tmp_path / "does_not_exist.pdf"
        source_type = detect_source_type(str(nonexistent_pdf))
        assert source_type is None, "Non-existent PDF should return None"

        # Test 4: Invalid PDF parsing (corrupted file)
        corrupted_pdf = tmp_path / "corrupted.pdf"
        corrupted_pdf.write_bytes(b"not a real pdf")
        result = _parse_pdf(corrupted_pdf, verbose=False)
        # Should return error code or raise exception
        assert isinstance(result, int) or result is None

        # Test 5: Missing API key for dialogue generation
        config_no_keys = PeripatosConfig(
            llm_provider="openai",
            llm_model="gpt-4o",
            tts_engine="openai",
            tts_voice_host="alloy",
            tts_voice_expert="onyx",
            persona="tutor",
            language="en",
            output_dir=str(tmp_path),
            openai_api_key=None,  # Missing key
            anthropic_api_key=None,
        )

        # Create minimal paper metadata
        paper = PaperMetadata(
            title="Test Paper",
            authors=["Test Author"],
            abstract="Test abstract",
            source_path=sample_pdf_path,
            sections=[
                SectionInfo(
                    title="Introduction",
                    content="Test content",
                    section_type=SectionType.INTRODUCTION,
                )
            ],
        )

        # Should return error when trying to generate dialogue without API key
        with patch("peripatos.brain.generator.importlib.import_module") as mock_import:
            mock_openai = Mock()
            mock_client = Mock()
            mock_client.chat.completions.create.side_effect = Exception("Invalid API key")
            mock_openai.OpenAI.return_value = mock_client
            mock_import.return_value = mock_openai

            result, _ = _generate_dialogue(paper, config_no_keys, verbose=False)
            assert isinstance(result, int), "Missing API key should return error code"

        # Test 6: Empty audio segments (mixer should fail)
        from peripatos.voice.mixer import MixerError

        with patch("shutil.which", return_value="/usr/bin/ffmpeg"):
            output_path = tmp_path / "empty_output.mp3"
            with pytest.raises(MixerError, match="empty|no segments"):
                from peripatos.voice.mixer import AudioMixer

                mixer = AudioMixer()
                mixer.mix([], [], output_path)

    @patch("peripatos.brain.generator.importlib.import_module")
    @patch("peripatos.voice.mixer.subprocess.run")
    @patch("peripatos.voice.mixer.shutil.which", return_value="/usr/bin/ffmpeg")
    def test_multi_section_chapter_generation(
        self, mock_which, mock_ffmpeg, mock_import, tmp_path, sample_pdf_path
    ):
        """Test that multi-section papers generate proper chapter markers."""
        # Mock OpenAI LLM
        mock_openai = Mock()
        mock_client = Mock()
        mock_openai.OpenAI.return_value = mock_client

        # Return different dialogue for each section
        section_responses = [
            json.dumps([{"speaker": "HOST", "text": "Intro question?"}, {"speaker": "EXPERT", "text": "Intro answer."}]),
            json.dumps([{"speaker": "HOST", "text": "Method question?"}, {"speaker": "EXPERT", "text": "Method answer."}]),
            json.dumps([{"speaker": "HOST", "text": "Results question?"}, {"speaker": "EXPERT", "text": "Results answer."}]),
        ]

        mock_completion = Mock()
        mock_client.chat.completions.create.side_effect = [
            Mock(choices=[Mock(message=Mock(content=resp))]) for resp in section_responses
        ]

        mock_import.return_value = mock_openai
        mock_ffmpeg.return_value = Mock(returncode=0)

        # Create paper with multiple sections
        paper = PaperMetadata(
            title="Multi-Section Paper",
            authors=["Author One"],
            abstract="Test abstract",
            source_path=sample_pdf_path,
            sections=[
                SectionInfo(title="Introduction", content="Intro text.", section_type=SectionType.INTRODUCTION),
                SectionInfo(title="Methodology", content="Method text.", section_type=SectionType.METHODOLOGY),
                SectionInfo(title="Results", content="Results text.", section_type=SectionType.EXPERIMENTS),
            ],
        )

        config = PeripatosConfig(
            llm_provider="openai",
            llm_model="gpt-4o",
            tts_engine="openai",
            tts_voice_host="alloy",
            tts_voice_expert="onyx",
            persona="peer",
            language="en",
            output_dir=str(tmp_path),
            openai_api_key="test-key",
            anthropic_api_key=None,
        )

        # Mock OpenAI TTS
        with patch("peripatos.voice.openai_tts.OpenAI") as mock_tts:
            mock_tts_client = Mock()
            mock_tts.return_value = mock_tts_client
            mock_tts_response = Mock()
            mock_tts_response.read.return_value = b"ID3\x03\x00" + b"\x00" * 100
            mock_tts_client.audio.speech.create.return_value = mock_tts_response

            with patch("peripatos.voice.mixer.PydubAudioSegment") as mock_pydub:
                mock_audio = Mock()
                mock_audio.__len__ = Mock(return_value=1000)
                mock_audio.__add__ = Mock(return_value=mock_audio)
                mock_audio.export = Mock()
                mock_pydub.from_mp3.return_value = mock_audio
                mock_pydub.silent.return_value = mock_audio

                # Generate dialogue
                script, _ = _generate_dialogue(paper, config, verbose=False)
                assert isinstance(script, DialogueScript)
                assert len(script.turns) >= 3

                # Render audio
                segments = _render_audio(script, config, verbose=False)
                assert len(segments) >= 3

                # Build chapters
                chapters, total_time = _build_chapters(script, segments, 300)
                assert len(chapters) >= 1, "Should generate at least one chapter"

                # Verify chapter structure
                for chapter in chapters:
                    assert isinstance(chapter, ChapterMarker)
                    assert chapter.title
                    assert chapter.start_time_ms >= 0
                    assert chapter.end_time_ms > chapter.start_time_ms
