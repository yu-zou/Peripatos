"""Packaging tests — assert prompts ship as installable package resources.

These tests guard against the failure mode where prompts/ lived outside
the package and failed to ship in the wheel (fixed in d558314).
Using importlib.resources.files() ensures these tests work identically
whether running from source tree or from an installed wheel.
"""
from importlib.resources import files

EXPECTED_ARCHETYPES = ["enthusiast", "peer", "skeptic", "tutor"]
EXPECTED_AUDIO_FILES = ["intro.mp3", "outro.mp3"]


def test_archetype_yaml_files_are_package_resources():
    """All archetype YAML files must be reachable as package resources."""
    prompts_dir = files("peripatos_core") / "prompts" / "archetypes"
    for name in EXPECTED_ARCHETYPES:
        resource = prompts_dir / f"{name}.yaml"
        assert resource.is_file(), f"Missing package resource: {resource}"


def test_archetype_yaml_files_have_content():
    """YAML files must be non-empty and parseable with required fields."""
    import yaml

    prompts_dir = files("peripatos_core") / "prompts" / "archetypes"
    for name in EXPECTED_ARCHETYPES:
        data = yaml.safe_load((prompts_dir / f"{name}.yaml").read_text())
        assert isinstance(data, dict)
        assert {"archetype", "host_name", "guest_name", "system_prompt", "dialogue_prompt"} <= data.keys()


def test_audio_mp3_files_are_package_resources():
    """Intro and outro MP3 files must be reachable as package resources."""
    audio_dir = files("peripatos_core") / "audio"
    for name in EXPECTED_AUDIO_FILES:
        resource = audio_dir / name
        assert resource.is_file(), f"Missing package resource: {resource}"
