import pytest
import yaml
from peripatos_core.archetypes import ArchetypeLoader, ArchetypePrompt
from peripatos_core.types import ArchetypeId
from peripatos_core.exceptions import ConfigError


def test_load_all_four_archetypes():
    loader = ArchetypeLoader()
    for archetype in ArchetypeId:
        prompt = loader.load(archetype)
        assert isinstance(prompt, ArchetypePrompt)
        assert prompt.archetype == archetype.value
        assert len(prompt.system_prompt) > 10
        assert "{paper_content}" in prompt.dialogue_prompt


def test_load_by_string():
    loader = ArchetypeLoader()
    prompt = loader.load("proxy_host")
    assert prompt.archetype == "proxy_host"


def test_load_missing_raises(tmp_path):
    loader = ArchetypeLoader(prompts_dir=tmp_path)
    with pytest.raises(ConfigError, match="not found"):
        loader.load("proxy_host")


def test_load_malformed_yaml_raises(tmp_path):
    bad = tmp_path / "proxy_host.yaml"
    bad.write_text(": invalid: yaml: [")
    loader = ArchetypeLoader(prompts_dir=tmp_path)
    with pytest.raises(ConfigError):
        loader.load("proxy_host")


def test_load_missing_fields_raises(tmp_path):
    incomplete = tmp_path / "proxy_host.yaml"
    incomplete.write_text(yaml.dump({"archetype": "proxy_host"}))
    loader = ArchetypeLoader(prompts_dir=tmp_path)
    with pytest.raises(ConfigError, match="missing fields"):
        loader.load("proxy_host")


def test_list_available():
    loader = ArchetypeLoader()
    available = loader.list_available()
    assert set(available) >= {"proxy_host", "author_persona", "devils_advocate", "domain_expert"}
