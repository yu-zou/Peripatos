# LLM Provider Extension: OpenRouter & Google Gemini

## TL;DR

> **Quick Summary**: Extend Peripatos LLM provider support from 2 (OpenAI, Anthropic) to 4 (+ OpenRouter, Google Gemini). Also improve `.env.example` documentation for `ENVIRONMENT` and `LOG_LEVEL` variables.
> 
> **Deliverables**:
> - OpenRouter provider fully wired: config → models → generator → CLI → tests
> - Google Gemini provider fully wired: config → models → generator → CLI → tests
> - `google-genai` dependency added to `pyproject.toml`
> - `.env.example` updated with new API keys and improved variable documentation
> - README.md updated with new provider options
> - All existing 164 tests still pass + new provider tests added
> 
> **Estimated Effort**: Short (2-3 hours implementation)
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 (foundation) → Task 3/4 (generator) → Task 7 (tests) → F1-F4

---

## Context

### Original Request
User noticed `.env.example` only supports OpenAI and Anthropic API keys. Requested:
1. Add OpenRouter as an LLM provider
2. Add Google Gemini as an LLM provider
3. Improve `.env.example` documentation for `ENVIRONMENT` and `LOG_LEVEL` variables

### Interview Summary
**Key Discussions**:
- MVP is 100% complete (35/35 tasks, 164 tests, 88% coverage)
- Adding providers follows a well-established pattern in the codebase (config → models → generator dispatch)
- OpenRouter uses the existing `openai` SDK with a custom `base_url` — zero new dependencies
- Google Gemini uses the `google-genai` SDK (NOT deprecated `google-generativeai`) — one new dependency

**Research Findings**:
- **OpenRouter**: `base_url="https://openrouter.ai/api/v1"`, env var `OPENROUTER_API_KEY`, model names like `openai/gpt-4o`, optional headers `HTTP-Referer`/`X-Title`
- **Google Gemini**: `google-genai` package, `client = genai.Client(api_key=...)`, `client.models.generate_content(model=..., contents=..., config=types.GenerateContentConfig(system_instruction=...))`, response via `response.text`, env var `GEMINI_API_KEY`
- **Metis review**: Recommended using existing string-matching retry pattern for consistency, confirmed `response.text` returning `None` flows safely into existing error handling

### Metis Review
**Identified Gaps** (addressed):
- Gemini rate-limit detection: Use `"resource_exhausted" in str(exc).lower() or "429" in str(exc)` alongside existing `"rate_limit"` check — consistent with codebase pattern
- Gemini `response.text` returning `None`: Falls into `json.loads(None)` → `TypeError` → caught as `GenerationError("Invalid JSON")` — acceptable, no special handling needed
- OpenRouter `max_tokens` parameter: Not needed for MVP — OpenRouter respects model defaults

---

## Work Objectives

### Core Objective
Add OpenRouter and Google Gemini as first-class LLM providers alongside existing OpenAI and Anthropic, following the established codebase patterns exactly.

### Concrete Deliverables
- `peripatos/models.py`: `LLMProvider` enum has 4 values (OPENAI, ANTHROPIC, OPENROUTER, GEMINI)
- `peripatos/config.py`: `VALID_LLM_PROVIDERS` includes all 4, API keys loaded from env, validation works
- `peripatos/brain/generator.py`: `_call_openrouter()` and `_call_gemini()` methods with retry logic
- `pyproject.toml`: `google-genai` added to dependencies
- `.env.example`: 4 API keys documented + improved ENVIRONMENT/LOG_LEVEL docs
- `README.md`: Updated CLI reference, configuration, and requirements sections
- Tests: All existing pass + new tests for OpenRouter and Gemini providers

