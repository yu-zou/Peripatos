import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from peripatos.brain.generator import DialogueGenerator, GenerationError
from peripatos.brain.personas import get_persona_prompts
from peripatos.config import PeripatosConfig
from peripatos.models import (
    DialogueTurn,
    LanguageMode,
    PaperMetadata,
    PersonaType,
    SectionInfo,
    SectionType,
    SpeakerRole,
)


def _build_config(provider: str) -> PeripatosConfig:
    return PeripatosConfig(
        llm_provider=provider,
        llm_model="gpt-4o",
        tts_engine="openai",
        tts_voice_host="alloy",
        tts_voice_expert="onyx",
        persona="tutor",
        language="en",
        output_dir="./test_output",
        openai_api_key="test-openai",
        anthropic_api_key="test-anthropic",
        openrouter_api_key="test-openrouter",
        gemini_api_key="test-gemini",
    )


def _sample_paper() -> PaperMetadata:
    return PaperMetadata(
        title="Sample Paper",
        authors=["Author One"],
        abstract="Abstract text",
        source_path=Path("/tmp/sample.pdf"),
        sections=[
            SectionInfo(
                title="Introduction",
                content="Intro content.",
                section_type=SectionType.INTRODUCTION,
            )
        ],
    )


def _json_dialogue() -> str:
    return json.dumps(
        [
            {"speaker": "HOST", "text": "What is the main idea?"},
            {"speaker": "EXPERT", "text": "The paper proposes a new method."},
        ]
    )


def test_persona_prompts_distinct():
    prompts = {persona: get_persona_prompts(persona) for persona in PersonaType}
    host_texts = {value["host_system"] for value in prompts.values()}
    expert_texts = {value["expert_system"] for value in prompts.values()}
    assert len(host_texts) == 4
    assert len(expert_texts) == 4


def test_persona_prompts_both_roles():
    for persona in PersonaType:
        prompts = get_persona_prompts(persona)
        assert "host_system" in prompts
        assert "expert_system" in prompts
        assert prompts["host_system"].strip()
        assert prompts["expert_system"].strip()


@patch("peripatos.brain.generator.importlib.import_module")
def test_generate_dialogue_openai_integration(mock_import_module):
    mock_client = Mock()
    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))
    mock_import_module.return_value = mock_openai_module
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content=_json_dialogue()))]
    mock_client.chat.completions.create.return_value = mock_response

    generator = DialogueGenerator()
    config = _build_config("openai")
    paper = _sample_paper()

    script = generator.generate(paper, config)

    assert script.paper_metadata == paper
    assert script.persona_type == PersonaType.TUTOR
    assert script.language_mode == LanguageMode.EN
    assert [turn.speaker for turn in script.turns] == [
        SpeakerRole.HOST,
        SpeakerRole.EXPERT,
    ]
    call_args = mock_client.chat.completions.create.call_args[1]
    assert call_args["model"] == "gpt-4o"
    assert call_args["messages"][0]["role"] == "system"
    assert call_args["messages"][1]["role"] == "user"


@patch("peripatos.brain.generator.importlib.import_module")
def test_generator_anthropic_integration(mock_import_module):
    mock_client = Mock()
    mock_anthropic_module = Mock(Anthropic=Mock(return_value=mock_client))
    mock_import_module.return_value = mock_anthropic_module
    mock_message = Mock()
    mock_message.content = [Mock(text=_json_dialogue())]
    mock_client.messages.create.return_value = mock_message

    generator = DialogueGenerator()
    config = _build_config("anthropic")
    paper = _sample_paper()

    script = generator.generate(paper, config)
    assert isinstance(script.turns[0], DialogueTurn)
    call_args = mock_client.messages.create.call_args[1]
    assert call_args["model"] == "gpt-4o"
    assert call_args["messages"][0]["role"] == "user"
    assert "system" in call_args


@patch("peripatos.brain.generator.importlib.import_module")
def test_json_parsing_creates_turns(mock_import_module):
    mock_client = Mock()
    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))
    mock_import_module.return_value = mock_openai_module
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content=_json_dialogue()))]
    mock_client.chat.completions.create.return_value = mock_response

    generator = DialogueGenerator()
    script = generator.generate(_sample_paper(), _build_config("openai"))

    assert len(script.turns) == 2
    assert script.turns[0].speaker == SpeakerRole.HOST
    assert script.turns[1].speaker == SpeakerRole.EXPERT


