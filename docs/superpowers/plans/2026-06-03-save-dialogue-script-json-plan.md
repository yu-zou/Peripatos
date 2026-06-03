# Save Dialogue Script JSON Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically save the generated dialogue script as JSON alongside the output MP3 file.

**Architecture:** After `gen.generate()` returns the script in `cmd_generate()`, serialize it via `dataclasses.asdict()` and write to `args.output.with_suffix(".json")`. Warn on failure, never abort.

**Tech Stack:** stdlib `json`, `dataclasses`, `logging`. No new dependencies.

---

### Task 1: Add script saving to CLI and write tests

**Files:**
- Modify: `peripatos_core/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Add `_save_script_json()` helper and integrate into `cmd_generate()`**

In `peripatos_core/cli.py`, add the helper function after the imports:

```python
def _save_script_json(script, output_path: Path) -> None:
    """Save a DialogueScript as JSON next to the output MP3.

    Writes to the same directory with .json extension.
    On failure, logs a warning but does not raise.
    """
    import logging
    logger = logging.getLogger(__name__)
    json_path = output_path.with_suffix(".json")
    try:
        from dataclasses import asdict
        import json
        json_path.write_text(
            json.dumps(asdict(script), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Script saved to %s", json_path)
    except Exception as exc:
        logger.warning("Could not save script JSON (%s): %s", json_path, exc)
```

In `cmd_generate()`, add a call right after `gen.generate()` returns the script and before the TTS synthesis:

```python
    script = gen.generate(
        paper_content=paper_content,
        archetype=args.archetype,
        title=metadata.title,
        metadata=metadata,
    )
    print(f"  Generated {len(script.turns)} turns: {script.title}")

    # NEW: Save script JSON
    _save_script_json(script, args.output)

    print("Synthesizing audio")
```

- [ ] **Step 2: Add test for `_save_script_json()`**

Add to `tests/test_cli.py` (import `Path` from `pathlib`, `_save_script_json` from `peripatos_core.cli`, and `DialogueScript`, `DialogueTurn`, `Chapter`, `ArchetypeId` from `peripatos_core.types`):

```python
def test_save_script_json_writes_file(tmp_path):
    """_save_script_json writes valid JSON next to output path."""
    from dataclasses import asdict
    import json
    from peripatos_core.cli import _save_script_json
    from peripatos_core.types import DialogueScript, DialogueTurn, Chapter, ArchetypeId

    script = DialogueScript(
        title="Test Paper",
        chapters=[
            Chapter(
                title="Intro",
                turns=[
                    DialogueTurn(speaker="Host", text="Hello", archetype=ArchetypeId.PEER),
                    DialogueTurn(speaker="Guest", text="Hi", archetype=ArchetypeId.PEER),
                ],
            )
        ],
        intro_turns=[],
        outro_turns=[],
    )
    output_path = tmp_path / "podcast.mp3"
    _save_script_json(script, output_path)

    json_path = tmp_path / "podcast.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text())
    assert data["title"] == "Test Paper"
    assert len(data["chapters"]) == 1
    assert len(data["chapters"][0]["turns"]) == 2


def test_save_script_json_warns_on_failure(tmp_path, monkeypatch, caplog):
    """_save_script_json logs a warning on write failure but does not raise."""
    from peripatos_core.cli import _save_script_json
    from peripatos_core.types import DialogueScript, DialogueTurn, Chapter, ArchetypeId

    script = DialogueScript(
        title="Test",
        chapters=[Chapter(title="C", turns=[DialogueTurn(speaker="H", text="T", archetype=ArchetypeId.PEER)])],
        intro_turns=[],
        outro_turns=[],
    )
    # Point output to a read-only directory
    read_only = tmp_path / "readonly"
    read_only.mkdir()
    read_only.chmod(0o000)
    output_path = read_only / "podcast.mp3"

    _save_script_json(script, output_path)

    assert "Could not save script JSON" in caplog.text
    # Clean up for pytest
    read_only.chmod(0o755)
```

- [ ] **Step 3: Run the tests**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/test_cli.py::test_save_script_json_writes_file tests/test_cli.py::test_save_script_json_warns_on_failure -v
```

Expected: Both PASS.

- [ ] **Step 4: Run full test suite to verify no regressions**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/ --ignore=tests/test_e2e.py --ignore=tests/test_http_retry.py -m "not integration" --tb=short
```

Expected: All PASS (should be ~174+ tests).

- [ ] **Step 5: Commit**

```bash
git add peripatos_core/cli.py tests/test_cli.py
git commit -m "feat: save dialogue script JSON next to output MP3"
```