### Definition of Done
- [ ] `peripatos generate --llm-provider openrouter --llm-model openai/gpt-4o --help` shows openrouter as valid choice
- [ ] `peripatos generate --llm-provider gemini --llm-model gemini-2.0-flash --help` shows gemini as valid choice
- [ ] `pytest` → all tests pass (existing 164 + new provider tests)
- [ ] `.env.example` contains `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, and expanded ENVIRONMENT/LOG_LEVEL docs

### Must Have
- OpenRouter provider using existing `openai` SDK with custom `base_url`
- Gemini provider using `google-genai` SDK with `genai.Client` and `generate_content()`
- Lazy SDK imports via `importlib.import_module()` (matches existing pattern)
- Retry logic with exponential backoff for both new providers (matches existing pattern)
- API key validation in `validate_api_keys()` for both new providers
- `.env.example` improved with ENVIRONMENT and LOG_LEVEL explanations

### Must NOT Have (Guardrails)
- NO refactoring of existing OpenAI/Anthropic provider code — only additive changes
- NO provider-specific CLI flags (e.g., no `--openrouter-referer`) — keep it simple
- NO streaming support — existing providers don't use it
- NO async calls — existing providers use sync
- NO fallback model routing (OpenRouter feature) — out of scope
- NO multimodal support (Gemini feature) — out of scope
- NO changes to `_parse_response()` — all providers must return JSON-array-of-turns string
- NO over-abstraction (no provider base class, no plugin system) — keep the existing if/elif dispatch
- NO changes to TTS engines or any non-LLM code

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest + pytest-cov + pytest-asyncio)
- **Automated tests**: YES (tests-after, matching existing pattern)
- **Framework**: pytest
- **Pattern**: Follow existing mock patterns in `test_brain.py` (patch `importlib.import_module`)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Config/Models**: Use Bash (python -c) — Import, instantiate, assert values
- **Generator**: Use Bash (pytest) — Run specific test files
- **CLI**: Use Bash (peripatos generate --help) — Verify choices shown
- **Full suite**: Use Bash (pytest) — All tests pass

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — foundation changes, all independent of each other):
├── Task 1: Models + Config + pyproject.toml (enum, validation, dependency) [quick]
├── Task 2: .env.example improvements (API keys + ENVIRONMENT/LOG_LEVEL docs) [quick]

Wave 2 (After Wave 1 — generator + docs, can run in parallel):
├── Task 3: Generator — OpenRouter provider method [unspecified-high]
├── Task 4: Generator — Gemini provider method [unspecified-high]
├── Task 5: README.md updates [quick]

Wave 3 (After Wave 2 — tests + verification):
├── Task 6: Tests — config and models [quick]
├── Task 7: Tests — generator (OpenRouter + Gemini) [unspecified-high]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
├── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → Task 3/4 → Task 7 → F1-F4
Parallel Speedup: ~50% faster than sequential
Max Concurrent: 3 (Wave 2)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1 | — | 3, 4, 5, 6, 7 |
| 2 | — | 5 |
| 3 | 1 | 7 |
| 4 | 1 | 7 |
| 5 | 1, 2 | — |
| 6 | 1 | — |
| 7 | 3, 4 | — |
| F1-F4 | ALL | — |

### Agent Dispatch Summary

- **Wave 1**: 2 tasks — T1 → `quick`, T2 → `quick`
- **Wave 2**: 3 tasks — T3 → `unspecified-high`, T4 → `unspecified-high`, T5 → `quick`
- **Wave 3**: 2 tasks — T6 → `quick`, T7 → `unspecified-high`
- **FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Foundation: Models + Config + pyproject.toml

  **What to do**:
  - Add `OPENROUTER = "openrouter"` and `GEMINI = "gemini"` to the `LLMProvider` enum in `peripatos/models.py` (after line 58, before the closing of the class)
  - Add `"openrouter"` and `"gemini"` to `VALID_LLM_PROVIDERS` set in `peripatos/config.py` line 13
  - Add two new fields to `PeripatosConfig` dataclass in `peripatos/config.py`:
    - `openrouter_api_key: str | None = field(default=None)` (after line 138)
    - `gemini_api_key: str | None = field(default=None)` (after openrouter_api_key)
  - Add `os.getenv("OPENROUTER_API_KEY")` and `os.getenv("GEMINI_API_KEY")` to the `config_dict` in `load_config()` (after line 258)
  - Pass both new keys through to `PeripatosConfig(...)` constructor call (lines 268-279)
  - Extend `validate_api_keys()` with two new checks matching existing pattern:
    - `if self.llm_provider == "openrouter" and not self.openrouter_api_key:` → raise ValueError mentioning `OPENROUTER_API_KEY`
    - `if self.llm_provider == "gemini" and not self.gemini_api_key:` → raise ValueError mentioning `GEMINI_API_KEY`
  - Add `"google-genai>=1.0.0"` to `dependencies` list in `pyproject.toml` (after line 27, alongside existing `anthropic`)
  - Update `PeripatosConfig` docstring to mention new providers and API key fields

  **Must NOT do**:
  - Do NOT change the default provider (keep `"openai"` as default)
  - Do NOT refactor existing validation code — only add new elif/if blocks
  - Do NOT add provider-specific config fields beyond API keys (no base_url config, no headers config)

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward additive changes to existing patterns — enum values, set members, dataclass fields, env reads
  - **Skills**: []
    - No specialized skills needed — standard Python file editing

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Tasks 3, 4, 5, 6, 7
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `peripatos/models.py:54-58` — LLMProvider enum: add new members after `ANTHROPIC = "anthropic"` following same `NAME = "value"` pattern
  - `peripatos/config.py:13` — `VALID_LLM_PROVIDERS` set: add new string literals to the set
  - `peripatos/config.py:137-138` — Existing API key fields (`openai_api_key`, `anthropic_api_key`): follow same `str | None = field(default=None)` pattern
  - `peripatos/config.py:257-258` — Existing `os.getenv()` calls: follow same pattern for new env var names
  - `peripatos/config.py:180-192` — Existing `validate_api_keys()` checks: follow same if/raise pattern
  - `peripatos/config.py:268-279` — Existing `PeripatosConfig(...)` constructor: add new key params

  **API/Type References**:
  - `peripatos/config.py:112-138` — Full `PeripatosConfig` dataclass definition showing all current fields

  **External References**:
  - None needed — purely internal changes

  **Acceptance Criteria**:

  - [ ] `python -c "from peripatos.models import LLMProvider; print(sorted(p.value for p in LLMProvider))"` → prints `['anthropic', 'gemini', 'openai', 'openrouter']`
  - [ ] `python -c "from peripatos.config import VALID_LLM_PROVIDERS; print(sorted(VALID_LLM_PROVIDERS))"` → prints `['anthropic', 'gemini', 'openai', 'openrouter']`
  - [ ] `python -c "from peripatos.config import PeripatosConfig; print(hasattr(PeripatosConfig, '__dataclass_fields__') and 'openrouter_api_key' in PeripatosConfig.__dataclass_fields__ and 'gemini_api_key' in PeripatosConfig.__dataclass_fields__)"` → prints `True`

  **QA Scenarios**:

  ```
  Scenario: LLMProvider enum has 4 values
    Tool: Bash (python -c)
    Preconditions: Package installed in dev mode (pip install -e .)
    Steps:
      1. Run: python -c "from peripatos.models import LLMProvider; vals = sorted(p.value for p in LLMProvider); print(vals); assert vals == ['anthropic', 'gemini', 'openai', 'openrouter'], f'Expected 4 providers, got {vals}'"
    Expected Result: Prints ['anthropic', 'gemini', 'openai', 'openrouter'] with no assertion error
    Failure Indicators: ImportError, AssertionError, or missing enum values
    Evidence: .sisyphus/evidence/task-1-enum-values.txt

  Scenario: Config validates new providers
    Tool: Bash (python -c)
    Preconditions: Package installed
    Steps:
      1. Run: python -c "from peripatos.config import PeripatosConfig; c = PeripatosConfig(llm_provider='openrouter', llm_model='openai/gpt-4o', tts_engine='openai', tts_voice_host='alloy', tts_voice_expert='onyx', persona='tutor', language='en', output_dir='./out'); print('openrouter OK')"
      2. Run: python -c "from peripatos.config import PeripatosConfig; c = PeripatosConfig(llm_provider='gemini', llm_model='gemini-2.0-flash', tts_engine='openai', tts_voice_host='alloy', tts_voice_expert='onyx', persona='tutor', language='en', output_dir='./out'); print('gemini OK')"
      3. Run: python -c "
