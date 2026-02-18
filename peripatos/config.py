"""Configuration management for Peripatos."""
import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

from dotenv import load_dotenv

# Valid configuration values
VALID_PERSONAS = {"skeptic", "enthusiast", "tutor", "peer"}
VALID_LANGUAGES = {"en", "zh-en"}
VALID_LLM_PROVIDERS = {"openai", "anthropic"}
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


def load_yaml_config(config_path: Path) -> dict:
    """Load YAML configuration from file.
    
    Args:
        config_path: Path to the config file.
        
    Returns:
        Dictionary with configuration data.
    """
    if not config_path.exists():
        return {}
    
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
        return data or {}


def merge_configs(*configs: dict) -> dict:
    """Merge multiple configuration dictionaries with later ones taking precedence.
    
    Args:
        *configs: Configuration dictionaries to merge.
        
    Returns:
        Merged configuration dictionary.
    """
    result = {}
    for config in configs:
        if config:
            result = _deep_merge(result, config)
    return result


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge overlay dictionary into base.
    
    Args:
        base: Base configuration dictionary.
        overlay: Configuration to overlay on top.
        
    Returns:
        Merged dictionary.
    """
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@dataclass
class PeripatosConfig:
    """Configuration for Peripatos application.
    
    Attributes:
        llm_provider: LLM provider (openai or anthropic).
        llm_model: Model name for the LLM.
        tts_engine: TTS engine (openai or edge-tts).
        tts_voice_host: Voice name for host persona.
        tts_voice_expert: Voice name for expert persona.
        persona: Selected persona (skeptic, enthusiast, tutor, or peer).
        language: Language setting (en or zh-en).
        output_dir: Directory for output files.
        openai_api_key: OpenAI API key from environment.
        anthropic_api_key: Anthropic API key from environment.
    """
    
    llm_provider: str
    llm_model: str
    tts_engine: str
    tts_voice_host: str
    tts_voice_expert: str
    persona: str
    language: str
    output_dir: str
    openai_api_key: Optional[str] = field(default=None)
    anthropic_api_key: Optional[str] = field(default=None)
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()
    
    def _validate(self):
        """Validate configuration values."""
        if self.persona not in VALID_PERSONAS:
            raise ValueError(
                f"Invalid persona '{self.persona}'. "
                f"Must be one of: {', '.join(sorted(VALID_PERSONAS))}"
            )
        
        if self.language not in VALID_LANGUAGES:
            raise ValueError(
                f"Invalid language '{self.language}'. "
                f"Must be one of: {', '.join(sorted(VALID_LANGUAGES))}"
            )
        
        if self.llm_provider not in VALID_LLM_PROVIDERS:
            raise ValueError(
                f"Invalid LLM provider '{self.llm_provider}'. "
                f"Must be one of: {', '.join(sorted(VALID_LLM_PROVIDERS))}"
            )
        
        if self.tts_engine not in VALID_TTS_ENGINES:
            raise ValueError(
                f"Invalid TTS engine '{self.tts_engine}'. "
                f"Must be one of: {', '.join(sorted(VALID_TTS_ENGINES))}"
            )
    
    def validate_api_keys(self) -> None:
        """Validate that required API keys are present.
        
        Raises:
            ValueError: If required API key is missing for the selected provider.
        """
        if self.llm_provider == "openai" and not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please add it to your .env file or set it in your environment."
            )
        
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Please add it to your .env file or set it in your environment."
            )


def load_config(cli_overrides: Optional[dict] = None) -> PeripatosConfig:
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
    load_dotenv()
    
    # Get config file path
    config_path = get_config_path()
    
    # Create default config if it doesn't exist
    if not config_path.exists():
        create_default_config(config_path)
    
    # Load YAML configuration
    yaml_config = load_yaml_config(config_path)
    
    # Merge configurations: defaults → yaml → env → cli
    merged = merge_configs(DEFAULT_CONFIG, yaml_config)
    
    # Extract nested values from merged config
    llm_config = merged.get("llm", {})
    tts_config = merged.get("tts", {})
    
    # Prepare config dict
    config_dict = {
        "llm_provider": llm_config.get("provider", DEFAULT_CONFIG["llm"]["provider"]),
        "llm_model": llm_config.get("model", DEFAULT_CONFIG["llm"]["model"]),
        "tts_engine": tts_config.get("engine", DEFAULT_CONFIG["tts"]["engine"]),
        "tts_voice_host": tts_config.get("voice_host", DEFAULT_CONFIG["tts"]["voice_host"]),
        "tts_voice_expert": tts_config.get("voice_expert", DEFAULT_CONFIG["tts"]["voice_expert"]),
        "persona": merged.get("persona", DEFAULT_CONFIG["persona"]),
        "language": merged.get("language", DEFAULT_CONFIG["language"]),
        "output_dir": merged.get("output_dir", DEFAULT_CONFIG["output_dir"]),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
    }
    
    # Apply CLI overrides
    if cli_overrides:
        config_dict.update(cli_overrides)
    
    # Create and return config object
    return PeripatosConfig(**config_dict)
