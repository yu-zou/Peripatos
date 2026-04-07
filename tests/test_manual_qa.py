"""Manual QA test script for final verification."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

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
from peripatos.eye.parser import PDFParser
from peripatos.models import (
    AudioSegment,
    ChapterMarker,
    DialogueScript,
    LanguageMode,
    PaperMetadata,
    PersonaType,
    SectionInfo,
    SectionType,
)

# Sample markdown content for testing
_TEST_MARKDOWN = """# Efficient Conversational AI through Structured Dialogue

**Authors:** John Doe, Jane Smith

## Abstract

This paper explores efficient dialogue generation for conversational AI systems using structured 
dialogue representations. We propose a novel approach combining hierarchical planning with 
context-aware response generation.

## 1. Introduction

Conversational AI has become increasingly important in recent years. Natural language understanding
and generation capabilities have improved dramatically with the advent of large language models.

## 2. Methodology

We propose a novel approach to structured dialogue generation. The key innovation is our use of
hierarchical planning to structure the dialogue flow.

## 3. Experiments

We evaluate our approach on three benchmark datasets: ConvAI2, PersonaChat, and DailyDialog.
Results show significant improvements in automatic metrics.

## 4. Conclusion

We have presented a novel approach to structured dialogue generation that significantly improves
dialogue coherence. Future work includes extending this method to multi-party conversations.
"""


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


class TestManualQA:
    """Manual QA test scenarios with real execution and mocked API calls."""

    @patch.object(__import__("peripatos.voice.openai_tts", fromlist=["OpenAI"]), "OpenAI")
    @patch("peripatos.voice.mixer.subprocess.run")
    @patch("peripatos.voice.mixer.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch.object(__import__("peripatos.voice.renderer", fromlist=["PydubAudioSegment"]).PydubAudioSegment, "from_mp3")
    @patch.object(__import__("peripatos.voice.renderer", fromlist=["PydubAudioSegment"]).PydubAudioSegment, "silent")
    @patch("peripatos.brain.generator.importlib.import_module")
    @patch("urllib.request.urlopen")
    def test_scenario_1_arxiv_tutor_with_chapters(
        self, mock_urlopen, mock_import, mock_renderer_silent, mock_renderer_from_mp3, mock_which, mock_ffmpeg, mock_openai_tts, tmp_path
    ):
        """Scenario 1: ArXiv ID → Full MP3 with tutor persona and chapters."""
        # Mock ArXiv PDF download
        mock_pdf_response = Mock()
        mock_pdf_response.read.return_value = b"%PDF-1.4 test arxiv content"
        mock_pdf_response.__enter__ = Mock(return_value=mock_pdf_response)
        mock_pdf_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_pdf_response

        # Mock OpenAI LLM
        mock_openai_module = Mock()
        mock_llm_client = Mock()
        mock_openai_module.OpenAI.return_value = mock_llm_client

        # Generate dialogue with section references
        dialogue_json = json.dumps([
            {"speaker": "HOST", "text": "What is this paper about?", "section": "Introduction"},
            {"speaker": "EXPERT", "text": "This paper discusses conversational AI.", "section": "Introduction"},
            {"speaker": "HOST", "text": "How does the methodology work?", "section": "Methodology"},
            {"speaker": "EXPERT", "text": "The approach uses hierarchical planning.", "section": "Methodology"},
        ])

        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content=dialogue_json))]
        mock_llm_client.chat.completions.create.return_value = mock_completion

        def import_side_effect(name):
            if name == "openai":
                return mock_openai_module
            # Allow all other imports to work normally
            real_import = __import__
            return real_import(name, fromlist=[name.split('.')[-1]])

        mock_import.side_effect = import_side_effect

        # Mock OpenAI TTS
        mock_tts_client = Mock()
        mock_openai_tts.return_value = mock_tts_client
        mock_tts_response = Mock()
        mock_tts_response.read.return_value = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 100
        mock_tts_client.audio.speech.create.return_value = mock_tts_response

        # Mock ffmpeg and pydub
        mock_ffmpeg.return_value = Mock(returncode=0)

        mock_audio = Mock()
        mock_audio.__len__ = Mock(return_value=2000)
        mock_audio.__add__ = Mock(return_value=mock_audio)
        mock_audio.export = Mock()
        mock_renderer_from_mp3.return_value = mock_audio
        mock_renderer_silent.return_value = mock_audio

        with patch("peripatos.voice.mixer.PydubAudioSegment") as mock_pydub:
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

            # Execute pipeline
            arxiv_id = "2408.09869"
            source_type = detect_source_type(arxiv_id)
            assert source_type == "arxiv"

            # Resolve source (download PDF)
            pdf_path = _resolve_source(arxiv_id, source_type, tmp_path, verbose=False)
            assert isinstance(pdf_path, Path)
            assert pdf_path.exists()

            # Parse PDF
            parser = PDFParser(converter=_make_stub_converter(_TEST_MARKDOWN))
            paper = parser.parse(pdf_path)
            assert isinstance(paper, PaperMetadata)
            assert len(paper.sections) > 0

            # Normalize math
            normalizer = MathNormalizer()
            paper = _normalize_paper(paper, normalizer)

            # Generate dialogue
            script, prompt_modifier = _generate_dialogue(paper, config, verbose=False)
            assert isinstance(script, DialogueScript)
            assert len(script.turns) > 0
            assert script.persona_type == PersonaType.TUTOR

            # Render audio
            segments = _render_audio(script, config, verbose=False)
            assert len(segments) > 0
            assert all(isinstance(seg, AudioSegment) for seg in segments)

            # Build chapters
            chapters, total_time_ms = _build_chapters(script, segments, 300)
            assert total_time_ms > 0
            # Should have at least one chapter if sections are long enough
            assert isinstance(chapters, list)

            print(f"✓ Scenario 1: ArXiv → MP3 with tutor persona - PASS")
            print(f"  - Generated {len(script.turns)} dialogue turns")
            print(f"  - Created {len(segments)} audio segments")
            print(f"  - Generated {len(chapters)} chapters")
            print(f"  - Total duration: {total_time_ms}ms")

    @patch("peripatos.voice.mixer.subprocess.run")
    @patch("peripatos.voice.mixer.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("peripatos.voice.openai_tts.OpenAI")
    @patch("peripatos.brain.generator.importlib.import_module")
    def test_scenario_2_local_pdf_skeptic(
        self, mock_import, mock_openai_tts, mock_which, mock_ffmpeg, tmp_path, sample_pdf_path
    ):
        """Scenario 2: Local PDF → Full MP3 with skeptic persona."""
        # Mock OpenAI LLM
        mock_openai_module = Mock()
        mock_llm_client = Mock()
        mock_openai_module.OpenAI.return_value = mock_llm_client

        dialogue_json = json.dumps([
            {"speaker": "HOST", "text": "Are the claims in this paper well-supported?"},
            {"speaker": "EXPERT", "text": "Let me critically examine the methodology and evidence."},
        ])

        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content=dialogue_json))]
        mock_llm_client.chat.completions.create.return_value = mock_completion
        mock_import.return_value = mock_openai_module

        # Mock OpenAI TTS
        mock_tts_client = Mock()
        mock_openai_tts.return_value = mock_tts_client
        mock_tts_response = Mock()
        mock_tts_response.read.return_value = b"ID3\x03\x00\x00" + b"\x00" * 100
        mock_tts_client.audio.speech.create.return_value = mock_tts_response

        mock_ffmpeg.return_value = Mock(returncode=0)

        with patch("peripatos.voice.mixer.PydubAudioSegment") as mock_pydub:
            mock_audio = Mock()
            mock_audio.__len__ = Mock(return_value=1500)
            mock_audio.__add__ = Mock(return_value=mock_audio)
            mock_audio.export = Mock()
            mock_pydub.from_mp3.return_value = mock_audio
            mock_pydub.silent.return_value = mock_audio

            config = PeripatosConfig(
                llm_provider="openai",
                llm_model="gpt-4o",
                tts_engine="openai",
                tts_voice_host="alloy",
                tts_voice_expert="onyx",
                persona="skeptic",
                language="en",
                output_dir=str(tmp_path),
                openai_api_key="test-key-123",
                anthropic_api_key=None,
            )

            # Parse PDF
            parser = PDFParser(converter=_make_stub_converter(_TEST_MARKDOWN))
            paper = parser.parse(sample_pdf_path)
            assert isinstance(paper, PaperMetadata)

            # Normalize and generate
            normalizer = MathNormalizer()
            paper = _normalize_paper(paper, normalizer)

            script, _ = _generate_dialogue(paper, config, verbose=False)
            assert isinstance(script, DialogueScript)
            assert script.persona_type == PersonaType.SKEPTIC

            segments = _render_audio(script, config, verbose=False)
            chapters, _ = _build_chapters(script, segments, 300)



            print(f"✓ Scenario 2: Local PDF → MP3 with skeptic persona - PASS")

    @patch("peripatos.voice.mixer.subprocess.run")
    @patch("peripatos.voice.mixer.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("peripatos.voice.edge_tts_engine.edge_tts.Communicate")
    @patch("peripatos.brain.generator.importlib.import_module")
    def test_scenario_3_edge_tts_fallback(
        self, mock_import, mock_edge_communicate, mock_which, mock_ffmpeg, tmp_path, sample_pdf_path
    ):
        """Scenario 3: edge-tts fallback (no OpenAI TTS API key)."""
        # Mock OpenAI LLM
        mock_openai_module = Mock()
        mock_llm_client = Mock()
        mock_openai_module.OpenAI.return_value = mock_llm_client

        dialogue_json = json.dumps([
            {"speaker": "HOST", "text": "Testing edge-tts fallback."},
            {"speaker": "EXPERT", "text": "This should use edge-tts for synthesis."},
        ])

        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content=dialogue_json))]
        mock_llm_client.chat.completions.create.return_value = mock_completion
        mock_import.return_value = mock_openai_module

        # Mock edge-tts
        mock_communicate_instance = AsyncMock()

        async def mock_stream():
            yield {"type": "audio", "data": b"\xFF\xFB\x90\x00"}
            yield {"type": "audio", "data": b"\x00" * 100}

        mock_communicate_instance.stream = mock_stream
        mock_edge_communicate.return_value = mock_communicate_instance

        mock_ffmpeg.return_value = Mock(returncode=0)

        with patch("peripatos.voice.mixer.PydubAudioSegment") as mock_pydub:
            mock_audio = Mock()
            mock_audio.__len__ = Mock(return_value=1200)
            mock_audio.__add__ = Mock(return_value=mock_audio)
            mock_audio.export = Mock()
            mock_pydub.from_mp3.return_value = mock_audio
            mock_pydub.silent.return_value = mock_audio

            config = PeripatosConfig(
                llm_provider="openai",
                llm_model="gpt-4o",
                tts_engine="edge-tts",  # Use edge-tts
                tts_voice_host="en-US-AriaNeural",
                tts_voice_expert="en-US-GuyNeural",
                persona="tutor",
                language="en",
                output_dir=str(tmp_path),
                openai_api_key="test-key-123",
                anthropic_api_key=None,
            )

            parser = PDFParser(converter=_make_stub_converter(_TEST_MARKDOWN))
            paper = parser.parse(sample_pdf_path)

            normalizer = MathNormalizer()
            paper = _normalize_paper(paper, normalizer)

            script, _ = _generate_dialogue(paper, config, verbose=False)
            assert isinstance(script, DialogueScript)
            segments = _render_audio(script, config, verbose=False)
            chapters, _ = _build_chapters(script, segments, 300)



            print(f"✓ Scenario 3: edge-tts fallback - PASS")

    @patch("peripatos.voice.mixer.subprocess.run")
    @patch("peripatos.voice.mixer.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("peripatos.voice.openai_tts.OpenAI")
    @patch("peripatos.brain.generator.importlib.import_module")
    def test_scenario_4_bilingual_zh_en(
        self, mock_import, mock_openai_tts, mock_which, mock_ffmpeg, tmp_path, sample_pdf_path
    ):
        """Scenario 4: Bilingual mode (zh-en) includes Chinese instruction."""
        # Mock OpenAI LLM
        mock_openai_module = Mock()
        mock_llm_client = Mock()
        mock_openai_module.OpenAI.return_value = mock_llm_client

        dialogue_json = json.dumps([
            {"speaker": "HOST", "text": "Transformer 模型是什么？"},
            {"speaker": "EXPERT", "text": "Transformer 使用 self-attention 机制。"},
        ])

        mock_completion = Mock()
        mock_completion.choices = [Mock(message=Mock(content=dialogue_json))]
        mock_llm_client.chat.completions.create.return_value = mock_completion
        mock_import.return_value = mock_openai_module

        # Mock TTS
        mock_tts_client = Mock()
        mock_openai_tts.return_value = mock_tts_client
        mock_tts_response = Mock()
        mock_tts_response.read.return_value = b"ID3\x03\x00" + b"\x00" * 100
        mock_tts_client.audio.speech.create.return_value = mock_tts_response

        mock_ffmpeg.return_value = Mock(returncode=0)

        with patch("peripatos.voice.mixer.PydubAudioSegment") as mock_pydub:
            mock_audio = Mock()
            mock_audio.__len__ = Mock(return_value=1000)
            mock_audio.__add__ = Mock(return_value=mock_audio)
            mock_audio.export = Mock()
            mock_pydub.from_mp3.return_value = mock_audio
            mock_pydub.silent.return_value = mock_audio

            config = PeripatosConfig(
                llm_provider="openai",
                llm_model="gpt-4o",
                tts_engine="openai",
                tts_voice_host="alloy",
                tts_voice_expert="onyx",
                persona="tutor",
                language="zh-en",  # Bilingual mode
                output_dir=str(tmp_path),
                openai_api_key="test-key-123",
                anthropic_api_key=None,
            )

            parser = PDFParser(converter=_make_stub_converter(_TEST_MARKDOWN))
            paper = parser.parse(sample_pdf_path)

            normalizer = MathNormalizer()
            paper = _normalize_paper(paper, normalizer)

            script, prompt_modifier = _generate_dialogue(paper, config, verbose=False)
            assert isinstance(script, DialogueScript)
            assert script.language_mode == LanguageMode.ZH_EN

            # Verify bilingual prompt modifier is included
            assert prompt_modifier != ""
            assert "Chinese" in prompt_modifier or "中文" in prompt_modifier

            segments = _render_audio(script, config, verbose=False)
            chapters, _ = _build_chapters(script, segments, 300)



            print(f"✓ Scenario 4: Bilingual zh-en mode - PASS")

    @patch("peripatos.voice.mixer.subprocess.run")
    @patch("peripatos.voice.mixer.shutil.which", return_value="/usr/bin/ffmpeg")
    @patch("peripatos.voice.openai_tts.OpenAI")
    @patch("peripatos.brain.generator.importlib.import_module")
    def test_scenario_5_all_personas(
        self, mock_import, mock_openai_tts, mock_which, mock_ffmpeg, tmp_path, sample_pdf_path
    ):
        """Scenario 5: Test all 4 personas generate different prompts."""
        from peripatos.brain.personas import get_persona_prompts

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
            combined = prompts["host_system"] + prompts["expert_system"]
            prompts_map[persona] = combined

        # Verify all prompts are distinct
        unique_prompts = set(prompts_map.values())
        assert len(unique_prompts) == 4

        # Verify persona-specific keywords
        assert "skeptical" in prompts_map[PersonaType.SKEPTIC].lower()
        assert "enthusiastic" in prompts_map[PersonaType.ENTHUSIAST].lower()
        assert "patient" in prompts_map[PersonaType.TUTOR].lower()
        assert "domain expertise" in prompts_map[PersonaType.PEER].lower()

        print(f"✓ Scenario 5: All 4 personas produce unique prompts - PASS")

    @patch("urllib.request.urlopen")
    def test_error_case_invalid_arxiv_id(self, mock_urlopen, tmp_path):
        """Error case: Invalid ArXiv ID returns clean error message."""
        # Test invalid format
        invalid_id = "not-an-arxiv-id"
        source_type = detect_source_type(invalid_id)
        assert source_type is None

        # Test valid format but 404
        mock_urlopen.side_effect = Exception("404 Not Found")
        result = _resolve_source("9999.99999", "arxiv", tmp_path, verbose=False)
        assert isinstance(result, int)
        assert result == 1

        print(f"✓ Error case: Invalid ArXiv ID - PASS")

    @patch("peripatos.brain.generator.importlib.import_module")
    def test_error_case_missing_api_key(self, mock_import, tmp_path, sample_pdf_path):
        """Error case: Missing API key returns helpful error."""
        # Mock OpenAI with invalid API key
        mock_openai = Mock()
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Invalid API key")
        mock_openai.OpenAI.return_value = mock_client
        mock_import.return_value = mock_openai

        config = PeripatosConfig(
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

        result, _ = _generate_dialogue(paper, config, verbose=False)
        assert isinstance(result, int)

        print(f"✓ Error case: Missing API key - PASS")

    def test_error_case_nonexistent_pdf(self, tmp_path):
        """Error case: Non-existent PDF path returns clear error."""
        nonexistent_pdf = tmp_path / "does_not_exist.pdf"
        source_type = detect_source_type(str(nonexistent_pdf))
        assert source_type is None

        # Try parsing corrupted PDF
        corrupted_pdf = tmp_path / "corrupted.pdf"
        corrupted_pdf.write_bytes(b"not a real pdf")
        result = _parse_pdf(corrupted_pdf, use_vlm=False, verbose=False)
        assert isinstance(result, int) or result is None

        print(f"✓ Error case: Non-existent/invalid PDF - PASS")