from peripatos.config import PeripatosConfig
try:
    c = PeripatosConfig(llm_provider='invalid', llm_model='x', tts_engine='openai', tts_voice_host='alloy', tts_voice_expert='onyx', persona='tutor', language='en', output_dir='./out')
    print('FAIL: no error')
except ValueError as e:
    print(f'OK: {e}')
"
    Expected Result: First two print 'openrouter OK' and 'gemini OK'; third prints 'OK: Invalid LLM provider...'
    Failure Indicators: ValueError on valid providers, or no error on invalid provider
    Evidence: .sisyphus/evidence/task-1-config-validation.txt

  Scenario: API key validation for new providers
    Tool: Bash (python -c)
    Preconditions: No OPENROUTER_API_KEY or GEMINI_API_KEY in environment
    Steps:
      1. Run: python -c "
from peripatos.config import PeripatosConfig
c = PeripatosConfig(llm_provider='openrouter', llm_model='x', tts_engine='openai', tts_voice_host='alloy', tts_voice_expert='onyx', persona='tutor', language='en', output_dir='./out')
try:
    c.validate_api_keys()
    print('FAIL: no error')
except ValueError as e:
    assert 'OPENROUTER_API_KEY' in str(e), f'Wrong error: {e}'
    print(f'OK: {e}')
