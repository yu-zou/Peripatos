"""Tests for peripatos configuration system."""
import os
import tempfile
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

from peripatos.config import (
    PeripatosConfig,
    load_config,
    VALID_PERSONAS,
    VALID_LANGUAGES,
    VALID_LLM_PROVIDERS,
    VALID_TTS_ENGINES,
)


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_config_file(temp_config_dir):
    """Create a temporary config file."""
    config_path = Path(temp_config_dir) / "config.yaml"
    config_data = {
        "llm": {
            "provider": "openai",
            "model": "gpt-4o",
        },
        "tts": {
            "engine": "openai",
            "voice_host": "alloy",
            "voice_expert": "onyx",
        },
        "persona": "tutor",
        "language": "en",
        "output_dir": "./output",
    }
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    return config_path


class TestDefaultConfig:
    """Test that default config loads when no file exists."""

    def test_default_config_loads(self, temp_config_dir, monkeypatch):
        """Test that default config is loaded when no config file exists."""
        # Mock the config directory to a temp location
        mock_config_path = Path(temp_config_dir) / "config.yaml"
        
        with patch("peripatos.config.get_config_path", return_value=mock_config_path):
            # Ensure no .env file exists
            with patch.dict(os.environ, {}, clear=True):
                config = load_config()
                
                # Check defaults
                assert config.persona == "tutor"
                assert config.language == "en"
                assert config.llm_provider == "openai"
                assert config.llm_model == "gpt-4o"
                assert config.tts_engine == "openai"
                assert config.tts_voice_host == "alloy"
                assert config.tts_voice_expert == "onyx"
                assert config.output_dir == "./output"


class TestYAMLConfigLoading:
    """Test that YAML config file is parsed correctly."""

    def test_yaml_config_file_parsed(self, temp_config_file):
        """Test that YAML config file is loaded and parsed correctly."""
        with patch("peripatos.config.get_config_path", return_value=temp_config_file):
            with patch.dict(os.environ, {}, clear=True):
                config = load_config()
                
                assert config.persona == "tutor"
                assert config.language == "en"
                assert config.llm_provider == "openai"
                assert config.llm_model == "gpt-4o"
                assert config.tts_engine == "openai"
                assert config.tts_voice_host == "alloy"
                assert config.tts_voice_expert == "onyx"
                assert config.output_dir == "./output"

    def test_partial_yaml_config(self, temp_config_dir):
        """Test that partial YAML config merges with defaults."""
        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "llm": {
                "provider": "anthropic",
                "model": "claude-3-opus",
            },
            "persona": "skeptic",
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        with patch("peripatos.config.get_config_path", return_value=config_path):
            with patch.dict(os.environ, {}, clear=True):
                config = load_config()
                
                # Check overridden values
                assert config.llm_provider == "anthropic"
                assert config.llm_model == "claude-3-opus"
                assert config.persona == "skeptic"
                
                # Check defaults for unspecified values
                assert config.language == "en"
                assert config.tts_engine == "openai"


class TestEnvVarLoading:
    """Test that .env API keys are loaded."""

    def test_env_vars_override_config(self, temp_config_file):
        """Test that environment variables override config file."""
        with patch("peripatos.config.get_config_path", return_value=temp_config_file):
            with patch.dict(os.environ, {
                "OPENAI_API_KEY": "sk-test-openai",
                "ANTHROPIC_API_KEY": "sk-test-anthropic",
            }, clear=True):
                config = load_config()
                
                assert config.openai_api_key == "sk-test-openai"
                assert config.anthropic_api_key == "sk-test-anthropic"


class TestCLIOverrides:
    """Test that CLI overrides take precedence."""

    def test_cli_overrides_take_precedence(self, temp_config_file):
        """Test that CLI overrides take precedence over config file."""
        with patch("peripatos.config.get_config_path", return_value=temp_config_file):
            with patch.dict(os.environ, {}, clear=True):
                cli_overrides = {
                    "persona": "enthusiast",
                    "language": "zh-en",
                    "llm_provider": "anthropic",
                }
                config = load_config(cli_overrides=cli_overrides)
                
                assert config.persona == "enthusiast"
                assert config.language == "zh-en"
                assert config.llm_provider == "anthropic"
                
                # Other values should still come from file
                assert config.llm_model == "gpt-4o"


