"""Configuration management for Peripatos."""
import os
import importlib
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable, Mapping
from typing import cast

# Valid configuration values
VALID_PERSONAS = {"skeptic", "enthusiast", "tutor", "peer"}
VALID_LANGUAGES = {"en", "zh-en"}
VALID_LLM_PROVIDERS = {"openai", "anthropic", "openrouter", "gemini"}
VALID_TTS_ENGINES = {"openai", "edge-tts"}

# Default configuration
DEFAULT_CONFIG = {
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


def get_config_path() -> Path:
    """Get the configuration file path.
    
    Returns:
        Path to ~/.peripatos/config.yaml
    """
    return Path.home() / ".peripatos" / "config.yaml"


def create_default_config(config_path: Path) -> None:
    """Create default config file if it doesn't exist.
    
    Args:
        config_path: Path to the config file to create.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(config_path, "w") as f:
        yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False)


def load_yaml_config(config_path: Path) -> dict[str, object]:
    """Load YAML configuration from file.
    
    Args:
        config_path: Path to the config file.
        
    Returns:
        Dictionary with configuration data.
    """
    if not config_path.exists():
        return {}
    
    with open(config_path, "r") as f:
        data = cast(object, yaml.safe_load(f))
        if isinstance(data, dict):
            return cast(dict[str, object], data)
        return {}


def merge_configs(*configs: Mapping[str, object]) -> dict[str, object]:
    """Merge multiple configuration dictionaries with later ones taking precedence.
    
    Args:
        *configs: Configuration dictionaries to merge.
        
    Returns:
        Merged configuration dictionary.
    """
    result: dict[str, object] = {}
    for config in configs:
        if config:
            result = _deep_merge(result, dict(config))
    return result


def _deep_merge(base: dict[str, object], overlay: dict[str, object]) -> dict[str, object]:
    """Deep merge overlay dictionary into base.
    
    Args:
        base: Base configuration dictionary.
        overlay: Configuration to overlay on top.
        
    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in overlay.items():
        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(value, dict):
            result[key] = _deep_merge(
                cast(dict[str, object], base_value),
                cast(dict[str, object], value),
            )
        else:
            result[key] = value
    return result


@dataclass
class PeripatosConfig:
    """Configuration for Peripatos application.
    
    Attributes:
        llm_provider: LLM provider (openai, anthropic, openrouter, or gemini).
        llm_model: Model name for the LLM.
        tts_engine: TTS engine (openai or edge-tts).
        tts_voice_host: Voice name for host persona.
        tts_voice_expert: Voice name for expert persona.
        persona: Selected persona (skeptic, enthusiast, tutor, or peer).
        language: Language setting (en or zh-en).
        output_dir: Directory for output files.
        openai_api_key: OpenAI API key from environment.
        anthropic_api_key: Anthropic API key from environment.
        openrouter_api_key: OpenRouter API key from environment.
        gemini_api_key: Gemini API key from environment.
    """
    
    llm_provider: str
    llm_model: str
    tts_engine: str
    tts_voice_host: str
    tts_voice_expert: str
    persona: str
    language: str
    output_dir: str
    openai_api_key: str | None = field(default=None)
    anthropic_api_key: str | None = field(default=None)
    openrouter_api_key: str | None = field(default=None)
    gemini_api_key: str | None = field(default=None)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        if self.persona not in VALID_PERSONAS:
            message = (
                f"Invalid persona '{self.persona}'. "
                + f"Must be one of: {', '.join(sorted(VALID_PERSONAS))}"
            )
            raise ValueError(message)
        
        if self.language not in VALID_LANGUAGES:
            message = (
                f"Invalid language '{self.language}'. "
                + f"Must be one of: {', '.join(sorted(VALID_LANGUAGES))}"
            )
            raise ValueError(message)
        
        if self.llm_provider not in VALID_LLM_PROVIDERS:
            message = (
                f"Invalid LLM provider '{self.llm_provider}'. "
                + f"Must be one of: {', '.join(sorted(VALID_LLM_PROVIDERS))}"
            )
            raise ValueError(message)
        
        if self.tts_engine not in VALID_TTS_ENGINES:
            message = (
                f"Invalid TTS engine '{self.tts_engine}'. "
                + f"Must be one of: {', '.join(sorted(VALID_TTS_ENGINES))}"
            )
            raise ValueError(message)
    
    def validate_api_keys(self) -> None:
        """Validate that required API keys are present.
        
        Raises:
            ValueError: If required API key is missing for the selected provider.
        """
        if self.llm_provider == "openai" and not self.openai_api_key:
            message = (
                "OPENAI_API_KEY environment variable is not set. "
                + "Please add it to your .env file or set it in your environment."
            )
            raise ValueError(message)
        
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            message = (
                "ANTHROPIC_API_KEY environment variable is not set. "
                + "Please add it to your .env file or set it in your environment."
            )
            raise ValueError(message)
        
        if self.llm_provider == "openrouter" and not self.openrouter_api_key:
            message = (
                "OPENROUTER_API_KEY environment variable is not set. "
                + "Please add it to your .env file or set it in your environment."
            )
            raise ValueError(message)
        
        if self.llm_provider == "gemini" and not self.gemini_api_key:
            message = (
                "GEMINI_API_KEY environment variable is not set. "
                + "Please add it to your .env file or set it in your environment."
            )
            raise ValueError(message)


def load_config(cli_overrides: Mapping[str, object] | None = None) -> PeripatosConfig:
    """Load and merge configuration from multiple sources.
    
    Configuration priority (later wins):
    1. Defaults
    2. YAML config file (~/.peripatos/config.yaml)
    3. Environment variables
    4. CLI overrides
    
    Args:
        cli_overrides: Dictionary of CLI overrides to apply.
        
    Returns:
        PeripatosConfig instance with merged configuration.
        
    Raises:
        ValueError: If configuration is invalid.
    """
    # Load .env file
    dotenv_module = importlib.import_module("dotenv")
    load_dotenv = cast(Callable[[], object], getattr(dotenv_module, "load_dotenv"))
    _ = load_dotenv()
    
    # Get config file path
    config_path = get_config_path()
    
    # Create default config if it doesn't exist
    if not config_path.exists():
        create_default_config(config_path)
    
    # Load YAML configuration
    yaml_config = load_yaml_config(config_path)
    
    # Merge configurations: defaults → yaml → env → cli
    merged = merge_configs(
        cast(Mapping[str, object], DEFAULT_CONFIG),
        cast(Mapping[str, object], yaml_config),
    )
    
    # Extract nested values from merged config
    llm_config = cast(dict[str, object], merged.get("llm", {}))
    tts_config = cast(dict[str, object], merged.get("tts", {}))

    default_llm = cast(dict[str, str], DEFAULT_CONFIG["llm"])
    default_tts = cast(dict[str, str], DEFAULT_CONFIG["tts"])

    def _get_str(source: dict[str, object], key: str, default: str) -> str:
        value = source.get(key)
        return value if isinstance(value, str) else default
    
    # Prepare config dict
    config_dict: dict[str, object] = {
        "llm_provider": _get_str(llm_config, "provider", default_llm["provider"]),
        "llm_model": _get_str(llm_config, "model", default_llm["model"]),
        "tts_engine": _get_str(tts_config, "engine", default_tts["engine"]),
        "tts_voice_host": _get_str(tts_config, "voice_host", default_tts["voice_host"]),
        "tts_voice_expert": _get_str(
            tts_config, "voice_expert", default_tts["voice_expert"]
        ),
        "persona": _get_str(merged, "persona", cast(str, DEFAULT_CONFIG["persona"])),
        "language": _get_str(merged, "language", cast(str, DEFAULT_CONFIG["language"])),
        "output_dir": _get_str(merged, "output_dir", cast(str, DEFAULT_CONFIG["output_dir"])),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
        "gemini_api_key": os.getenv("GEMINI_API_KEY"),
    }
    
    # Apply CLI overrides
    if cli_overrides:
        for key, value in cli_overrides.items():
            if isinstance(value, str):
                config_dict[key] = value
    
    # Create and return config object
    return PeripatosConfig(
        llm_provider=cast(str, config_dict["llm_provider"]),
        llm_model=cast(str, config_dict["llm_model"]),
        tts_engine=cast(str, config_dict["tts_engine"]),
        tts_voice_host=cast(str, config_dict["tts_voice_host"]),
        tts_voice_expert=cast(str, config_dict["tts_voice_expert"]),
        persona=cast(str, config_dict["persona"]),
        language=cast(str, config_dict["language"]),
        output_dir=cast(str, config_dict["output_dir"]),
        openai_api_key=cast(str | None, config_dict["openai_api_key"]),
        anthropic_api_key=cast(str | None, config_dict["anthropic_api_key"]),
        openrouter_api_key=cast(str | None, config_dict["openrouter_api_key"]),
        gemini_api_key=cast(str | None, config_dict["gemini_api_key"]),
    )