"
      2. Run same pattern for gemini/GEMINI_API_KEY
    Expected Result: Both print 'OK:' with correct env var name in error message
    Failure Indicators: No ValueError raised, or wrong env var name in error
    Evidence: .sisyphus/evidence/task-1-api-key-validation.txt

  Scenario: google-genai in pyproject.toml
    Tool: Bash (grep)
    Steps:
      1. Run: grep "google-genai" pyproject.toml
    Expected Result: Output contains `"google-genai>=1.0.0"` (or similar version constraint)
    Failure Indicators: No match found
    Evidence: .sisyphus/evidence/task-1-pyproject-dep.txt
  ```

  **Commit**: YES
  - Message: `feat(config): add openrouter and gemini to LLM provider support`
  - Files: `peripatos/models.py`, `peripatos/config.py`, `pyproject.toml`
  - Pre-commit: `python -c "from peripatos.models import LLMProvider; assert len(list(LLMProvider)) == 4"`

- [x] 2. Improve .env.example documentation

  **What to do**:
  - Add `OPENROUTER_API_KEY` entry with documentation comment explaining OpenRouter (unified API gateway for multiple LLM providers), where to get the key (`https://openrouter.ai/keys`), and that model names use `provider/model` format
  - Add `GEMINI_API_KEY` entry with documentation comment explaining Google Gemini, where to get the key (`https://ai.google.dev`), and example model names
  - Expand `ENVIRONMENT` documentation (line 14-16) to explain:
    - `development`: Enables verbose logging, detailed error messages, and debug output
    - `production`: Minimal logging, concise error messages, optimized for end-user experience
    - `testing`: Used by test suite, may mock external services
  - Expand `LOG_LEVEL` documentation (line 22-24) to explain:
    - `DEBUG`: All messages including internal state — useful for debugging API calls and parsing
    - `INFO`: General progress messages (default) — shows pipeline stages
    - `WARNING`: Only potential issues — e.g., fallback behaviors triggered
    - `ERROR`: Only failures — API errors, parsing failures
    - `CRITICAL`: Only fatal errors that stop execution

  **Must NOT do**:
  - Do NOT change existing OPENAI_API_KEY or ANTHROPIC_API_KEY entries (only add new ones)
  - Do NOT add config values that aren't actually read by the application (ENVIRONMENT and LOG_LEVEL are already there — just improve their docs)
  - Do NOT add excessive boilerplate — keep it practical

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single file edit, documentation only, no code logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 5
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References**:
  - `.env.example:1-25` — Full current file. Follow existing comment style (# header, # description, # URL, then VAR=placeholder)

  **External References**:
  - OpenRouter keys page: `https://openrouter.ai/keys`
  - Google AI Studio: `https://ai.google.dev`

  **Acceptance Criteria**:

  - [ ] `.env.example` contains `OPENROUTER_API_KEY=your-openrouter-api-key-here`
  - [ ] `.env.example` contains `GEMINI_API_KEY=your-gemini-api-key-here`
  - [ ] `ENVIRONMENT` section has at least 3 lines of explanation (development/production/testing)
  - [ ] `LOG_LEVEL` section has at least 5 lines of explanation (DEBUG/INFO/WARNING/ERROR/CRITICAL)

  **QA Scenarios**:

  ```
  Scenario: New API keys present in .env.example
    Tool: Bash (grep)
    Steps:
      1. Run: grep "OPENROUTER_API_KEY" .env.example
      2. Run: grep "GEMINI_API_KEY" .env.example
      3. Run: grep -c "API_KEY" .env.example
    Expected Result: Both greps find matches; count is exactly 4
    Failure Indicators: Missing entries or count != 4
    Evidence: .sisyphus/evidence/task-2-env-api-keys.txt

  Scenario: ENVIRONMENT documentation expanded
    Tool: Bash (grep)
    Steps:
      1. Run: grep -A 5 "ENVIRONMENT" .env.example
    Expected Result: Output shows at least 3 option descriptions (development, production, testing)
    Failure Indicators: Only single-line comment like before
    Evidence: .sisyphus/evidence/task-2-env-environment-docs.txt

  Scenario: LOG_LEVEL documentation expanded
    Tool: Bash (grep)
    Steps:
      1. Run: grep -A 7 "LOG_LEVEL" .env.example
    Expected Result: Output shows descriptions for DEBUG, INFO, WARNING, ERROR, CRITICAL
    Failure Indicators: Only single-line comment listing options
    Evidence: .sisyphus/evidence/task-2-env-loglevel-docs.txt
  ```

  **Commit**: YES
  - Message: `docs(env): improve .env.example with new API keys and variable docs`
  - Files: `.env.example`
  - Pre-commit: `grep -c "API_KEY" .env.example | grep -q 4`

- [x] 3. Generator: OpenRouter provider method

  **What to do**:
  - Add `self._openrouter_client = None` to `DialogueGenerator.__init__()` (line 28, alongside existing client attributes)
  - Add dispatch branch in `_call_llm()` (after line 86): `if provider == LLMProvider.OPENROUTER: return self._call_openrouter(config, system_prompt, content)`
  - Implement `_call_openrouter(self, config, system_prompt, content) -> str`:
    - Lazy import: `openai_module = importlib.import_module("openai")` (reuses existing openai SDK)
    - On `ImportError`: raise `GenerationError("OpenAI client not available (required for OpenRouter)")` 
    - Create client: `self._openrouter_client = openai_module.OpenAI(base_url="https://openrouter.ai/api/v1", api_key=config.openrouter_api_key)`
    - Call: `self._openrouter_client.chat.completions.create(model=config.llm_model, messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": content}])` — same as OpenAI pattern
    - Extract response: `completion.choices[0].message.content` — identical to OpenAI
    - Retry logic: Same pattern as `_call_openai()` — retry on `"rate_limit"` in error string, exponential backoff with `time.sleep(2 ** attempt)`
    - Error prefix: `"OpenRouter API call failed: {exc}"`

  **Must NOT do**:
  - Do NOT add `HTTP-Referer` or `X-Title` headers (optional, out of scope for MVP)
  - Do NOT add fallback model routing
  - Do NOT modify `_call_openai()` — OpenRouter gets its own method even though it uses the same SDK
  - Do NOT add streaming support

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Requires understanding the existing generator pattern and correctly adapting it for OpenRouter's OpenAI-compatible API
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 4, 5)
  - **Blocks**: Task 7
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `peripatos/brain/generator.py:23-28` — `__init__` showing client attribute initialization pattern
  - `peripatos/brain/generator.py:78-87` — `_call_llm()` dispatch: add new branch after Anthropic check
  - `peripatos/brain/generator.py:89-115` — `_call_openai()`: THIS IS THE TEMPLATE. OpenRouter method is nearly identical but with `base_url` and different API key
  - `peripatos/config.py:112-138` — `PeripatosConfig` fields including `openrouter_api_key` (added by Task 1)

  **API/Type References**:
  - `peripatos/models.py:54-58` — `LLMProvider` enum with `OPENROUTER` value (added by Task 1)

  **External References**:
  - OpenRouter API docs: `https://openrouter.ai/docs/api-reference/overview` — OpenAI-compatible chat completions endpoint
  - OpenRouter base URL: `https://openrouter.ai/api/v1`

  **WHY Each Reference Matters**:
  - `generator.py:89-115` is the PRIMARY template — OpenRouter is literally the OpenAI SDK with a different `base_url` and `api_key`, so `_call_openrouter` should be almost a copy of `_call_openai` with those two differences

  **Acceptance Criteria**:

  - [ ] `_call_openrouter` method exists in `DialogueGenerator`
  - [ ] Method uses `base_url="https://openrouter.ai/api/v1"` when creating client
  - [ ] Method uses `config.openrouter_api_key` for authentication
  - [ ] `_call_llm` dispatches to `_call_openrouter` when provider is `LLMProvider.OPENROUTER`

  **QA Scenarios**:

  ```
  Scenario: OpenRouter dispatch exists in _call_llm
    Tool: Bash (grep)
    Steps:
      1. Run: grep -n "OPENROUTER" peripatos/brain/generator.py
    Expected Result: At least 2 matches — one in dispatch, one in method definition
    Failure Indicators: No matches or only 1 match
    Evidence: .sisyphus/evidence/task-3-openrouter-dispatch.txt

  Scenario: OpenRouter uses correct base_url
    Tool: Bash (grep)
    Steps:
      1. Run: grep "openrouter.ai/api/v1" peripatos/brain/generator.py
    Expected Result: Line containing `base_url="https://openrouter.ai/api/v1"`
    Failure Indicators: No match — wrong URL or missing base_url parameter
    Evidence: .sisyphus/evidence/task-3-openrouter-baseurl.txt

  Scenario: OpenRouter uses openrouter_api_key from config
    Tool: Bash (grep)
    Steps:
      1. Run: grep "openrouter_api_key" peripatos/brain/generator.py
    Expected Result: Line containing `config.openrouter_api_key`
    Failure Indicators: Uses wrong config field or hardcoded key
    Evidence: .sisyphus/evidence/task-3-openrouter-apikey.txt

  Scenario: OpenRouter retry logic present
    Tool: Bash (grep)
    Steps:
      1. Run: grep -A 20 "def _call_openrouter" peripatos/brain/generator.py | grep "rate_limit"
    Expected Result: Rate limit string detection present in method
    Failure Indicators: No retry logic
    Evidence: .sisyphus/evidence/task-3-openrouter-retry.txt
  ```

  **Commit**: YES (groups with Task 4)
  - Message: `feat(generator): implement openrouter and gemini LLM dispatch`
  - Files: `peripatos/brain/generator.py`
  - Pre-commit: `python -c "from peripatos.brain.generator import DialogueGenerator; g = DialogueGenerator(); assert hasattr(g, '_openrouter_client')"`