@patch.object(__import__("peripatos.brain.generator", fromlist=["time"]).time, "sleep")
@patch("peripatos.brain.generator.importlib.import_module")
def test_api_failure_retry_raises_generation_error(mock_import_module, mock_sleep):
    mock_client = Mock()
    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))
    mock_import_module.return_value = mock_openai_module
    mock_client.chat.completions.create.side_effect = Exception("rate_limit")

    generator = DialogueGenerator()

    with pytest.raises(GenerationError, match="OpenAI API call failed"):
        generator.generate(_sample_paper(), _build_config("openai"))

    assert mock_client.chat.completions.create.call_count == 3
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)
    mock_sleep.assert_any_call(4)


@patch("peripatos.brain.generator.importlib.import_module")
def test_invalid_json_handling(mock_import_module):
    mock_client = Mock()
    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))
    mock_import_module.return_value = mock_openai_module
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="not-json"))]
    mock_client.chat.completions.create.return_value = mock_response

    generator = DialogueGenerator()

    with pytest.raises(GenerationError, match="Invalid JSON"):
        generator.generate(_sample_paper(), _build_config("openai"))


def test_parse_response_strips_json_code_fence():
    generator = DialogueGenerator()
    response_text = '```json\n[{"speaker": "HOST", "text": "Hello"}, {"speaker": "EXPERT", "text": "Hi"}]\n```'
    
    turns = generator._parse_response(response_text, "test-section")
    
    assert len(turns) == 2
    assert turns[0].speaker == SpeakerRole.HOST
    assert turns[0].text == "Hello"
    assert turns[1].speaker == SpeakerRole.EXPERT
    assert turns[1].text == "Hi"
    assert all(turn.section_ref == "test-section" for turn in turns)


def test_parse_response_strips_bare_code_fence():
    generator = DialogueGenerator()
    response_text = '```\n[{"speaker": "HOST", "text": "Hello"}, {"speaker": "EXPERT", "text": "Hi"}]\n```'
    
    turns = generator._parse_response(response_text, "test-section")
    
    assert len(turns) == 2
    assert turns[0].speaker == SpeakerRole.HOST
    assert turns[0].text == "Hello"
    assert turns[1].speaker == SpeakerRole.EXPERT
    assert turns[1].text == "Hi"


def test_parse_response_clean_json_still_works():
    generator = DialogueGenerator()
    response_text = '[{"speaker": "HOST", "text": "Hello"}, {"speaker": "EXPERT", "text": "Hi"}]'
    
    turns = generator._parse_response(response_text, "test-section")
    
    assert len(turns) == 2
    assert turns[0].speaker == SpeakerRole.HOST
    assert turns[0].text == "Hello"
    assert turns[1].speaker == SpeakerRole.EXPERT
    assert turns[1].text == "Hi"


def test_parse_response_repairs_unescaped_quotes():
    generator = DialogueGenerator()
    # Unescaped double quotes inside text value — the primary bug from E2E testing
    response_text = '[{"speaker": "HOST", "text": "The paper is "about" topic modeling"}, {"speaker": "EXPERT", "text": "That is correct"}]'
    turns = generator._parse_response(response_text, "test-section")
    assert len(turns) == 2
    assert turns[0].speaker == SpeakerRole.HOST
    assert "about" in turns[0].text
    assert turns[1].speaker == SpeakerRole.EXPERT


def test_parse_response_repairs_control_characters():
    generator = DialogueGenerator()
    # Literal newlines inside JSON string values (not escaped as \\n)
    response_text = '[{"speaker": "HOST", "text": "Line one.\nLine two."}, {"speaker": "EXPERT", "text": "Agreed"}]'
    turns = generator._parse_response(response_text, "test-section")
    assert len(turns) == 2
    assert turns[0].speaker == SpeakerRole.HOST
    assert "Line one" in turns[0].text
    assert turns[1].speaker == SpeakerRole.EXPERT


def test_parse_response_repairs_trailing_comma():
    generator = DialogueGenerator()
    # Trailing comma after last element — common LLM mistake
    response_text = '[{"speaker": "HOST", "text": "Hello"}, {"speaker": "EXPERT", "text": "Hi"},]'
    turns = generator._parse_response(response_text, "test-section")
    assert len(turns) == 2
    assert turns[0].speaker == SpeakerRole.HOST
    assert turns[0].text == "Hello"
    assert turns[1].speaker == SpeakerRole.EXPERT
    assert turns[1].text == "Hi"


def test_parse_response_repairs_fenced_malformed_json():
    generator = DialogueGenerator()
    # Combined: code fence wrapping + unescaped quotes inside
    response_text = '```json\n[{"speaker": "HOST", "text": "The method is "novel" indeed"}, {"speaker": "EXPERT", "text": "Yes"}]\n```'
    turns = generator._parse_response(response_text, "test-section")
    assert len(turns) == 2
    assert turns[0].speaker == SpeakerRole.HOST
    assert "novel" in turns[0].text
    assert turns[1].speaker == SpeakerRole.EXPERT