class TestAPIKeyValidation:
    """Test that missing API key raises ValueError."""

    def test_missing_openai_api_key_raises_error(self, temp_config_file):
        """Test that missing OPENAI_API_KEY raises ValueError."""
        with patch("peripatos.config.get_config_path", return_value=temp_config_file):
            with patch.dict(os.environ, {}, clear=True):  # No API keys
                config = load_config()
                
                with pytest.raises(ValueError) as exc_info:
                    config.validate_api_keys()
                
                # Check that error message contains the missing key name
                assert "OPENAI_API_KEY" in str(exc_info.value)

    def test_missing_anthropic_api_key_raises_error(self, temp_config_file, temp_config_dir):
        """Test that missing ANTHROPIC_API_KEY raises ValueError."""
        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "llm": {
                "provider": "anthropic",
                "model": "claude-3-opus",
            },
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        with patch("peripatos.config.get_config_path", return_value=config_path):
            with patch.dict(os.environ, {}, clear=True):  # No API keys
                config = load_config()
                
                with pytest.raises(ValueError) as exc_info:
                    config.validate_api_keys()
                
                # Check that error message contains the missing key name
                assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    def test_api_key_validation_passes_with_key(self, temp_config_file):
        """Test that validation passes when API key is present."""
        with patch("peripatos.config.get_config_path", return_value=temp_config_file):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
                config = load_config()
                
                # Should not raise
                config.validate_api_keys()


class TestPersonaValidation:
    """Test that invalid persona raises ValueError."""

    def test_invalid_persona_raises_error(self, temp_config_dir):
        """Test that invalid persona value raises ValueError."""
        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "persona": "invalid_persona",
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        with patch("peripatos.config.get_config_path", return_value=config_path):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError) as exc_info:
                    load_config()
                
                assert "persona" in str(exc_info.value).lower()
                assert "invalid_persona" in str(exc_info.value)


class TestLanguageValidation:
    """Test language validation."""

    def test_valid_languages(self, temp_config_dir):
        """Test that valid languages are accepted."""
        for lang in VALID_LANGUAGES:
            config_path = Path(temp_config_dir) / "config.yaml"
            config_data = {"language": lang}
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)
            
            with patch("peripatos.config.get_config_path", return_value=config_path):
                with patch.dict(os.environ, {}, clear=True):
                    config = load_config()
                    assert config.language == lang

    def test_invalid_language_raises_error(self, temp_config_dir):
        """Test that invalid language raises ValueError."""
        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {"language": "invalid_lang"}
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        with patch("peripatos.config.get_config_path", return_value=config_path):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError) as exc_info:
                    load_config()
                
                assert "language" in str(exc_info.value).lower()


class TestConfigDataclass:
    """Test PeripatosConfig dataclass."""

    def test_config_dataclass_attributes(self, temp_config_file):
        """Test that PeripatosConfig has all required attributes."""
        with patch("peripatos.config.get_config_path", return_value=temp_config_file):
            with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
                config = load_config()
                
                # Check all required attributes exist
                assert hasattr(config, "llm_provider")
                assert hasattr(config, "llm_model")
                assert hasattr(config, "tts_engine")
                assert hasattr(config, "tts_voice_host")
                assert hasattr(config, "tts_voice_expert")
                assert hasattr(config, "persona")
                assert hasattr(config, "language")
                assert hasattr(config, "output_dir")
                assert hasattr(config, "openai_api_key")
                assert hasattr(config, "anthropic_api_key")


class TestPriorityOrder:
    """Test that config priority is: defaults → file → env → CLI."""

    def test_full_priority_chain(self, temp_config_dir):
        """Test complete priority chain: defaults → file → env → CLI."""
        # Create config file
        config_path = Path(temp_config_dir) / "config.yaml"
        config_data = {
            "language": "zh-en",  # file sets this
            "persona": "peer",    # file sets this
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        
        with patch("peripatos.config.get_config_path", return_value=config_path):
            # File sets language and persona
            # CLI overrides persona
            cli_overrides = {"persona": "skeptic"}
            with patch.dict(os.environ, {}, clear=True):
                config = load_config(cli_overrides=cli_overrides)
                
                # CLI override should take precedence
                assert config.persona == "skeptic"
                # File value should be used where no override
                assert config.language == "zh-en"
                # Default should be used where no file/CLI override
                assert config.llm_provider == "openai"