- [x] 4. Generator: Gemini provider method

  **What to do**:
  - Add `self._gemini_client = None` to `DialogueGenerator.__init__()` (alongside other client attributes)
  - Add dispatch branch in `_call_llm()`: `if provider == LLMProvider.GEMINI: return self._call_gemini(config, system_prompt, content)`
  - Implement `_call_gemini(self, config, system_prompt, content) -> str`:
    - Lazy import: `genai_module = importlib.import_module("google.genai")` and `types_module = importlib.import_module("google.genai.types")`
    - On `ImportError`: raise `GenerationError("Google GenAI client not available")`
    - Create client: `self._gemini_client = genai_module.Client(api_key=config.gemini_api_key)`
    - Build config: `gen_config = types_module.GenerateContentConfig(system_instruction=system_prompt)`
    - Call: `response = self._gemini_client.models.generate_content(model=config.llm_model, contents=content, config=gen_config)`
    - Extract response: `response.text`
    - Retry logic: Same exponential backoff pattern, but detect rate limits via `"rate_limit" in str(exc).lower() or "resource_exhausted" in str(exc).lower() or "429" in str(exc)`
    - Error prefix: `"Gemini API call failed: {exc}"`
  - Remove the final unreachable `raise GenerationError(...)` at old line 87 — it's now covered by the dispatch branches (or keep it as a safety net, either is fine)

  **Must NOT do**:
  - Do NOT use deprecated `google-generativeai` package — use `google.genai` (the `google-genai` package)
  - Do NOT add multimodal support
  - Do NOT add async calls (`client.aio.models...`)
  - Do NOT add streaming (`generate_content_stream`)
  - Do NOT import typed exception classes from google.genai — use string matching for consistency

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Gemini SDK has a different API shape than OpenAI — requires careful adaptation of the generate_content call and response extraction
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 5)
  - **Blocks**: Task 7
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `peripatos/brain/generator.py:23-28` — `__init__` client attributes pattern
  - `peripatos/brain/generator.py:78-87` — `_call_llm()` dispatch
  - `peripatos/brain/generator.py:117-141` — `_call_anthropic()`: Closest pattern since Gemini also has a different API shape (not OpenAI-compatible). Shows how to handle different SDK method signatures
  - `peripatos/brain/generator.py:89-115` — `_call_openai()`: Shows retry pattern to replicate

  **API/Type References**:
  - `peripatos/models.py:54-58` — `LLMProvider.GEMINI` (added by Task 1)
  - `peripatos/config.py:112-138` — `PeripatosConfig.gemini_api_key` (added by Task 1)

  **External References**:
  - Google GenAI Python SDK: `https://ai.google.dev/gemini-api/docs/text-generation` — `generate_content` API
  - Package: `google-genai` on PyPI — import as `from google import genai` and `from google.genai import types`
  - System instruction pattern: `types.GenerateContentConfig(system_instruction="...")` passed as `config` parameter
  - Response: `response.text` returns the generated text string (or `None` if no candidates)

  **WHY Each Reference Matters**:
  - `generator.py:117-141` (Anthropic) is the best template since Gemini, like Anthropic, has its own SDK with different method names. The pattern of "lazy import → create client → call with retry → extract text" is identical
  - The Gemini SDK uses `generate_content()` not `chat.completions.create()`, and `system_instruction` goes in config not as a message — this is the key difference to get right

  **Acceptance Criteria**:

  - [ ] `_call_gemini` method exists in `DialogueGenerator`
  - [ ] Method imports `google.genai` and `google.genai.types` via `importlib.import_module`
  - [ ] Method uses `config.gemini_api_key` for authentication
  - [ ] Method passes `system_instruction` via `GenerateContentConfig`, NOT as a message
  - [ ] Method extracts response via `response.text`
  - [ ] `_call_llm` dispatches to `_call_gemini` when provider is `LLMProvider.GEMINI`

  **QA Scenarios**:

  ```
  Scenario: Gemini dispatch exists in _call_llm
    Tool: Bash (grep)
    Steps:
      1. Run: grep -n "GEMINI" peripatos/brain/generator.py
    Expected Result: At least 2 matches — one in dispatch, one in method definition
    Failure Indicators: No matches
    Evidence: .sisyphus/evidence/task-4-gemini-dispatch.txt

  Scenario: Gemini uses google.genai import
    Tool: Bash (grep)
    Steps:
      1. Run: grep "google.genai" peripatos/brain/generator.py
    Expected Result: Lines showing importlib.import_module("google.genai") and import_module("google.genai.types")
    Failure Indicators: Uses deprecated google.generativeai or direct import
    Evidence: .sisyphus/evidence/task-4-gemini-import.txt

  Scenario: Gemini uses system_instruction in config
    Tool: Bash (grep)
    Steps:
      1. Run: grep "system_instruction" peripatos/brain/generator.py
    Expected Result: Line containing `system_instruction=system_prompt` in GenerateContentConfig
    Failure Indicators: System prompt passed as message content instead
    Evidence: .sisyphus/evidence/task-4-gemini-system-instruction.txt

  Scenario: Gemini response extraction uses response.text
    Tool: Bash (grep)
    Steps:
      1. Run: grep -A 30 "def _call_gemini" peripatos/brain/generator.py | grep "\.text"
    Expected Result: Line showing `response.text` for text extraction
    Failure Indicators: Uses different extraction pattern
    Evidence: .sisyphus/evidence/task-4-gemini-response.txt
  ```

  **Commit**: YES (groups with Task 3)
  - Message: `feat(generator): implement openrouter and gemini LLM dispatch`
  - Files: `peripatos/brain/generator.py`
  - Pre-commit: `python -c "from peripatos.brain.generator import DialogueGenerator; g = DialogueGenerator(); assert hasattr(g, '_gemini_client')"`

