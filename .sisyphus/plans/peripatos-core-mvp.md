# Peripatos Core MVP — Build from Scratch

## TL;DR

> **Quick Summary**: Build `peripatos-core`, an open-source (MIT) Python CLI tool that converts academic research papers (ArXiv / local PDF) into interactive two-persona Socratic audio dialogues. The pipeline: PDF → Markdown (Docling) → Dialogue Script (LLM) → Audio MP3 with chapters (OpenAI TTS / edge-tts fallback).
> 
> **Deliverables**:
> - Pip-installable Python package (`peripatos`)
> - CLI interface: `peripatos generate <arxiv_id_or_pdf_path>`
> - Full pipeline: ingestion → parsing → script generation → audio rendering
> - 4 persona archetypes: Skeptic, Enthusiast, Tutor, Peer
> - Bilingual code-switching (Chinese + English)
> - Chapter-marked MP3 output
> - BYOK (Bring Your Own Key) for OpenAI/Anthropic
> - Test suite with pytest (TDD)
> 
> **Estimated Effort**: Large
> **Parallel Execution**: YES — 4 waves
> **Critical Path**: Task 1 (scaffold) → Task 3 (types) → Task 5 (parsing) → Task 8 (dialogue gen) → Task 11 (audio render) → Task 13 (mixer) → Task 14 (CLI orchestrator) → Task 16 (E2E integration test)

---

## Context

### Original Request
User wants to build the Peripatos project from scratch. Design documents in `design_guideline/` describe a two-component system (core engine + web platform). We scoped this plan to **Phase 1 only**: the `peripatos-core` open-source CLI.

### Interview Summary
**Key Discussions**:
- **Scope**: Phase 1 CLI MVP only. No web platform, no SaaS layer.
- **PDF Parser**: Switched from `marker-pdf` (GPL-3.0 blocker) to `docling` (MIT, IBM-backed, 53.4k stars).
- **Scholar Profile**: Deferred — `scholarly` library too unreliable (3-year stale, 40-60% failure rate). Will revisit in future phase.
- **Personas**: All 4 archetypes from day one (Skeptic, Enthusiast, Tutor, Peer).
- **Audio**: OpenAI TTS primary, `edge-tts` as fallback. No ElevenLabs in Phase 1.
- **Code-Switching**: Chinese + English first pair, extensible later.
- **CLI**: argparse (stdlib). Config via `.env` + `~/.peripatos/config.yaml`.
- **Testing**: TDD with pytest.
- **License**: MIT.

**Research Findings**:
- **Docling** has a simple API: `DocumentConverter().convert(source).document.export_to_markdown()`. Supports URLs (including ArXiv), local PDFs, formula enrichment, OCR, and table structure.
- **OpenAI TTS** has a 4096 character limit per request — dialogue segments must be chunked at sentence boundaries.
- **edge-tts** (Python, by rany2) supports many voices including Chinese, uses Microsoft Edge's TTS service, async API.
- **ffmpeg** supports chapter metadata injection — needed for podcast player navigation.

### Metis Review
**Identified Gaps** (addressed):
- **GPL-3.0 license blocker**: Resolved by switching to Docling (MIT).
- **scholarly unreliability**: Resolved by deferring scholar profile ingestion.
- **Math-to-speech pipeline underspecified**: Resolved — Docling has `do_formula_enrichment` option, plus we'll delegate LaTeX→phonetic conversion to the LLM during dialogue generation.
- **OpenAI TTS 4096 char limit**: Addressed in audio renderer design — smart chunking at sentence boundaries.
- **Unspecified naming**: Resolved — package name `peripatos`, CLI command `peripatos`.

---

## Work Objectives

### Core Objective
Build a pip-installable Python CLI tool that takes an ArXiv paper ID or local PDF path and produces a high-quality Socratic dialogue audio file (MP3 with chapter markers), using the user's own LLM and TTS API keys.

### Concrete Deliverables
- `peripatos/` Python package (pip-installable)
- CLI: `peripatos generate 2310.00123` or `peripatos generate ./paper.pdf`
- CLI: `peripatos generate --persona skeptic --language zh-en 2310.00123`
- Config file support: `~/.peripatos/config.yaml`
- BYOK: `.env` for API keys
- MP3 output with embedded chapter markers
- 4 persona modes: Skeptic, Enthusiast, Tutor, Peer
- Bilingual mode: Chinese narrative + English technical terms
- pytest test suite

### Definition of Done
- [ ] `pip install -e .` succeeds from repo root
- [ ] `peripatos generate <arxiv_id>` produces a valid MP3 file
- [ ] `peripatos generate <local_pdf>` produces a valid MP3 file
- [ ] MP3 has chapter markers readable by ffprobe
- [ ] All 4 persona modes produce distinctly different dialogue styles
- [ ] `--language zh-en` produces Chinese+English code-switched output
- [ ] `pytest` passes with >80% coverage on core logic
- [ ] MIT LICENSE file present at repo root

### Must Have
- Working end-to-end pipeline (PDF → audio) for both ArXiv and local PDF inputs
- Two distinct voices in the audio (Host vs Expert)
- All 4 persona archetypes with distinct prompt behavior
- Chapter markers in output MP3
- edge-tts fallback when OpenAI TTS key is not provided
- BYOK — never hardcode API keys
- Clean error messages when API keys are missing
- MIT license

### Must NOT Have (Guardrails)
- **NO web server or HTTP endpoints** — this is a CLI tool only
- **NO database** — no PostgreSQL, SQLite, or any persistent storage
- **NO user authentication** — no accounts, no sessions
- **NO marker-pdf** — GPL-3.0 incompatible with MIT license
- **NO scholarly** — unreliable, deferred to future phase
- **NO ElevenLabs integration** — Phase 3 feature
- **NO RSS feed generation** — Phase 3 feature
- **NO hardcoded API keys** in source code or committed to git
- **NO over-abstraction** — avoid creating abstract base classes or factory patterns unless there are 3+ concrete implementations
- **NO excessive comments** — code should be self-documenting; only add comments for non-obvious logic
- **NO `as any` equivalent** — use proper Python type hints throughout
- **NO empty except blocks** — always handle or re-raise with context

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: NO (fresh repo, setting up from scratch)
- **Automated tests**: TDD — write tests first, then implement
- **Framework**: pytest
- **Structure**: Each pipeline module gets its own test file. Integration tests for end-to-end flow.

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

| Deliverable Type | Verification Tool | Method |
|------------------|-------------------|--------|
| Python package | Bash (pip, python) | Install, import, verify modules |
| CLI commands | interactive_bash (tmux) / Bash | Run CLI, check output files |
| Audio output | Bash (ffprobe, ffmpeg) | Validate MP3 metadata, duration, chapters |
| Config loading | Bash (python -c) | Test config file parsing |
| LLM integration | Bash (pytest with mocks) | Verify prompt construction, response parsing |

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — project scaffolding + foundation):
├── Task 1: Project scaffolding (pyproject.toml, directory structure, LICENSE) [quick]
├── Task 2: Configuration system (.env + config.yaml loading) [quick]
├── Task 3: Core type definitions & data models [quick]
└── Task 4: Test infrastructure setup (pytest, fixtures, sample data) [quick]

Wave 2 (After Wave 1 — pipeline modules, MAX PARALLEL):
├── Task 5: The "Eye" — PDF parser module (Docling integration) [deep]
├── Task 6: The "Eye" — ArXiv fetcher module [quick]
├── Task 7: Math normalization (LaTeX → spoken text) [unspecified-high]
├── Task 8: The "Brain" — Dialogue script generator (LLM prompts + 4 personas) [deep]
├── Task 9: The "Voice" — OpenAI TTS engine [unspecified-high]
└── Task 10: The "Voice" — edge-tts fallback engine [quick]

Wave 3 (After Wave 2 — integration + mixing):
├── Task 11: Audio renderer orchestrator (TTS engine selection + chunking) [deep]
├── Task 12: Bilingual code-switching (Chinese + English) [unspecified-high]
├── Task 13: The "Mixer" — audio stitching + chapter markers (ffmpeg) [unspecified-high]
└── Task 14: CLI orchestrator (argparse + end-to-end pipeline wiring) [deep]

Wave 4 (After Wave 3 — packaging + final verification):
├── Task 15: Package distribution (pip install, entry points) [quick]
├── Task 16: End-to-end integration tests [deep]
└── Task 17: Documentation (README.md, usage examples) [writing]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: T1 → T3 → T5 → T8 → T11 → T13 → T14 → T16 → FINAL
Parallel Speedup: ~65% faster than sequential
Max Concurrent: 6 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|------------|--------|------|
| 1 | — | 2, 3, 4, 5, 6, 7, 8, 9, 10 | 1 |
| 2 | 1 | 8, 9, 10, 14 | 1 |
| 3 | 1 | 5, 6, 7, 8, 9, 10, 11 | 1 |
| 4 | 1 | 5, 6, 7, 8, 9, 10 | 1 |
| 5 | 1, 3, 4 | 7, 11, 14 | 2 |
| 6 | 1, 3, 4 | 14 | 2 |
| 7 | 3, 4, 5 | 8 | 2 |
| 8 | 2, 3, 4, 7 | 11, 12, 14 | 2 |
| 9 | 2, 3, 4 | 11 | 2 |
| 10 | 2, 3, 4 | 11 | 2 |
| 11 | 3, 8, 9, 10 | 13, 14 | 3 |
| 12 | 8 | 14 | 3 |
| 13 | 11 | 14 | 3 |
| 14 | 2, 5, 6, 8, 11, 12, 13 | 15, 16 | 3 |
| 15 | 14 | 16 | 4 |
| 16 | 14, 15 | F1-F4 | 4 |
| 17 | 14 | — | 4 |
| F1-F4 | 15, 16, 17 | — | FINAL |

### Agent Dispatch Summary