@patch("peripatos.brain.generator.importlib.import_module")
def test_long_section_chunking(mock_import_module):
    mock_client = Mock()
    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))
    mock_import_module.return_value = mock_openai_module
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content=_json_dialogue()))]
    mock_client.chat.completions.create.return_value = mock_response

    long_text = "Paragraph. " * 50
    paper = PaperMetadata(
        title="Chunked Paper",
        authors=["Author"],
        abstract="Abstract",
        source_path=Path("/tmp/chunked.pdf"),
        sections=[
            SectionInfo(
                title="Long Section",
                content=long_text,
                section_type=SectionType.OTHER,
            )
        ],
    )

    generator = DialogueGenerator(max_chunk_size=50)
    generator.generate(paper, _build_config("openai"))

    assert mock_client.chat.completions.create.call_count > 1


@patch("peripatos.brain.generator.importlib.import_module")
def test_generator_openrouter_integration(mock_import_module):
    mock_client = Mock()
    mock_openai_module = Mock(OpenAI=Mock(return_value=mock_client))
    mock_import_module.return_value = mock_openai_module
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content=_json_dialogue()))]
    mock_client.chat.completions.create.return_value = mock_response

    generator = DialogueGenerator()
    config = _build_config("openrouter")
    paper = _sample_paper()

    script = generator.generate(paper, config)

    assert script.paper_metadata == paper
    assert script.persona_type == PersonaType.TUTOR
    assert script.language_mode == LanguageMode.EN
    assert [turn.speaker for turn in script.turns] == [
        SpeakerRole.HOST,
        SpeakerRole.EXPERT,
    ]
    # Verify OpenAI client created with OpenRouter base_url
    call_args = mock_openai_module.OpenAI.call_args[1]
    assert call_args["base_url"] == "https://openrouter.ai/api/v1"
    assert call_args["api_key"] == "test-openrouter"
    # Verify chat.completions.create called correctly
    create_args = mock_client.chat.completions.create.call_args[1]
    assert create_args["model"] == "gpt-4o"
    assert create_args["messages"][0]["role"] == "system"
    assert create_args["messages"][1]["role"] == "user"


@patch("peripatos.brain.generator.importlib.import_module")
def test_generator_gemini_integration(mock_import_module):
    mock_client = Mock()
    mock_genai_module = Mock(Client=Mock(return_value=mock_client))
    mock_types_module = Mock()
    mock_config = Mock()
    mock_types_module.GenerateContentConfig = Mock(return_value=mock_config)
    
    # Handle two import calls: google.genai and google.genai.types
    def import_side_effect(module_name):
        if module_name == "google.genai":
            return mock_genai_module
        elif module_name == "google.genai.types":
            return mock_types_module
        raise ImportError(f"No module named '{module_name}'")
    
    mock_import_module.side_effect = import_side_effect
    
    mock_response = Mock()
    mock_response.text = _json_dialogue()
    mock_client.models.generate_content.return_value = mock_response

    generator = DialogueGenerator()
    config = _build_config("gemini")
    paper = _sample_paper()

    script = generator.generate(paper, config)

    assert script.paper_metadata == paper
    assert script.persona_type == PersonaType.TUTOR
    assert script.language_mode == LanguageMode.EN
    assert [turn.speaker for turn in script.turns] == [
        SpeakerRole.HOST,
        SpeakerRole.EXPERT,
    ]
    # Verify Client created with correct api_key
    client_args = mock_genai_module.Client.call_args[1]
    assert client_args["api_key"] == "test-gemini"
    # Verify generate_content called with correct parameters
    call_args = mock_client.models.generate_content.call_args[1]
    assert call_args["model"] == "gpt-4o"
    assert "contents" in call_args
    assert call_args["config"] == mock_config


@patch("peripatos.brain.generator.importlib.import_module")
def test_openrouter_import_error(mock_import_module):
    mock_import_module.side_effect = ImportError("No module named 'openai'")

    generator = DialogueGenerator()
    config = _build_config("openrouter")
    paper = _sample_paper()

    with pytest.raises(GenerationError, match="OpenAI client not available"):
        generator.generate(paper, config)


@patch("peripatos.brain.generator.importlib.import_module")
def test_gemini_import_error(mock_import_module):
    mock_import_module.side_effect = ImportError("No module named 'google.genai'")

    generator = DialogueGenerator()
    config = _build_config("gemini")
    paper = _sample_paper()

    with pytest.raises(GenerationError, match="Google GenAI client not available"):
        generator.generate(paper, config)