- [x] 5. Update README.md

  **What to do**:
  - Update the Configuration section (around line 37-42): Add `OPENROUTER_API_KEY` and `GEMINI_API_KEY` to the `.env` example block
  - Update the CLI Reference section (around line 61-82): Change `--llm-provider {anthropic,openai}` to `--llm-provider {anthropic,gemini,openai,openrouter}` in the usage text
  - Update the Requirements section (around line 84-89): Change "API keys for OpenAI or Anthropic" to "API keys for at least one LLM provider (OpenAI, Anthropic, OpenRouter, or Google Gemini)"
  - Add OpenRouter and Google Gemini to the Acknowledgments section

  **Must NOT do**:
  - Do NOT rewrite the entire README
  - Do NOT add extensive provider-specific documentation (keep it concise like existing entries)
  - Do NOT add a new "Providers" section — integrate into existing sections

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple text updates in a markdown file
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 3, 4)
  - **Blocks**: None
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References**:
  - `README.md:35-42` — Configuration section with `.env` example block
  - `README.md:59-82` — CLI Reference section with usage text
  - `README.md:84-89` — Requirements section
  - `README.md:103-108` — Acknowledgments section

  **Acceptance Criteria**:

  - [ ] README shows 4 providers in `--llm-provider` choices
  - [ ] README configuration section mentions all 4 API keys
  - [ ] README requirements section mentions all 4 providers
  - [ ] Acknowledgments includes OpenRouter and Google Gemini

  **QA Scenarios**:

  ```
  Scenario: README CLI reference shows all 4 providers
    Tool: Bash (grep)
    Steps:
      1. Run: grep "llm-provider" README.md
    Expected Result: Line containing `{anthropic,gemini,openai,openrouter}` (sorted)
    Failure Indicators: Only shows 2 providers
    Evidence: .sisyphus/evidence/task-5-readme-cli.txt

  Scenario: README has all 4 API key entries
    Tool: Bash (grep)
    Steps:
      1. Run: grep "API_KEY" README.md
    Expected Result: Lines mentioning OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY, GEMINI_API_KEY
    Failure Indicators: Missing new API keys
    Evidence: .sisyphus/evidence/task-5-readme-apikeys.txt
  ```

  **Commit**: YES
  - Message: `docs(readme): update for openrouter and gemini providers`
  - Files: `README.md`
  - Pre-commit: `grep -q "openrouter" README.md && grep -q "gemini" README.md`