| Wave | # Parallel | Tasks → Agent Category |
|------|------------|----------------------|
| 1 | **4** | T1 → `quick`, T2 → `quick`, T3 → `quick`, T4 → `quick` |
| 2 | **6** | T5 → `deep`, T6 → `quick`, T7 → `unspecified-high`, T8 → `deep`, T9 → `unspecified-high`, T10 → `quick` |
| 3 | **4** | T11 → `deep`, T12 → `unspecified-high`, T13 → `unspecified-high`, T14 → `deep` |
| 4 | **3** | T15 → `quick`, T16 → `deep`, T17 → `writing` |
| FINAL | **4** | F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep` |

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.

### Wave 1 — Project Scaffolding & Foundation

- [x] 1. Project Scaffolding

  **What to do**:
  - Create the project directory structure:
    ```
    peripatos/
    ├── peripatos/
    │   ├── __init__.py          # Package init, __version__
    │   ├── cli.py               # (placeholder) CLI entry point
    │   ├── models.py            # (placeholder) Data models
    │   ├── config.py            # (placeholder) Configuration
    │   ├── eye/                  # Ingestion & Parsing module
    │   │   ├── __init__.py
    │   │   ├── parser.py        # (placeholder) PDF parser
    │   │   ├── arxiv.py         # (placeholder) ArXiv fetcher
    │   │   └── math_normalize.py # (placeholder) Math normalization
    │   ├── brain/                # Script Generation module
    │   │   ├── __init__.py
    │   │   ├── generator.py     # (placeholder) Dialogue generator
    │   │   ├── personas.py      # (placeholder) Persona definitions
    │   │   └── bilingual.py     # (placeholder) Code-switching
    │   └── voice/                # Audio Rendering module
    │       ├── __init__.py
    │       ├── openai_tts.py    # (placeholder) OpenAI TTS engine
    │       ├── edge_tts_engine.py # (placeholder) edge-tts fallback
    │       ├── renderer.py      # (placeholder) Audio renderer orchestrator
    │       └── mixer.py         # (placeholder) Audio mixer + chapters
    ├── tests/
    │   ├── __init__.py
    │   └── conftest.py          # (placeholder) Shared fixtures
    ├── pyproject.toml            # Project metadata, dependencies, entry points
    ├── LICENSE                   # MIT license
    ├── .env.example              # Example env file with required keys
    └── .gitignore                # Python-specific ignores
    ```
  - Write `pyproject.toml` with:
    - Package name: `peripatos`
    - Python requires: `>=3.10`
    - Dependencies: `docling`, `pydub`, `edge-tts`, `openai`, `anthropic`, `python-dotenv`, `pyyaml`
    - Dev dependencies: `pytest`, `pytest-cov`, `pytest-asyncio`
    - Entry point: `[project.scripts] peripatos = "peripatos.cli:main"`
    - Version: `0.1.0`
  - Write MIT LICENSE file with current year and "Peripatos Contributors"
  - Write `.env.example` with: `OPENAI_API_KEY=`, `ANTHROPIC_API_KEY=`
  - Update `.gitignore` for Python (venv, __pycache__, .env, dist/, *.egg-info, output/)
  - Write placeholder `__init__.py` with `__version__ = "0.1.0"`
  - **TDD**: Write `tests/test_package.py` with:
    - Test: `import peripatos` succeeds
    - Test: `peripatos.__version__` equals `"0.1.0"`
  - Run `pip install -e .` to validate

  **Must NOT do**:
  - Do NOT add any implementation logic — only structure and placeholders
  - Do NOT add marker-pdf or scholarly to dependencies
  - Do NOT add any web framework dependencies

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: File creation and boilerplate, no complex logic
  - **Skills**: []
    - No specialized skills needed for scaffolding
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed
    - `frontend-ui-ux`: No UI work

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T2, T3, T4 after independent portions — but T1 must complete first as it creates the directory structure)
  - **Parallel Group**: Wave 1 — starts first, others follow immediately
  - **Blocks**: T2, T3, T4, T5, T6, T7, T8, T9, T10
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:13-16` — Tech stack specification (Python 3.10+, CLI dependencies list). Use to confirm dependency names.
  - `design_guideline/design.md:5` — Module naming: "peripatos-core" is the engine component name. Package name should be `peripatos`.

  **External References**:
  - Python Packaging Guide: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/ — Use `[project]` table format (PEP 621), not legacy setup.py
  - MIT License template: https://opensource.org/licenses/MIT

  **WHY Each Reference Matters**:
  - The design doc's tech stack list is the authoritative source for which dependencies to include — don't deviate
  - The packaging guide ensures pyproject.toml follows current best practices (PEP 621 format)

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_package.py`
  - [ ] `pytest tests/test_package.py` → PASS (2 tests: import + version)

  **QA Scenarios:**

  ```
  Scenario: Fresh install from source
    Tool: Bash
    Preconditions: Clean Python 3.10+ virtual environment
    Steps:
      1. Run: python -m venv .venv && source .venv/bin/activate
      2. Run: pip install -e ".[dev]"
      3. Run: python -c "import peripatos; print(peripatos.__version__)"
    Expected Result: Prints "0.1.0" with exit code 0
    Failure Indicators: ImportError, ModuleNotFoundError, wrong version
    Evidence: .sisyphus/evidence/task-1-fresh-install.txt

  Scenario: Directory structure validation
    Tool: Bash
    Preconditions: After pip install -e .
    Steps:
      1. Run: find peripatos -name "*.py" | sort
      2. Verify output contains: peripatos/__init__.py, peripatos/cli.py, peripatos/models.py, peripatos/config.py, peripatos/eye/__init__.py, peripatos/eye/parser.py, peripatos/eye/arxiv.py, peripatos/eye/math_normalize.py, peripatos/brain/__init__.py, peripatos/brain/generator.py, peripatos/brain/personas.py, peripatos/brain/bilingual.py, peripatos/voice/__init__.py, peripatos/voice/openai_tts.py, peripatos/voice/edge_tts_engine.py, peripatos/voice/renderer.py, peripatos/voice/mixer.py
      3. Run: cat LICENSE | head -1
      4. Verify: Contains "MIT License"
    Expected Result: All files present, LICENSE is MIT
    Failure Indicators: Missing files, wrong license
    Evidence: .sisyphus/evidence/task-1-structure.txt

  Scenario: Missing forbidden dependencies
    Tool: Bash
    Preconditions: After scaffolding
    Steps:
      1. Run: grep -r "marker" pyproject.toml
      2. Run: grep -r "scholarly" pyproject.toml
      3. Run: grep -r "elevenlabs" pyproject.toml
    Expected Result: All grep commands return empty (exit code 1)
    Failure Indicators: Any grep returns a match
    Evidence: .sisyphus/evidence/task-1-no-forbidden-deps.txt
  ```

  **Commit**: YES
  - Message: `chore: scaffold peripatos-core project structure`
  - Files: `pyproject.toml, peripatos/**, tests/**, LICENSE, .env.example, .gitignore`
  - Pre-commit: `pytest tests/test_package.py`

- [x] 2. Configuration System (.env + config.yaml)

  **What to do**:
  - Implement `peripatos/config.py`:
    - Load API keys from `.env` file using `python-dotenv` (OPENAI_API_KEY, ANTHROPIC_API_KEY)
    - Load user preferences from `~/.peripatos/config.yaml` using `PyYAML`
    - Config YAML schema:
      ```yaml
      # ~/.peripatos/config.yaml
      llm:
        provider: openai  # or "anthropic"
        model: gpt-4o     # model name
      tts:
        engine: openai    # or "edge-tts"
        voice_host: "alloy"     # OpenAI voice for Host persona
        voice_expert: "onyx"    # OpenAI voice for Expert persona
      persona: tutor      # default persona: skeptic|enthusiast|tutor|peer
      language: en        # "en" or "zh-en" for bilingual
      output_dir: ./output  # where to save generated audio
      ```
    - Implement a `PeripatosConfig` dataclass that merges: defaults → config file → env vars → CLI overrides (in that priority order)
    - Provide `load_config(cli_overrides: dict | None = None) -> PeripatosConfig` function
    - Create default config if `~/.peripatos/config.yaml` doesn't exist
    - Validate: raise clear error if required API key is missing for chosen provider
  - **TDD**: Write `tests/test_config.py` with:
    - Test: default config loads when no file exists
    - Test: YAML config file is parsed correctly
    - Test: .env API keys are loaded
    - Test: CLI overrides take precedence over config file
    - Test: missing API key raises `ValueError` with helpful message
    - Test: invalid persona value raises `ValueError`

  **Must NOT do**:
  - Do NOT store API keys in config.yaml — only in .env
  - Do NOT create a database or persistent state
  - Do NOT add ElevenLabs config options

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file module with straightforward config loading logic
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T3, T4 — after T1 completes)
  - **Parallel Group**: Wave 1 (with Tasks 3, 4)
  - **Blocks**: T8, T9, T10, T14
  - **Blocked By**: T1

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:29` — BYOK: "Reads API keys from local environment variables (`.env`)". This is the authoritative source for key loading.
  - `design_guideline/design.md:24` — Persona selection: "A logic layer that selects the Persona (Skeptic, Tutor, etc.) based on user config". Config must support persona selection.

  **External References**:
  - python-dotenv: https://pypi.org/project/python-dotenv/ — Use `load_dotenv()` and `os.getenv()`
  - PyYAML: https://pyyaml.org/wiki/PyYAMLDocumentation — Use `yaml.safe_load()`

  **WHY Each Reference Matters**:
  - Design doc specifies BYOK via .env — this is the contract the config module must honor
  - Persona config needs to match the 4 archetypes defined in the PRD

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_config.py`
  - [ ] `pytest tests/test_config.py` → PASS (6+ tests)

  **QA Scenarios:**

  ```
  Scenario: Config loads with defaults when no file exists
    Tool: Bash
    Preconditions: No ~/.peripatos/config.yaml, no .env
    Steps:
      1. Run: python -c "from peripatos.config import load_config; c = load_config(); print(c.persona, c.language)"
    Expected Result: Prints "tutor en" (defaults)
    Failure Indicators: ImportError, AttributeError, crash
    Evidence: .sisyphus/evidence/task-2-default-config.txt

  Scenario: Missing API key produces clear error
    Tool: Bash
    Preconditions: No .env file, config sets llm.provider=openai
    Steps:
      1. Run: python -c "from peripatos.config import load_config; c = load_config(); c.validate_api_keys()"
      2. Capture stderr
    Expected Result: ValueError raised with message containing "OPENAI_API_KEY"
    Failure Indicators: Silent failure, generic error, crash without message
    Evidence: .sisyphus/evidence/task-2-missing-key-error.txt
  ```

  **Commit**: YES
  - Message: `feat(config): add .env and YAML configuration system`
  - Files: `peripatos/config.py, tests/test_config.py, .env.example`
  - Pre-commit: `pytest tests/test_config.py`

- [x] 3. Core Type Definitions & Data Models

  **What to do**:
  - Implement `peripatos/models.py` with Python dataclasses (or Pydantic if preferred for validation — but stdlib dataclasses preferred for fewer deps):
    - `PaperMetadata`: title, authors, abstract, arxiv_id (optional), source_path, sections (list of SectionInfo)
    - `SectionInfo`: title, content (markdown string), section_type (enum: ABSTRACT, INTRODUCTION, METHODOLOGY, EXPERIMENTS, RESULTS, DISCUSSION, CONCLUSION, REFERENCES, OTHER)
    - `DialogueTurn`: speaker (enum: HOST, EXPERT), text, section_ref (which section this turn discusses)
    - `DialogueScript`: paper_metadata, turns (list of DialogueTurn), persona_type (enum), language_mode (enum: EN, ZH_EN)
    - `AudioSegment`: speaker, audio_bytes (bytes), duration_seconds (float), text (original text)
    - `ChapterMarker`: title, start_time_ms (int), end_time_ms (int)
    - `GeneratedPodcast`: paper_metadata, audio_path (Path), chapters (list of ChapterMarker), duration_seconds, persona_type
    - Enums: `PersonaType` (SKEPTIC, ENTHUSIAST, TUTOR, PEER), `SpeakerRole` (HOST, EXPERT), `LanguageMode` (EN, ZH_EN), `TTSEngine` (OPENAI, EDGE_TTS), `LLMProvider` (OPENAI, ANTHROPIC)
  - All models should have proper `__repr__` and type hints
  - **TDD**: Write `tests/test_models.py` with:
    - Test: each dataclass can be instantiated with valid data
    - Test: enums have all expected values
    - Test: `DialogueScript` correctly stores list of `DialogueTurn`s
    - Test: `PaperMetadata` works with and without optional arxiv_id

  **Must NOT do**:
  - Do NOT use Pydantic (adds heavy dependency for simple data classes)
  - Do NOT add database-related fields (no IDs, timestamps, user references)
  - Do NOT add fields for features we're not building (zotero, orcid, etc.)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Pure data class definitions with type hints, no complex logic
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T2, T4 — after T1 completes)
  - **Parallel Group**: Wave 1 (with Tasks 2, 4)
  - **Blocks**: T5, T6, T7, T8, T9, T10, T11
  - **Blocked By**: T1

  **References**:

  **Pattern References**:
  - `design_guideline/PRD.md:24-37` — Persona archetypes: Skeptic, Enthusiast, Tutor, Peer. Use these exact names for the enum.
  - `design_guideline/PRD.md:25-27` — Two-persona dynamic: "Proxy Host" and "Expert Author". Map to HOST and EXPERT speaker roles.
  - `design_guideline/design.md:25-26` — JSON transcript: "generate a JSON transcript". DialogueScript is this transcript's Python representation.
  - `design_guideline/PRD.md:23` — Section types: "Introduction, Methodology, Experiments, etc." — use these for the SectionType enum.

  **WHY Each Reference Matters**:
  - Persona names must match PRD exactly — these flow through to prompts and CLI options
  - Speaker roles (HOST/EXPERT) are the fundamental dialogue structure — every downstream module depends on this
  - Section types enable chapter markers in the final audio

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_models.py`
  - [ ] `pytest tests/test_models.py` → PASS (8+ tests)

  **QA Scenarios:**

  ```
  Scenario: All data models are importable and constructible
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "from peripatos.models import PaperMetadata, DialogueTurn, DialogueScript, AudioSegment, ChapterMarker, GeneratedPodcast, PersonaType, SpeakerRole, LanguageMode; print('All models imported')"
      2. Run: python -c "from peripatos.models import PersonaType; print([p.name for p in PersonaType])"
    Expected Result: First command prints "All models imported". Second prints "['SKEPTIC', 'ENTHUSIAST', 'TUTOR', 'PEER']"
    Failure Indicators: ImportError, missing class, wrong enum values
    Evidence: .sisyphus/evidence/task-3-models-import.txt
  ```

  **Commit**: YES
  - Message: `feat(types): add core data models and type definitions`
  - Files: `peripatos/models.py, tests/test_models.py`
  - Pre-commit: `pytest tests/test_models.py`

- [x] 4. Test Infrastructure Setup

  **What to do**:
  - Set up `tests/conftest.py` with shared pytest fixtures:
    - `sample_pdf_path`: fixture that provides path to a small test PDF (include a 1-page test PDF in `tests/fixtures/sample_paper.pdf` — find or create a simple academic-style PDF)
    - `sample_arxiv_id`: fixture returning a known ArXiv ID (e.g., `"2408.09869"` — Docling's own paper)
    - `mock_openai_key`: fixture that sets `OPENAI_API_KEY` env var to a test value
    - `mock_config`: fixture that returns a `PeripatosConfig` with test defaults
    - `tmp_output_dir`: fixture using `tmp_path` for generated audio output
    - `sample_markdown`: fixture returning a representative Markdown string (academic paper format with sections, equations)
    - `sample_dialogue_script`: fixture returning a pre-built `DialogueScript` object
  - Create `tests/fixtures/` directory with:
    - `sample_paper.pdf` — A small (1-2 page) PDF for testing. Can be a simple LaTeX-generated doc or a downloaded public domain paper.
    - `sample_config.yaml` — Test config file
    - `sample_dialogue.json` — Example dialogue script in JSON format
  - Configure `pyproject.toml` with pytest settings:
    ```toml
    [tool.pytest.ini_options]
    testpaths = ["tests"]
    asyncio_mode = "auto"
    ```
  - Verify: `pytest --co` lists all test files

  **Must NOT do**:
  - Do NOT use copyrighted papers as test fixtures — use public domain or self-generated
  - Do NOT create overly complex fixtures that hide test logic

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Boilerplate test setup, fixture creation
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T2, T3 — after T1 completes)
  - **Parallel Group**: Wave 1 (with Tasks 2, 3)
  - **Blocks**: T5, T6, T7, T8, T9, T10
  - **Blocked By**: T1

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:87-89` — Testing strategy: "Unit Tests for peripatos-core logic, Integration Tests end-to-end CLI run on sample PDF." Follow this structure.

  **External References**:
  - pytest fixtures: https://docs.pytest.org/en/stable/how-to/fixtures.html — Use session-scoped fixtures for expensive operations
  - pytest-asyncio: https://pytest-asyncio.readthedocs.io/ — Needed for edge-tts async tests

  **WHY Each Reference Matters**:
  - Design doc prescribes the test strategy — fixtures should enable both unit and integration tests
  - pytest-asyncio is needed because edge-tts is async

  **Acceptance Criteria**:

  **TDD:**
  - [ ] `pytest --co` → Lists all discovered test files without errors
  - [ ] `tests/fixtures/sample_paper.pdf` exists and is a valid PDF

  **QA Scenarios:**

  ```
  Scenario: Test discovery works
    Tool: Bash
    Preconditions: pip install -e ".[dev]"
    Steps:
      1. Run: pytest --co 2>&1
      2. Verify output contains: test_package.py, test_config.py, test_models.py
    Expected Result: All test files discovered, no collection errors
    Failure Indicators: Collection errors, missing files
    Evidence: .sisyphus/evidence/task-4-test-discovery.txt

  Scenario: Fixtures are loadable
    Tool: Bash
    Preconditions: After setup
    Steps:
      1. Run: python -c "import pathlib; assert pathlib.Path('tests/fixtures/sample_paper.pdf').exists(); print('PDF fixture exists')"
      2. Run: python -c "import yaml; c = yaml.safe_load(open('tests/fixtures/sample_config.yaml')); print(c)"
    Expected Result: Both commands succeed
    Failure Indicators: FileNotFoundError, yaml parse error
    Evidence: .sisyphus/evidence/task-4-fixtures.txt
  ```

  **Commit**: YES
  - Message: `test: set up pytest infrastructure with fixtures and sample data`
  - Files: `tests/conftest.py, tests/fixtures/**, pyproject.toml`
  - Pre-commit: `pytest --co`

### Wave 2 — Pipeline Modules (MAX PARALLEL)

- [x] 5. The "Eye" — PDF Parser Module (Docling Integration)

  **What to do**:
  - Implement `peripatos/eye/parser.py`:
    - `PDFParser` class with method `parse(source: str | Path) -> PaperMetadata`
    - Use Docling's `DocumentConverter` to convert PDF → Markdown
    - Configure Docling pipeline options:
      - `do_formula_enrichment = True` (for math/equation recognition)
      - `do_table_structure = True`
      - `do_ocr = True` (for scanned PDFs)
    - Parse the Markdown output into `PaperMetadata`:
      - Extract title from first heading
      - Extract authors (if detectable from first page)
      - Split content into `SectionInfo` objects based on heading hierarchy
      - Classify sections by type (Introduction, Methodology, etc.) using heading text matching
    - Handle errors: invalid PDF path, corrupted PDF, Docling failures → raise `ParsingError` with context
  - **TDD**: Write `tests/test_parser.py` with:
    - Test: valid PDF produces `PaperMetadata` with non-empty title and sections
    - Test: sections are correctly classified by type
    - Test: invalid path raises `ParsingError`
    - Test: Markdown output preserves equation content (check for LaTeX-like content)

  **Must NOT do**:
  - Do NOT import or use marker-pdf
  - Do NOT attempt to download papers from URLs in this module (that's ArXiv fetcher's job)
  - Do NOT do math-to-speech conversion here (that's Task 7)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Requires understanding Docling API, PDF parsing edge cases, section classification logic
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T6, T8, T9, T10)
  - **Parallel Group**: Wave 2
  - **Blocks**: T7, T11, T14
  - **Blocked By**: T1, T3, T4

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:19-22` — The "Eye" module spec: "Input: Local PDF path or ArXiv ID. Parsing: Uses [Docling] to convert PDF → Clean Markdown. Math Normalization: Custom Regex/LLM pass."
  - `peripatos/models.py` (from T3) — `PaperMetadata`, `SectionInfo`, `SectionType` — these are the output types this parser must produce.

  **External References**:
  - Docling basic usage: `from docling.document_converter import DocumentConverter; converter = DocumentConverter(); result = converter.convert(source); result.document.export_to_markdown()`
  - Docling pipeline options: `PdfPipelineOptions` with `do_formula_enrichment=True`, `do_table_structure=True`, `do_ocr=True`
  - Docling handles both local paths and URLs natively

  **WHY Each Reference Matters**:
  - Design doc defines the module boundary ("The Eye") — parser handles only PDF→structured data
  - Docling API is the core dependency — must use correctly for formula enrichment and layout handling
  - Models from T3 are the contract — parser output must conform exactly

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_parser.py`
  - [ ] `pytest tests/test_parser.py` → PASS (4+ tests)

  **QA Scenarios:**

  ```
  Scenario: Parse sample PDF to structured metadata
    Tool: Bash
    Preconditions: pip install -e ., sample PDF in tests/fixtures/
    Steps:
      1. Run: python -c "
         from peripatos.eye.parser import PDFParser
         p = PDFParser()
         meta = p.parse('tests/fixtures/sample_paper.pdf')
         print(f'Title: {meta.title}')
         print(f'Sections: {len(meta.sections)}')
         for s in meta.sections:
             print(f'  - {s.section_type.name}: {s.title[:50]}')
         "
    Expected Result: Prints title, 2+ sections with classified types
    Failure Indicators: Empty title, 0 sections, ParsingError
    Evidence: .sisyphus/evidence/task-5-parse-pdf.txt

  Scenario: Invalid PDF path raises clear error
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "
         from peripatos.eye.parser import PDFParser
         try:
             PDFParser().parse('/nonexistent/paper.pdf')
         except Exception as e:
             print(f'Error type: {type(e).__name__}')
             print(f'Message: {e}')
         "
    Expected Result: Prints "Error type: ParsingError" with descriptive message
    Failure Indicators: Generic exception, no message, crash
    Evidence: .sisyphus/evidence/task-5-invalid-pdf.txt
  ```

  **Commit**: YES
  - Message: `feat(parser): add PDF parsing via Docling`
  - Files: `peripatos/eye/parser.py, tests/test_parser.py`
  - Pre-commit: `pytest tests/test_parser.py`

- [x] 6. The "Eye" — ArXiv Fetcher Module

  **What to do**:
  - Implement `peripatos/eye/arxiv.py`:
    - `ArxivFetcher` class with method `fetch(arxiv_id: str) -> Path`
    - Given an ArXiv ID (e.g., `"2408.09869"` or `"2408.09869v1"`), download the PDF to a temp/output directory
    - Use ArXiv's direct URL pattern: `https://arxiv.org/pdf/{arxiv_id}`
    - Use `urllib.request` or `requests` (check if already a dependency) — prefer stdlib to minimize deps
    - Validate ArXiv ID format with regex: `^\d{4}\.\d{4,5}(v\d+)?$`
    - Also extract metadata from ArXiv API (`http://export.arxiv.org/api/query?id_list={arxiv_id}`) to get title, authors, abstract
    - Return path to downloaded PDF
    - Handle errors: invalid ID format, network failure, paper not found (404) → raise `FetchError`
  - **TDD**: Write `tests/test_arxiv.py` with:
    - Test: valid ArXiv ID format passes validation
    - Test: invalid ArXiv ID format raises `FetchError`
    - Test: metadata extraction parses title and authors from ArXiv API XML response (use mocked response)
    - Test: download returns valid PDF path (mock the HTTP call)

  **Must NOT do**:
  - Do NOT add `requests` as a dependency if not already present — use `urllib.request` from stdlib
  - Do NOT cache downloaded PDFs (no persistent storage in Phase 1)
  - Do NOT handle IEEE/ACM URLs — ArXiv only

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple HTTP fetch + XML parsing, well-defined API
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed for ArXiv API

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T7, T8, T9, T10)
  - **Parallel Group**: Wave 2
  - **Blocks**: T14
  - **Blocked By**: T1, T3, T4

  **References**:

  **Pattern References**:
  - `design_guideline/PRD.md:13` — "Users can generate a podcast simply by providing an ArXiv paper ID (e.g., `2310.00123`)." This is the input contract.
  - `design_guideline/design.md:20` — "Input: Local PDF path or ArXiv ID." Confirms ArXiv ID is a first-class input.

  **External References**:
  - ArXiv API docs: https://info.arxiv.org/help/api/basics.html — Use `id_list` parameter for single paper lookup
  - ArXiv PDF URL pattern: `https://arxiv.org/pdf/{id}` — Direct PDF download

  **WHY Each Reference Matters**:
  - PRD defines the user-facing contract (ArXiv ID as input)
  - ArXiv API is needed for metadata extraction (title/authors) before PDF parsing

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_arxiv.py`
  - [ ] `pytest tests/test_arxiv.py` → PASS (4+ tests)

  **QA Scenarios:**

  ```
  Scenario: Validate ArXiv ID format
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "
         from peripatos.eye.arxiv import ArxivFetcher
         f = ArxivFetcher()
         # Valid IDs
         assert f.validate_id('2408.09869')
         assert f.validate_id('2408.09869v1')
         # Invalid IDs
         try: f.validate_id('not-an-id'); assert False
         except Exception: pass
         print('All validations passed')
         "
    Expected Result: Prints "All validations passed"
    Failure Indicators: AssertionError, wrong validation
    Evidence: .sisyphus/evidence/task-6-validate-id.txt

  Scenario: Fetch fails gracefully for non-existent paper
    Tool: Bash
    Preconditions: pip install -e ., network available
    Steps:
      1. Run: python -c "
         from peripatos.eye.arxiv import ArxivFetcher
         try:
             ArxivFetcher().fetch('9999.99999')
         except Exception as e:
             print(f'Error: {type(e).__name__}: {e}')
         "
    Expected Result: Prints FetchError with descriptive message about paper not found
    Failure Indicators: Generic exception, timeout without message
    Evidence: .sisyphus/evidence/task-6-fetch-nonexistent.txt
  ```

  **Commit**: YES
  - Message: `feat(arxiv): add ArXiv paper fetcher`
  - Files: `peripatos/eye/arxiv.py, tests/test_arxiv.py`
  - Pre-commit: `pytest tests/test_arxiv.py`

- [x] 7. Math Normalization (LaTeX → Spoken Text)

  **What to do**:
  - Implement `peripatos/eye/math_normalize.py`:
    - `MathNormalizer` class with method `normalize(markdown: str) -> str`
    - Two-pass approach:
      1. **Regex pass**: Handle common LaTeX patterns with deterministic rules:
         - `\sum` → "the sum of", `\prod` → "the product of"
         - `\frac{a}{b}` → "a over b"
         - `x^2` → "x squared", `x^n` → "x to the power of n"
         - `\sqrt{x}` → "the square root of x"
         - `\alpha`, `\beta`, `\gamma` etc. → spelled-out Greek letters
         - `\leq` → "less than or equal to", `\geq` → "greater than or equal to"
         - `\int` → "the integral of"
         - `\partial` → "the partial derivative of"
      2. **LLM pass** (optional, for complex equations): If an equation is too complex for regex, flag it for the dialogue generator to explain contextually during script generation
    - Process both inline math (`$...$`) and display math (`$$...$$` or `\[...\]`)
    - Preserve non-math text unchanged
    - Return the markdown with math blocks replaced by spoken equivalents
  - **TDD**: Write `tests/test_math.py` with:
    - Test: simple inline math is normalized (e.g., `$x^2$` → "x squared")
    - Test: fractions are normalized (`$\frac{a}{b}$` → "a over b")
    - Test: Greek letters are spelled out
    - Test: non-math text is unchanged
    - Test: complex equations are flagged (not corrupted)
    - Test: nested LaTeX (e.g., `$\sum_{i=1}^{N} x_i$`) produces readable output

  **Must NOT do**:
  - Do NOT require an LLM call for every equation — regex handles common cases
  - Do NOT strip equations entirely — always produce a spoken approximation
  - Do NOT depend on any external math-to-speech library

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Regex engineering for LaTeX patterns requires careful implementation and edge case handling
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T8, T9, T10 — but depends on T5 for realistic test data)
  - **Parallel Group**: Wave 2 (can start after T3, T4; T5 is soft dependency)
  - **Blocks**: T8
  - **Blocked By**: T3, T4, T5 (soft — needs parsed markdown for integration)

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:22` — "Math Normalization: Custom Regex/LLM pass to convert LaTeX equations (e.g., $\sum$) into phonetic text ('the sum of...')." This defines the approach.
  - `design_guideline/PRD.md:22` — "'Speakable' Math Extraction: convert mathematical notation into natural, spoken English phonetics."
  - `design_guideline/PRD.md:45` — "The system must accurately describe key equations conceptually rather than reading every symbol verbatim." This is the quality bar.

  **WHY Each Reference Matters**:
  - Design doc mandates the two-pass approach (regex + LLM) — follow it
  - PRD's quality bar is clear: conceptual descriptions, not verbatim symbol reading

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_math.py`
  - [ ] `pytest tests/test_math.py` → PASS (6+ tests)

  **QA Scenarios:**

  ```
  Scenario: Common LaTeX patterns normalized correctly
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "
         from peripatos.eye.math_normalize import MathNormalizer
         n = MathNormalizer()
         results = [
             n.normalize('The loss is \$\\\\frac{1}{N}\$'),
             n.normalize('where \$x^2 + y^2 = r^2\$'),
             n.normalize('\$\\\\sum_{i=1}^{N} x_i\$'),
             n.normalize('No math here, just text.'),
         ]
         for r in results: print(r)
         "
    Expected Result: Math converted to spoken text; plain text unchanged
    Failure Indicators: LaTeX symbols remain in output, text corrupted, crash
    Evidence: .sisyphus/evidence/task-7-math-normalize.txt
  ```

  **Commit**: YES
  - Message: `feat(math): add LaTeX to spoken text normalization`
  - Files: `peripatos/eye/math_normalize.py, tests/test_math.py`
  - Pre-commit: `pytest tests/test_math.py`

- [x] 8. The "Brain" — Dialogue Script Generator (LLM Prompts + 4 Personas)

  **What to do**:
  - Implement `peripatos/brain/personas.py`:
    - Define persona prompt templates for all 4 archetypes:
      - **Skeptic**: Critical analysis, questions methodology, highlights limitations. System prompt should instruct the Expert to defend choices and the Host to probe weaknesses.
      - **Enthusiast**: Optimistic, focuses on impact and "what's cool". System prompt creates excitement and forward-looking discussion.
      - **Tutor**: Patient, explains background, assumes less prior knowledge. System prompt adds scaffolding and analogies.
      - **Peer**: High-bandwidth technical, skips basics, assumes domain expertise. System prompt maximizes information density.
    - Each persona has distinct system prompts for both HOST and EXPERT roles
    - `get_persona_prompts(persona_type: PersonaType) -> dict` returning system prompts for both roles
  - Implement `peripatos/brain/generator.py`:
    - `DialogueGenerator` class with method `generate(paper: PaperMetadata, config: PeripatosConfig) -> DialogueScript`
    - Process sections in order: for each section, generate a dialogue exchange (HOST asks, EXPERT explains)
    - Build LLM prompts that:
      - Include the paper section's markdown content
      - Apply the selected persona's system prompt
      - Instruct the LLM to output structured JSON: `[{"speaker": "HOST", "text": "..."}, {"speaker": "EXPERT", "text": "..."}]`
    - Support both OpenAI and Anthropic via config (use the `openai` and `anthropic` Python SDKs)
    - Chunk sections if they exceed LLM context limits
    - Parse LLM JSON response into `DialogueTurn` objects
    - Assemble all turns into a complete `DialogueScript`
    - Handle errors: LLM API failure, invalid JSON response, rate limits → retry with backoff or raise `GenerationError`
  - **TDD**: Write `tests/test_brain.py` with:
    - Test: each persona generates distinct system prompts (compare prompt text)
    - Test: generator constructs valid LLM messages for each persona
    - Test: JSON response parsing produces correct `DialogueTurn` list (mock LLM response)
    - Test: long sections are chunked appropriately
    - Test: API failure raises `GenerationError`

  **Must NOT do**:
  - Do NOT hardcode API keys — use config
  - Do NOT support local LLMs (Ollama etc.) in Phase 1 — only OpenAI and Anthropic
  - Do NOT generate audio in this module — only text dialogue scripts
  - Do NOT implement auto-tuning based on listening history (Phase 2 feature)

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex prompt engineering for 4 distinct personas, LLM API integration, JSON parsing, error handling
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T6, T9, T10 — but depends on T7 for math-normalized input)
  - **Parallel Group**: Wave 2
  - **Blocks**: T11, T12, T14
  - **Blocked By**: T2, T3, T4, T7

  **References**:

  **Pattern References**:
  - `design_guideline/PRD.md:25-37` — Complete persona specification: two-persona dynamic (Proxy Host + Expert Author), 4 archetypes with detailed descriptions. This is the authoritative source for persona behavior.
  - `design_guideline/design.md:23-29` — "The Brain" module spec: Orchestrator selects Persona, Generator sends Markdown chunks to LLM, generates JSON transcript.
  - `peripatos/models.py` (from T3) — `DialogueScript`, `DialogueTurn`, `PersonaType` — the output types this generator must produce.
  - `peripatos/config.py` (from T2) — `PeripatosConfig` — provides LLM provider, model, and persona selection.

  **External References**:
  - OpenAI Chat API: `client.chat.completions.create(model=..., messages=[{"role": "system", "content": ...}])`
  - Anthropic Messages API: `client.messages.create(model=..., system=..., messages=[...])`

  **WHY Each Reference Matters**:
  - PRD persona specs are the source of truth — prompt engineering must capture these exact personalities
  - Design doc defines the pipeline boundary — generator produces JSON transcript, not audio
  - Config provides the LLM routing logic — must work with both OpenAI and Anthropic

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_brain.py`
  - [ ] `pytest tests/test_brain.py` → PASS (5+ tests)

  **QA Scenarios:**

  ```
  Scenario: All 4 personas produce distinct prompt styles
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "
         from peripatos.brain.personas import get_persona_prompts
         from peripatos.models import PersonaType
         prompts = {}
         for p in PersonaType:
             prompts[p.name] = get_persona_prompts(p)
             print(f'{p.name}: {prompts[p.name][\"host_system\"][:80]}...')
         # Verify all are distinct
         texts = [v['host_system'] for v in prompts.values()]
         assert len(set(texts)) == 4, 'Personas are not distinct!'
         print('All 4 personas are distinct')
         "
    Expected Result: 4 distinct persona prompts printed, assertion passes
    Failure Indicators: Duplicate prompts, missing persona, KeyError
    Evidence: .sisyphus/evidence/task-8-persona-prompts.txt

  Scenario: Dialogue generation with mocked LLM produces valid script
    Tool: Bash
    Preconditions: pip install -e ., pytest installed
    Steps:
      1. Run: pytest tests/test_brain.py -v -k "test_generate_dialogue" --tb=short
    Expected Result: Test passes, demonstrating mocked LLM produces DialogueScript with HOST and EXPERT turns
    Failure Indicators: Test fails, wrong turn structure
    Evidence: .sisyphus/evidence/task-8-dialogue-gen.txt
  ```

  **Commit**: YES
  - Message: `feat(brain): add dialogue script generator with 4 persona archetypes`
  - Files: `peripatos/brain/generator.py, peripatos/brain/personas.py, tests/test_brain.py`
  - Pre-commit: `pytest tests/test_brain.py`

- [x] 9. The "Voice" — OpenAI TTS Engine

  **What to do**:
  - Implement `peripatos/voice/openai_tts.py`:
    - `OpenAITTSEngine` class implementing a common TTS interface:
      - `synthesize(text: str, voice: str) -> bytes` — returns raw audio bytes (MP3)
      - `is_available() -> bool` — checks if OPENAI_API_KEY is set
    - Use OpenAI's TTS API: `client.audio.speech.create(model="tts-1", voice=voice, input=text)`
    - **Smart chunking**: OpenAI TTS has a 4096 character limit per request
      - Split text at sentence boundaries (`. `, `? `, `! `)
      - If a single sentence exceeds 4096 chars, split at clause boundaries (`, `, `; `)
      - Synthesize each chunk separately and concatenate the audio bytes
    - Support different voices for Host vs Expert (configurable via config):
      - Default Host voice: "alloy" (warmer, conversational)
      - Default Expert voice: "onyx" (deeper, authoritative)
    - Handle errors: API key missing → raise `TTSError("OPENAI_API_KEY not set")`, rate limits → retry with exponential backoff, network errors → raise `TTSError`
  - **TDD**: Write `tests/test_openai_tts.py` with:
    - Test: text chunking splits correctly at sentence boundaries
    - Test: chunks never exceed 4096 characters
    - Test: `is_available()` returns False when key is missing
    - Test: synthesis with mocked API returns audio bytes
    - Test: different voices are used for different speaker roles

  **Must NOT do**:
  - Do NOT use "tts-1-hd" model by default (expensive) — use "tts-1" as default, make configurable
  - Do NOT hardcode API key
  - Do NOT add ElevenLabs support

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: API integration with chunking logic and retry behavior
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T6, T7, T8, T10)
  - **Parallel Group**: Wave 2
  - **Blocks**: T11
  - **Blocked By**: T2, T3, T4

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:29-31` — "Standard: Calls OpenAI Audio (High Fidelity). Fallback: Calls edge-tts." This establishes OpenAI as the primary engine.
  - `design_guideline/PRD.md:44` — "The 'Host' and 'Author' voices must be easily distinguishable by tone/pitch." Different voices per role is a requirement.
  - `peripatos/config.py` (from T2) — `voice_host` and `voice_expert` config fields provide voice selection.

  **External References**:
  - OpenAI TTS API: `client.audio.speech.create(model="tts-1", voice="alloy", input="text")` — returns audio response
  - OpenAI voices: alloy, echo, fable, onyx, nova, shimmer
  - Character limit: 4096 chars per request

  **WHY Each Reference Matters**:
  - PRD requires distinguishable voices — must use different OpenAI voices for Host vs Expert
  - 4096 char limit is a hard constraint — chunking logic is essential

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_openai_tts.py`
  - [ ] `pytest tests/test_openai_tts.py` → PASS (5+ tests)

  **QA Scenarios:**

  ```
  Scenario: Text chunking respects 4096 char limit
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "
         from peripatos.voice.openai_tts import OpenAITTSEngine
         engine = OpenAITTSEngine.__new__(OpenAITTSEngine)
         # Test with long text
         long_text = 'This is a sentence. ' * 300  # ~6000 chars
         chunks = engine._chunk_text(long_text)
         print(f'Chunks: {len(chunks)}')
         for i, c in enumerate(chunks):
             print(f'  Chunk {i}: {len(c)} chars')
             assert len(c) <= 4096, f'Chunk {i} exceeds limit: {len(c)}'
         print('All chunks within limit')
         "
    Expected Result: Multiple chunks, all ≤4096 chars, split at sentence boundaries
    Failure Indicators: Chunk exceeds 4096, split mid-word
    Evidence: .sisyphus/evidence/task-9-chunking.txt

  Scenario: Missing API key detected
    Tool: Bash
    Preconditions: No OPENAI_API_KEY in environment
    Steps:
      1. Run: OPENAI_API_KEY="" python -c "
         from peripatos.voice.openai_tts import OpenAITTSEngine
         engine = OpenAITTSEngine()
         print(f'Available: {engine.is_available()}')
         "
    Expected Result: Prints "Available: False"
    Failure Indicators: Returns True without key, crash
    Evidence: .sisyphus/evidence/task-9-no-key.txt
  ```

  **Commit**: YES
  - Message: `feat(voice): add OpenAI TTS engine`
  - Files: `peripatos/voice/openai_tts.py, tests/test_openai_tts.py`
  - Pre-commit: `pytest tests/test_openai_tts.py`

- [x] 10. The "Voice" — edge-tts Fallback Engine

  **What to do**:
  - Implement `peripatos/voice/edge_tts_engine.py`:
    - `EdgeTTSEngine` class implementing the same TTS interface as OpenAI engine:
      - `async synthesize(text: str, voice: str) -> bytes` — returns raw audio bytes (MP3)
      - `is_available() -> bool` — always returns True (no API key needed)
    - Use the `edge-tts` Python library (by rany2):
      - `communicate = edge_tts.Communicate(text, voice)`
      - Stream audio data from `communicate.stream()`
    - Support different voices for Host vs Expert:
      - Default Host voice: "en-US-AriaNeural" (conversational female)
      - Default Expert voice: "en-US-GuyNeural" (deeper male)
      - Chinese voices: "zh-CN-XiaoxiaoNeural" (host), "zh-CN-YunxiNeural" (expert)
    - Handle the async nature: wrap in `asyncio.run()` for synchronous callers, or provide async-native interface
    - Handle errors: network failure, invalid voice name → raise `TTSError`
  - **TDD**: Write `tests/test_edge_tts.py` with:
    - Test: `is_available()` always returns True
    - Test: voice selection returns correct voice names for language modes
    - Test: synthesize with mocked edge_tts returns audio bytes
    - Test: invalid voice name handling

  **Must NOT do**:
  - Do NOT require any API keys for edge-tts
  - Do NOT add ElevenLabs support
  - Do NOT cache audio — each call produces fresh output

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simpler TTS integration, no API key management, well-documented library
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T5, T6, T7, T8, T9)
  - **Parallel Group**: Wave 2
  - **Blocks**: T11
  - **Blocked By**: T2, T3, T4

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:31` — "Fallback: Calls edge-tts (Local/Offline) for users without API keys." This establishes edge-tts as the fallback.
  - `design_guideline/PRD.md:44` — Distinguishable voices requirement applies to edge-tts too.

  **External References**:
  - edge-tts Python (rany2): `pip install edge-tts` — async TTS using Microsoft Edge's service
  - Usage: `import edge_tts; communicate = edge_tts.Communicate("text", "en-US-AriaNeural"); await communicate.save("output.mp3")`
  - Voice list: `edge_tts.list_voices()` returns available voices

  **WHY Each Reference Matters**:
  - Design doc specifies edge-tts as the specific fallback — not any other free TTS
  - Need different voices for Host/Expert to meet PRD's distinguishability requirement

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_edge_tts.py`
  - [ ] `pytest tests/test_edge_tts.py` → PASS (4+ tests)

  **QA Scenarios:**

  ```
  Scenario: edge-tts is always available (no key needed)
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "
         from peripatos.voice.edge_tts_engine import EdgeTTSEngine
         engine = EdgeTTSEngine()
         print(f'Available: {engine.is_available()}')
         "
    Expected Result: Prints "Available: True"
    Failure Indicators: Returns False, ImportError
    Evidence: .sisyphus/evidence/task-10-available.txt

  Scenario: Voice selection for different languages
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "
         from peripatos.voice.edge_tts_engine import EdgeTTSEngine
         engine = EdgeTTSEngine()
         en_voices = engine.get_voices('en')
         zh_voices = engine.get_voices('zh')
         print(f'English host: {en_voices[\"host\"]}')
         print(f'English expert: {en_voices[\"expert\"]}')
         print(f'Chinese host: {zh_voices[\"host\"]}')
         print(f'Chinese expert: {zh_voices[\"expert\"]}')
         "
    Expected Result: Prints 4 distinct voice names (2 English, 2 Chinese)
    Failure Indicators: Same voice for host/expert, missing language
    Evidence: .sisyphus/evidence/task-10-voices.txt
  ```

  **Commit**: YES
  - Message: `feat(voice): add edge-tts fallback engine`
  - Files: `peripatos/voice/edge_tts_engine.py, tests/test_edge_tts.py`
  - Pre-commit: `pytest tests/test_edge_tts.py`

### Wave 3 — Integration & Mixing

- [x] 11. Audio Renderer Orchestrator (TTS Engine Selection + Smart Chunking)

  **What to do**:
  - Implement `peripatos/voice/renderer.py`:
    - `AudioRenderer` class with method `render(script: DialogueScript, config: PeripatosConfig) -> list[AudioSegment]`
    - Engine selection logic:
      1. If `config.tts.engine == "openai"` and `OpenAITTSEngine.is_available()` → use OpenAI
      2. Else → fall back to edge-tts with a warning log
    - For each `DialogueTurn` in the script:
      - Select the correct voice based on `turn.speaker` (HOST vs EXPERT) and config
      - Call the selected TTS engine to synthesize the text
      - Wrap result in `AudioSegment` dataclass
    - Add brief silence (300ms) between turns for natural pacing
    - Handle mixed language: for `zh-en` mode, detect language of each turn and select appropriate voice
    - Return ordered list of `AudioSegment`s
    - Provide progress callback (optional) for CLI progress bar
  - **TDD**: Write `tests/test_renderer.py` with:
    - Test: OpenAI engine selected when available
    - Test: edge-tts fallback when OpenAI key missing
    - Test: HOST and EXPERT get different voices
    - Test: silence padding is inserted between turns
    - Test: render produces AudioSegment list matching DialogueScript length

  **Must NOT do**:
  - Do NOT mix audio here — that's the Mixer's job (Task 13)
  - Do NOT add ElevenLabs as a third engine
  - Do NOT implement caching of rendered audio

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Orchestration logic with engine selection, voice routing, error handling, progress reporting
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T12, but NOT T13/T14 which depend on it)
  - **Parallel Group**: Wave 3
  - **Blocks**: T13, T14
  - **Blocked By**: T3, T8, T9, T10

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:28-34` — "The Voice" module spec: Synthesizer iterates through JSON transcript, calls OpenAI/edge-tts, Mixer stitches segments.
  - `peripatos/voice/openai_tts.py` (from T9) — OpenAI engine interface
  - `peripatos/voice/edge_tts_engine.py` (from T10) — edge-tts engine interface
  - `peripatos/models.py` (from T3) — `DialogueScript`, `AudioSegment` types

  **WHY Each Reference Matters**:
  - Design doc defines the renderer as the orchestrator that selects engines and iterates through the transcript
  - Must work with both TTS engines produced by T9 and T10

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_renderer.py`
  - [ ] `pytest tests/test_renderer.py` → PASS (5+ tests)

  **QA Scenarios:**

  ```
  Scenario: Engine fallback works when OpenAI key missing
    Tool: Bash
    Preconditions: pip install -e ., no OPENAI_API_KEY set
    Steps:
      1. Run: OPENAI_API_KEY="" python -c "
         from peripatos.voice.renderer import AudioRenderer
         from peripatos.config import load_config
         config = load_config()
         renderer = AudioRenderer(config)
         print(f'Active engine: {renderer.active_engine_name}')
         "
    Expected Result: Prints "Active engine: edge-tts"
    Failure Indicators: Crash, prints "openai"
    Evidence: .sisyphus/evidence/task-11-fallback.txt
  ```

  **Commit**: YES
  - Message: `feat(voice): add audio renderer orchestrator with smart chunking`
  - Files: `peripatos/voice/renderer.py, tests/test_renderer.py`
  - Pre-commit: `pytest tests/test_renderer.py`

- [x] 12. Bilingual Code-Switching (Chinese + English)

  **What to do**:
  - Implement `peripatos/brain/bilingual.py`:
    - `BilingualProcessor` class with method `process(script: DialogueScript) -> DialogueScript`
    - When `language_mode == ZH_EN`:
      - Post-process dialogue turns: the LLM should already generate bilingual text (via prompt), but this module ensures:
        1. Technical terms remain in English (build a term whitelist: "Transformer", "Attention Mechanism", "Gradient Descent", "Loss Function", "Backpropagation", "Neural Network", etc.)
        2. Chinese text is natural and fluent
        3. Mixed-language text is properly formatted for TTS (add brief pauses via SSML or punctuation between language switches)
    - Also modify the dialogue generator's system prompt for bilingual mode:
      - `get_bilingual_prompt_modifier(language_mode: LanguageMode) -> str` — returns an additional instruction to append to persona prompts
      - E.g., "Explain the concepts in Mandarin Chinese (简体中文), but keep all technical terms in English. For example, say 'Transformer 模型' not '变换器模型'."
    - Handle voice selection for bilingual: Chinese voices for narrative, with clear English pronunciation for technical terms
  - **TDD**: Write `tests/test_bilingual.py` with:
    - Test: bilingual prompt modifier is generated for ZH_EN mode
    - Test: technical terms in whitelist are preserved in English
    - Test: EN mode returns script unchanged
    - Test: prompt modifier includes specific Chinese+English instruction

  **Must NOT do**:
  - Do NOT support any language pair beyond Chinese+English in this task
  - Do NOT build a full i18n framework
  - Do NOT attempt automatic language detection (trust the LLM output + whitelist)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding of bilingual text processing, prompt modification, and TTS voice routing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T11, T13)
  - **Parallel Group**: Wave 3
  - **Blocks**: T14
  - **Blocked By**: T8

  **References**:

  **Pattern References**:
  - `design_guideline/PRD.md:38` — "Bilingual 'Code-Switching': The system must support 'Mixed Language' generation, allowing the narrative to flow in the user's native language (e.g., Chinese) while keeping critical technical terminology in English."
  - `design_guideline/idea.md:18` — "Code-Switching: Supports native language flow (e.g., Chinese) with precise English technical terminology."
  - `design_guideline/PRD.md:8` — Non-native speaker user story: "explain the concepts in Mandarin but keep the technical terms in English."

  **WHY Each Reference Matters**:
  - PRD defines the exact code-switching behavior — Chinese narrative + English terms
  - User story gives the concrete example of expected output
  - This is a key differentiator mentioned in the idea doc

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_bilingual.py`
  - [ ] `pytest tests/test_bilingual.py` → PASS (4+ tests)

  **QA Scenarios:**

  ```
  Scenario: Bilingual prompt modifier generates correct instruction
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "
         from peripatos.brain.bilingual import BilingualProcessor, get_bilingual_prompt_modifier
         from peripatos.models import LanguageMode
         modifier = get_bilingual_prompt_modifier(LanguageMode.ZH_EN)
         print(modifier)
         assert '中文' in modifier or 'Chinese' in modifier
         assert 'English' in modifier
         print('Bilingual modifier OK')
         "
    Expected Result: Modifier contains instructions for Chinese+English code-switching
    Failure Indicators: Empty modifier, missing language references
    Evidence: .sisyphus/evidence/task-12-bilingual-prompt.txt
  ```

  **Commit**: YES
  - Message: `feat(brain): add bilingual code-switching (zh-en)`
  - Files: `peripatos/brain/bilingual.py, tests/test_bilingual.py`
  - Pre-commit: `pytest tests/test_bilingual.py`

- [x] 13. The "Mixer" — Audio Stitching + Chapter Markers (ffmpeg)

  **What to do**:
  - Implement `peripatos/voice/mixer.py`:
    - `AudioMixer` class with method `mix(segments: list[AudioSegment], chapters: list[ChapterMarker], output_path: Path) -> Path`
    - Use `pydub` to:
      - Concatenate all `AudioSegment` audio bytes in order
      - Insert configurable silence between segments (default: 500ms between sections, 300ms between turns within a section)
      - Optionally add intro/outro silence (1 second)
    - Use `ffmpeg` (via subprocess) to:
      - Inject chapter metadata into the final MP3 using ffmpeg's `-metadata` and chapter specification
      - Chapter format: ffmpeg metadata file format (`;FFMETADATA1` header, `[CHAPTER]` sections with `TIMEBASE`, `START`, `END`, `title`)
    - Generate chapter markers from section boundaries:
      - Track cumulative time offset as segments are concatenated
      - Create a `ChapterMarker` for each section transition
    - Export final MP3 file to `output_path`
    - Validate: check ffmpeg is installed (`which ffmpeg`), raise `MixerError` if missing
  - **TDD**: Write `tests/test_mixer.py` with:
    - Test: concatenation produces audio with expected total duration
    - Test: chapter metadata file is correctly formatted
    - Test: ffmpeg missing raises `MixerError` with install instructions
    - Test: empty segment list raises `MixerError`
    - Test: output file is a valid MP3

  **Must NOT do**:
  - Do NOT add intro/outro music (not in scope for MVP)
  - Do NOT compress or transcode audio — keep original quality
  - Do NOT install ffmpeg automatically — just detect and error if missing

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: ffmpeg subprocess integration, audio manipulation, chapter metadata format
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on T11 output)
  - **Parallel Group**: Wave 3 (but sequential after T11)
  - **Blocks**: T14
  - **Blocked By**: T11

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:32` — "Mixer: Uses ffmpeg to stitch segments, inject chapter markers, and add intro/outro music."
  - `design_guideline/PRD.md:40` — "The final output (MP3) must include embedded chapter metadata, allowing users to use standard podcast players to skip or rewind specific sections."
  - `peripatos/models.py` (from T3) — `AudioSegment`, `ChapterMarker` types

  **External References**:
  - ffmpeg chapter metadata format: https://ffmpeg.org/ffmpeg-formats.html#Metadata-1 — Use `;FFMETADATA1` format
  - pydub: `from pydub import AudioSegment; combined = segment1 + silence + segment2`

  **WHY Each Reference Matters**:
  - PRD requires chapter markers for podcast player navigation — this is a key UX feature
  - ffmpeg metadata format is specific — must follow the exact `;FFMETADATA1` spec

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_mixer.py`
  - [ ] `pytest tests/test_mixer.py` → PASS (5+ tests)

  **QA Scenarios:**

  ```
  Scenario: Chapter markers are readable by ffprobe
    Tool: Bash
    Preconditions: pip install -e ., ffmpeg installed, test audio segments available
    Steps:
      1. Run: pytest tests/test_mixer.py -v -k "test_chapter_metadata" --tb=short
      2. If a test MP3 is produced, run: ffprobe -show_chapters -print_format json <output.mp3>
    Expected Result: ffprobe shows chapter entries with titles matching section names
    Failure Indicators: No chapters in output, ffprobe error
    Evidence: .sisyphus/evidence/task-13-chapters.txt

  Scenario: ffmpeg missing produces clear error
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: PATH="" python -c "
         from peripatos.voice.mixer import AudioMixer
         try:
             AudioMixer()
         except Exception as e:
             print(f'{type(e).__name__}: {e}')
         "
    Expected Result: MixerError with message about ffmpeg not being installed
    Failure Indicators: Generic error, no helpful message
    Evidence: .sisyphus/evidence/task-13-no-ffmpeg.txt
  ```

  **Commit**: YES
  - Message: `feat(voice): add audio mixer with chapter markers`
  - Files: `peripatos/voice/mixer.py, tests/test_mixer.py`
  - Pre-commit: `pytest tests/test_mixer.py`

- [x] 14. CLI Orchestrator (argparse + End-to-End Pipeline Wiring)

  **What to do**:
  - Implement `peripatos/cli.py`:
    - Use `argparse` to define the CLI interface:
      ```
      peripatos generate <source>            # ArXiv ID or PDF path
        --persona {skeptic,enthusiast,tutor,peer}  # Default: from config
        --language {en,zh-en}               # Default: from config
        --tts-engine {openai,edge-tts}       # Default: from config
        --output-dir <path>                  # Default: ./output
        --llm-provider {openai,anthropic}    # Default: from config
        --llm-model <model_name>             # Default: from config
        --verbose / -v                       # Enable verbose logging

      peripatos --version                    # Print version
      peripatos --help                       # Print help
      ```
    - Implement `main()` function as the entry point:
      1. Parse CLI arguments
      2. Load config (merge CLI overrides)
      3. Detect source type: ArXiv ID (regex match) vs local PDF (file exists)
      4. If ArXiv ID → use `ArxivFetcher` to download PDF
      5. Parse PDF → `PaperMetadata` via `PDFParser`
      6. Normalize math → `MathNormalizer`
      7. If bilingual mode → apply `BilingualProcessor` prompt modifier
      8. Generate dialogue → `DialogueGenerator`
      9. Render audio → `AudioRenderer`
      10. Mix and add chapters → `AudioMixer`
      11. Print output path and summary
    - Add progress logging: print status at each pipeline stage (e.g., "📄 Parsing PDF...", "🧠 Generating dialogue (Tutor persona)...", "🔊 Rendering audio...")
    - Handle errors at each stage with user-friendly messages (not stack traces unless --verbose)
    - Create output directory if it doesn't exist
  - **TDD**: Write `tests/test_cli.py` with:
    - Test: argparse parses all valid argument combinations
    - Test: `--version` prints correct version
    - Test: `--help` prints usage info
    - Test: invalid source raises SystemExit with error message
    - Test: ArXiv ID is correctly detected vs PDF path

  **Must NOT do**:
  - Do NOT add any HTTP server or web endpoints
  - Do NOT add interactive/REPL mode
  - Do NOT add `typer` dependency — use argparse

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Wires together all pipeline modules, complex argument parsing, error handling for full pipeline
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on most Wave 2 and Wave 3 tasks)
  - **Parallel Group**: Wave 3 (last task — starts when T11, T12, T13 are done)
  - **Blocks**: T15, T16
  - **Blocked By**: T2, T5, T6, T8, T11, T12, T13

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:15` — "Interface: CLI (typer or argparse)". User chose argparse.
  - `design_guideline/PRD.md:13` — "Users can generate a podcast simply by providing an ArXiv paper ID." This is the primary use case.
  - `design_guideline/PRD.md:46` — "A standard 10-page 2-column PDF should be processed into audio in under 2 minutes." Performance target for the full pipeline.
  - All previous tasks' modules — this is the orchestrator that connects them all.

  **WHY Each Reference Matters**:
  - Design doc specifies argparse — must not deviate
  - PRD defines the user-facing UX (ArXiv ID as primary input)
  - All modules from T2-T13 are wired together here — the CLI is the integration point

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_cli.py`
  - [ ] `pytest tests/test_cli.py` → PASS (5+ tests)

  **QA Scenarios:**

  ```
  Scenario: CLI help and version commands work
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: peripatos --version
      2. Run: peripatos --help
      3. Run: peripatos generate --help
    Expected Result: Version prints "0.1.0", help shows all options
    Failure Indicators: Command not found, missing options in help
    Evidence: .sisyphus/evidence/task-14-cli-help.txt

  Scenario: Source type detection (ArXiv vs PDF)
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: python -c "
         from peripatos.cli import detect_source_type
         print(detect_source_type('2408.09869'))   # ArXiv
         print(detect_source_type('paper.pdf'))     # PDF
         print(detect_source_type('2408.09869v2'))  # ArXiv with version
         "
    Expected Result: Prints "arxiv", "pdf", "arxiv"
    Failure Indicators: Wrong detection, crash
    Evidence: .sisyphus/evidence/task-14-source-detect.txt

  Scenario: Invalid source produces clear error
    Tool: Bash
    Preconditions: pip install -e .
    Steps:
      1. Run: peripatos generate "not-a-valid-source" 2>&1
    Expected Result: Error message like "Could not identify source type for 'not-a-valid-source'. Provide an ArXiv ID (e.g., 2408.09869) or a path to a PDF file."
    Failure Indicators: Stack trace (without -v), silent failure
    Evidence: .sisyphus/evidence/task-14-invalid-source.txt
  ```

  **Commit**: YES
  - Message: `feat(cli): add CLI orchestrator with argparse`
  - Files: `peripatos/cli.py, tests/test_cli.py`
  - Pre-commit: `pytest tests/test_cli.py`

### Wave 4 — Packaging & Final Verification

- [x] 15. Package Distribution (pip install, Entry Points)

  **What to do**:
  - Finalize `pyproject.toml`:
    - Verify all dependencies are correctly listed with version constraints
    - Ensure `[project.scripts]` entry point is correct: `peripatos = "peripatos.cli:main"`
    - Add classifiers: Development Status, License, Python versions, Topic
    - Add project URLs: homepage (GitHub), documentation
    - Verify `[build-system]` uses `setuptools` or `hatchling`
  - Test the full install flow:
    1. Create a fresh virtual environment
    2. `pip install -e .` — verify no dependency conflicts
    3. `peripatos --version` — verify entry point works
    4. `peripatos --help` — verify all subcommands visible
  - Create `.env.example` with all supported environment variables documented
  - Verify `pip install -e ".[dev]"` installs dev dependencies (pytest, etc.)

  **Must NOT do**:
  - Do NOT publish to PyPI yet — just ensure local install works
  - Do NOT pin exact versions — use compatible release (`>=x.y`) or ranges
  - Do NOT add unnecessary dependencies

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Package metadata finalization, dependency verification
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T16, T17)
  - **Parallel Group**: Wave 4
  - **Blocks**: T16
  - **Blocked By**: T14

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:69` — "Release pip install peripatos (v0.1)." This is the target.
  - `pyproject.toml` (from T1) — Initial scaffolding to finalize.

  **External References**:
  - PEP 621: https://peps.python.org/pep-0621/ — Project metadata standard

  **WHY Each Reference Matters**:
  - Design doc sets the target: pip-installable v0.1
  - PEP 621 ensures metadata is standard-compliant

  **Acceptance Criteria**:

  **TDD:**
  - [ ] `pip install -e .` → SUCCESS in fresh venv
  - [ ] `peripatos --version` → prints "0.1.0"

  **QA Scenarios:**

  ```
  Scenario: Clean install in fresh virtual environment
    Tool: Bash
    Preconditions: Python 3.10+ available
    Steps:
      1. Run: python -m venv /tmp/peripatos-test-venv
      2. Run: /tmp/peripatos-test-venv/bin/pip install -e .
      3. Run: /tmp/peripatos-test-venv/bin/peripatos --version
      4. Run: /tmp/peripatos-test-venv/bin/peripatos --help
      5. Run: rm -rf /tmp/peripatos-test-venv
    Expected Result: Install succeeds, version prints "0.1.0", help shows all commands
    Failure Indicators: Dependency conflict, entry point not found, import errors
    Evidence: .sisyphus/evidence/task-15-clean-install.txt
  ```

  **Commit**: YES
  - Message: `chore: finalize package distribution (entry points, metadata)`
  - Files: `pyproject.toml, .env.example`
  - Pre-commit: `pip install -e . && peripatos --help`

- [ ] 16. End-to-End Integration Tests

  **What to do**:
  - Implement `tests/test_e2e.py`:
    - **Test: Full pipeline with mocked LLM and TTS** (no real API calls):
      - Mock OpenAI chat completion to return a pre-built dialogue JSON
      - Mock OpenAI TTS to return dummy audio bytes
      - Run the full pipeline: local PDF → parse → generate → render → mix → MP3
      - Assert: output MP3 file exists, has non-zero size, has chapter markers
    - **Test: Full pipeline with edge-tts fallback** (no API key):
      - Same as above but with no OPENAI_API_KEY → should auto-fallback to edge-tts
      - Mock edge-tts to return dummy audio bytes
      - Assert: same output expectations
    - **Test: ArXiv ID pipeline** (mocked network):
      - Mock ArXiv HTTP response to return a pre-stored PDF
      - Run full pipeline
      - Assert: MP3 produced with correct metadata
    - **Test: Each persona produces different output**:
      - Run the dialogue generator (mocked LLM) with all 4 personas on the same input
      - Assert: the generated prompts are different for each persona
    - **Test: Bilingual mode (zh-en)**:
      - Run with `--language zh-en` (mocked)
      - Assert: prompt includes bilingual instructions
    - **Test: Error cases**:
      - Invalid ArXiv ID → clean error
      - Missing both API keys when openai engine selected → fallback message
      - Non-existent PDF path → clear error
  - Use `pytest` fixtures from T4 extensively
  - All tests should run without real API calls (fully mocked)

  **Must NOT do**:
  - Do NOT make real API calls in CI-friendly tests
  - Do NOT skip error case tests
  - Do NOT use `subprocess` to call CLI when direct function calls suffice

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex test setup with multiple mocks, full pipeline verification, edge case coverage
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T17)
  - **Parallel Group**: Wave 4
  - **Blocks**: F1-F4
  - **Blocked By**: T14, T15

  **References**:

  **Pattern References**:
  - `design_guideline/design.md:87-88` — "Unit Tests for peripatos-core logic. Integration Tests: End-to-end CLI run on a sample PDF."
  - All modules from T2-T14 — integration tests verify they all work together.

  **WHY Each Reference Matters**:
  - Design doc mandates end-to-end integration tests — this task fulfills that requirement
  - Every module from the pipeline must be exercised in combination

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file created: `tests/test_e2e.py`
  - [ ] `pytest tests/test_e2e.py` → PASS (6+ tests)

  **QA Scenarios:**

  ```
  Scenario: Full test suite passes
    Tool: Bash
    Preconditions: pip install -e ".[dev]"
    Steps:
      1. Run: pytest tests/ -v --tb=short 2>&1
      2. Run: pytest --cov=peripatos --cov-report=term-missing 2>&1
    Expected Result: All tests pass, coverage >80% on core logic
    Failure Indicators: Any test failure, coverage below 80%
    Evidence: .sisyphus/evidence/task-16-full-suite.txt

  Scenario: E2E pipeline produces output (mocked)
    Tool: Bash
    Preconditions: pip install -e ".[dev]"
    Steps:
      1. Run: pytest tests/test_e2e.py -v -k "test_full_pipeline" --tb=long 2>&1
    Expected Result: Test passes, shows pipeline stages executing in order
    Failure Indicators: Test failure at any pipeline stage
    Evidence: .sisyphus/evidence/task-16-e2e-pipeline.txt
  ```

  **Commit**: YES
  - Message: `test: add end-to-end integration tests`
  - Files: `tests/test_e2e.py`
  - Pre-commit: `pytest tests/test_e2e.py`

- [ ] 17. Documentation (README.md + Usage Examples)

  **What to do**:
  - Write `README.md` with:
    - Project title and tagline: "Peripatos — Deep Learning while Moving"
    - Badge: MIT License
    - One-paragraph description of what Peripatos does
    - **Quick Start** section:
      ```bash
      pip install -e .
      # Set your API key
      export OPENAI_API_KEY=sk-...
      # Generate a podcast from an ArXiv paper
      peripatos generate 2408.09869
      # Or from a local PDF
      peripatos generate ./paper.pdf
      ```
    - **Configuration** section:
      - API keys via `.env`
      - Config file at `~/.peripatos/config.yaml` with example
    - **Persona Modes** section: describe all 4 archetypes with example use cases
    - **Bilingual Mode** section: explain zh-en code-switching
    - **CLI Reference** section: full `--help` output
    - **Requirements**: Python 3.10+, ffmpeg
    - **Development** section: `pip install -e ".[dev]"`, `pytest`
    - **License**: MIT
    - **Acknowledgments**: Docling, OpenAI, edge-tts
  - Keep README concise (under 200 lines) — not a full manual

  **Must NOT do**:
  - Do NOT include API keys in examples (use `sk-...` placeholder)
  - Do NOT document Phase 2/3 features
  - Do NOT add badges for CI/coverage (no CI setup yet)

  **Recommended Agent Profile**:
  - **Category**: `writing`
    - Reason: Documentation writing, clear prose, formatting
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES (with T15, T16)
  - **Parallel Group**: Wave 4
  - **Blocks**: — (non-blocking)
  - **Blocked By**: T14

  **References**:

  **Pattern References**:
  - `design_guideline/idea.md:1-9` — Vision statement and tagline — use for README intro
  - `design_guideline/PRD.md:6-9` — User stories — can reference as "Who is this for?"
  - All CLI options from T14 — document exact flags and usage

  **WHY Each Reference Matters**:
  - Idea doc has the tagline and vision — README should capture this energy
  - User stories from PRD make compelling "who is this for" section

  **Acceptance Criteria**:

  **QA Scenarios:**

  ```
  Scenario: README exists and is well-formed
    Tool: Bash
    Preconditions: After writing README
    Steps:
      1. Run: test -f README.md && echo "EXISTS" || echo "MISSING"
      2. Run: wc -l README.md
      3. Run: grep -c "## " README.md  # Count sections
      4. Run: grep "OPENAI_API_KEY=sk-" README.md  # Verify no real keys
    Expected Result: File exists, <200 lines, 5+ sections, no real API keys
    Failure Indicators: Missing file, real API key, over 200 lines
    Evidence: .sisyphus/evidence/task-17-readme.txt
  ```

  **Commit**: YES
  - Message: `docs: add README with usage examples and setup guide`
  - Files: `README.md`
  - Pre-commit: none

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run CLI command). For each "Must NOT Have": search codebase for forbidden patterns (marker-pdf imports, hardcoded API keys, HTTP servers, databases) — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `python -m py_compile` on all .py files + `pytest` + check for type hints coverage. Review all changed files for: empty except blocks, hardcoded secrets, missing type hints, unused imports, commented-out code. Check AI slop: excessive docstrings, over-abstraction, generic variable names (data/result/item/temp).
  Output: `Build [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state (`pip install -e .`). Execute EVERY QA scenario from EVERY task — follow exact steps, capture evidence. Test cross-task integration: ArXiv ID → full MP3 with chapters and correct persona. Test edge cases: invalid ArXiv ID, missing API key, corrupted PDF, empty config. Save to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git log/diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance. Detect cross-task contamination: Task N touching Task M's files. Flag unaccounted changes. Verify NO marker-pdf, NO scholarly, NO ElevenLabs, NO web server code exists anywhere.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| After Task(s) | Message | Key Files | Verification |
|------------|---------|-------|--------------|
| 1 | `chore: scaffold peripatos-core project structure` | pyproject.toml, peripatos/, tests/, LICENSE | `pip install -e .` |
| 2 | `feat(config): add .env and YAML configuration system` | peripatos/config.py | `pytest tests/test_config.py` |
| 3 | `feat(types): add core data models and type definitions` | peripatos/models.py | `pytest tests/test_models.py` |
| 4 | `test: set up pytest infrastructure with fixtures and sample data` | conftest.py, tests/fixtures/ | `pytest --co` |
| 5 | `feat(parser): add PDF parsing via Docling` | peripatos/eye/parser.py | `pytest tests/test_parser.py` |
| 6 | `feat(arxiv): add ArXiv paper fetcher` | peripatos/eye/arxiv.py | `pytest tests/test_arxiv.py` |
| 7 | `feat(math): add LaTeX to spoken text normalization` | peripatos/eye/math_normalize.py | `pytest tests/test_math.py` |
| 8 | `feat(brain): add dialogue script generator with 4 persona archetypes` | peripatos/brain/ | `pytest tests/test_brain.py` |
| 9 | `feat(voice): add OpenAI TTS engine` | peripatos/voice/openai_tts.py | `pytest tests/test_openai_tts.py` |
| 10 | `feat(voice): add edge-tts fallback engine` | peripatos/voice/edge_tts_engine.py | `pytest tests/test_edge_tts.py` |
| 11 | `feat(voice): add audio renderer orchestrator with smart chunking` | peripatos/voice/renderer.py | `pytest tests/test_renderer.py` |
| 12 | `feat(brain): add bilingual code-switching (zh-en)` | peripatos/brain/bilingual.py | `pytest tests/test_bilingual.py` |
| 13 | `feat(voice): add audio mixer with chapter markers` | peripatos/voice/mixer.py | `pytest tests/test_mixer.py` |
| 14 | `feat(cli): add CLI orchestrator with argparse` | peripatos/cli.py | `peripatos --help` |
| 15 | `chore: finalize package distribution (entry points, metadata)` | pyproject.toml | `pip install -e . && peripatos --help` |
| 16 | `test: add end-to-end integration tests` | tests/test_e2e.py | `pytest tests/test_e2e.py` |
| 17 | `docs: add README with usage examples and setup guide` | README.md | visual inspection |

---

## Success Criteria

### Verification Commands
```bash
pip install -e .                        # Expected: successful install
peripatos --help                        # Expected: usage info with all options
peripatos generate 2408.09869           # Expected: MP3 file created in output/
peripatos generate 2408.09869 --persona skeptic  # Expected: skeptic-toned dialogue
peripatos generate 2408.09869 --language zh-en   # Expected: Chinese+English output
ffprobe -show_chapters output/*.mp3     # Expected: chapter metadata present
pytest                                  # Expected: all tests pass
pytest --cov=peripatos --cov-report=term  # Expected: >80% coverage
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass
- [ ] MIT LICENSE present
- [ ] No hardcoded API keys in any file
- [ ] Clean `pip install -e .` from fresh venv