- [x] 6. Tests: Config and Models

  **What to do**:
  - Update `tests/test_models.py:71-76` — `test_llm_provider_has_two_values`: Change expected count from 2 to 4, and expected set from `{"OPENAI", "ANTHROPIC"}` to `{"OPENAI", "ANTHROPIC", "OPENROUTER", "GEMINI"}`. Rename test method to `test_llm_provider_has_four_values`.
  - Add test to `tests/test_config.py` in `TestEnvVarLoading`:
    - `test_openrouter_and_gemini_env_vars_loaded`: Patch env with `OPENROUTER_API_KEY` and `GEMINI_API_KEY`, call `load_config()`, assert `config.openrouter_api_key` and `config.gemini_api_key` match
  - Add tests to `tests/test_config.py` in `TestAPIKeyValidation`:
    - `test_missing_openrouter_api_key_raises_error`: Set provider to "openrouter" in YAML, no env key, assert `validate_api_keys()` raises ValueError with "OPENROUTER_API_KEY"
    - `test_missing_gemini_api_key_raises_error`: Set provider to "gemini" in YAML, no env key, assert `validate_api_keys()` raises ValueError with "GEMINI_API_KEY"
    - `test_openrouter_api_key_validation_passes_with_key`: Patch `OPENROUTER_API_KEY` env, set provider to "openrouter", assert `validate_api_keys()` does not raise
    - `test_gemini_api_key_validation_passes_with_key`: Same for Gemini
  - Add test to `tests/test_config.py` in `TestConfigDataclass`:
    - Verify `config` has `openrouter_api_key` and `gemini_api_key` attributes
  - Optionally add test in `tests/test_cli.py`: Parse args with `--llm-provider openrouter` and `--llm-provider gemini`, verify accepted

  **Must NOT do**:
  - Do NOT modify existing test assertions for OpenAI/Anthropic — only add/extend
  - Do NOT delete existing tests

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Tests follow well-established patterns already in the file — copy-adapt existing tests
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 7)
  - **Blocks**: None
  - **Blocked By**: Task 1

  **References**:

  **Pattern References**:
  - `tests/test_models.py:71-76` — Existing `test_llm_provider_has_two_values` — update to 4
  - `tests/test_config.py:121-131` — `test_env_vars_override_config`: Follow this pattern for new env vars
  - `tests/test_config.py:159-170` — `test_missing_openai_api_key_raises_error`: Copy this pattern for openrouter/gemini
  - `tests/test_config.py:171-191` — `test_missing_anthropic_api_key_raises_error`: Another template
  - `tests/test_config.py:193-200` — `test_api_key_validation_passes_with_key`: Follow for pass cases
  - `tests/test_config.py:258-274` — `test_config_dataclass_attributes`: Add new attribute checks

  **Acceptance Criteria**:

  - [ ] `pytest tests/test_models.py -v` → passes, shows test for 4 providers
  - [ ] `pytest tests/test_config.py -v` → passes, shows new API key validation tests
  - [ ] At least 4 new test functions added across config/models test files

  **QA Scenarios**:

  ```
  Scenario: Model enum test updated
    Tool: Bash (pytest)
    Steps:
      1. Run: pytest tests/test_models.py::TestEnumValues -v
    Expected Result: All enum tests pass including updated LLMProvider test
    Failure Indicators: Test failure mentioning "2" vs "4" or missing enum values
    Evidence: .sisyphus/evidence/task-6-test-models.txt

  Scenario: Config validation tests pass
    Tool: Bash (pytest)
    Steps:
      1. Run: pytest tests/test_config.py -v
    Expected Result: All tests pass including new openrouter/gemini API key tests
    Failure Indicators: Any test failures
    Evidence: .sisyphus/evidence/task-6-test-config.txt

  Scenario: No existing tests broken
    Tool: Bash (pytest)
    Steps:
      1. Run: pytest tests/test_models.py tests/test_config.py -v --tb=short
    Expected Result: 0 failures, all original + new tests pass
    Failure Indicators: Any FAILED lines in output
    Evidence: .sisyphus/evidence/task-6-no-regressions.txt
  ```

  **Commit**: YES (groups with Task 7)
  - Message: `test: add openrouter and gemini provider tests`
  - Files: `tests/test_models.py`, `tests/test_config.py`
  - Pre-commit: `pytest tests/test_models.py tests/test_config.py -q`

- [x] 7. Tests: Generator (OpenRouter + Gemini)

  **What to do**:
  - Update `_build_config()` helper in `tests/test_brain.py` to accept new providers by adding `openrouter_api_key="test-openrouter"` and `gemini_api_key="test-gemini"` to the `PeripatosConfig(...)` call
  - Add `test_generator_openrouter_integration`:
    - Mock `importlib.import_module` to return a mock module with `OpenAI` class
    - Configure mock: `mock_openai_module.OpenAI.return_value = mock_client`
    - Verify client created with `base_url="https://openrouter.ai/api/v1"` and `api_key="test-openrouter"`
    - Configure mock response: `mock_response.choices = [Mock(message=Mock(content=_json_dialogue()))]`
    - Call `generator.generate(paper, _build_config("openrouter"))`
    - Assert `mock_client.chat.completions.create` called with correct model and messages
    - Assert script has correct turns
  - Add `test_generator_gemini_integration`:
    - Mock `importlib.import_module` to handle TWO calls: one for `"google.genai"` returning mock genai module, one for `"google.genai.types"` returning mock types module
    - Use `side_effect` on `mock_import_module` to return different mocks based on module name argument
    - Configure mock: `mock_genai_module.Client.return_value = mock_client`
    - Configure mock types: `mock_types_module.GenerateContentConfig = Mock(return_value=mock_config)`
    - Configure mock response: `mock_response.text = _json_dialogue()`
    - Call `generator.generate(paper, _build_config("gemini"))`
    - Assert `mock_client.models.generate_content` called with `model=config.llm_model`, `contents=content`, `config=mock_config`
    - Assert script has correct turns
  - Add `test_openrouter_import_error`:
    - Mock `importlib.import_module` to raise `ImportError`
    - Assert `GenerationError("OpenAI client not available")` raised
  - Add `test_gemini_import_error`:
    - Mock `importlib.import_module` to raise `ImportError`
    - Assert `GenerationError("Google GenAI client not available")` raised

  **Must NOT do**:
  - Do NOT modify existing OpenAI/Anthropic test functions
  - Do NOT make real API calls
  - Do NOT test streaming or async

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Gemini mock requires handling multiple `importlib.import_module` calls with `side_effect` — more complex than simple mocking
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 6)
  - **Blocks**: None
  - **Blocked By**: Tasks 3, 4

  **References**:

  **Pattern References**:
  - `tests/test_brain.py:21-33` — `_build_config()` helper: Add new API key fields
  - `tests/test_brain.py:78-103` — `test_generate_dialogue_openai_integration`: Primary template for OpenRouter test (same SDK, just verify base_url)
  - `tests/test_brain.py:106-124` — `test_generator_anthropic_integration`: Template showing different SDK shape assertion
  - `tests/test_brain.py:144-160` — `test_api_failure_retry_raises_generation_error`: Retry pattern test reference

  **API/Type References**:
  - `peripatos/brain/generator.py` — The actual methods being tested (after Tasks 3, 4 are complete)
  - `peripatos/config.py:112-138` — `PeripatosConfig` with new fields (after Task 1)

  **WHY Each Reference Matters**:
  - `test_brain.py:78-103` is the exact pattern for OpenRouter — mock OpenAI module, assert `chat.completions.create` called correctly. Only difference: verify `base_url` passed to constructor
  - `test_brain.py:106-124` shows how to assert different SDK method names (for Gemini: `models.generate_content` instead of `chat.completions.create`)
  - `_build_config()` must be updated FIRST or all new tests will fail with missing field errors

  **Acceptance Criteria**:

  - [ ] `pytest tests/test_brain.py -v` → all tests pass (existing + 4 new)
  - [ ] OpenRouter test verifies `base_url` parameter
  - [ ] Gemini test verifies `generate_content` call with `system_instruction` in config
  - [ ] Import error tests verify graceful GenerationError for both providers

  **QA Scenarios**:

  ```
  Scenario: All brain tests pass including new providers
    Tool: Bash (pytest)
    Steps:
      1. Run: pytest tests/test_brain.py -v --tb=short
    Expected Result: All tests pass, including test_generator_openrouter_integration, test_generator_gemini_integration, test_openrouter_import_error, test_gemini_import_error
    Failure Indicators: Any FAILED lines
    Evidence: .sisyphus/evidence/task-7-test-brain.txt

  Scenario: Full test suite still passes
    Tool: Bash (pytest)
    Steps:
      1. Run: pytest --tb=short -q
    Expected Result: All tests pass (164 existing + new), 0 failures
    Failure Indicators: Any failures or errors
    Evidence: .sisyphus/evidence/task-7-full-suite.txt

  Scenario: No existing tests broken
    Tool: Bash (pytest)
    Steps:
      1. Run: pytest tests/test_brain.py::test_generate_dialogue_openai_integration tests/test_brain.py::test_generator_anthropic_integration -v
    Expected Result: Both existing tests still pass unchanged
    Failure Indicators: Failure in existing tests (regression)
    Evidence: .sisyphus/evidence/task-7-no-regressions.txt
  ```

  **Commit**: YES (groups with Task 6)
  - Message: `test: add openrouter and gemini provider tests`
  - Files: `tests/test_brain.py`
  - Pre-commit: `pytest tests/test_brain.py -q`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest` + check all changed files for: `as any`/`@ts-ignore` equivalents, empty catches, print statements in prod code, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names. Verify no provider base class or plugin system was introduced.
  Output: `Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Run `peripatos generate --help` and verify all 4 providers shown in `--llm-provider` choices. Run `python -c "from peripatos.models import LLMProvider; print([p.value for p in LLMProvider])"` and verify 4 values. Run `python -c "from peripatos.config import VALID_LLM_PROVIDERS; print(sorted(VALID_LLM_PROVIDERS))"` and verify 4 values. Run `pytest -v` and verify all pass. Check `.env.example` contains all 4 API keys and improved docs. Save all output to `.sisyphus/evidence/final-qa/`.
  Output: `Scenarios [N/N pass] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff (git diff). Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance — especially: no refactoring of existing providers, no provider base class, no streaming, no async. Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

- **Wave 1**: `feat(config): add openrouter and gemini to LLM provider support` — models.py, config.py, pyproject.toml
- **Wave 1**: `docs(env): improve .env.example with new API keys and variable docs` — .env.example
- **Wave 2**: `feat(generator): implement openrouter and gemini LLM dispatch` — generator.py
- **Wave 2**: `docs(readme): update for openrouter and gemini providers` — README.md
- **Wave 3**: `test: add openrouter and gemini provider tests` — test_models.py, test_config.py, test_brain.py

---

## Success Criteria

### Verification Commands
```bash
peripatos generate --help  # Expected: --llm-provider {anthropic,gemini,openai,openrouter}
python -c "from peripatos.models import LLMProvider; print(sorted(p.value for p in LLMProvider))"  # Expected: ['anthropic', 'gemini', 'openai', 'openrouter']
python -c "from peripatos.config import VALID_LLM_PROVIDERS; print(sorted(VALID_LLM_PROVIDERS))"  # Expected: ['anthropic', 'gemini', 'openai', 'openrouter']
pytest  # Expected: all tests pass
grep -c "API_KEY" .env.example  # Expected: 4
grep "ENVIRONMENT" .env.example  # Expected: detailed explanation present
grep "LOG_LEVEL" .env.example  # Expected: detailed explanation present
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass (existing 164 + new)
- [ ] `.env.example` has 4 API keys + improved ENVIRONMENT/LOG_LEVEL docs
- [ ] README reflects all 4 providers
