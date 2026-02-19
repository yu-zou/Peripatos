# README TTS Documentation

## TL;DR

> **Quick Summary**: Add two new documentation sections to README.md covering TTS engine setup and recommended voice/model settings for edge-tts and OpenAI TTS.
> 
> **Deliverables**:
> - "TTS Engine Setup" section in README.md (engine selection, API keys, voice configuration, fallback behavior)
> - "Recommended Settings" section in README.md (voice recommendations, model differences, engine-specific voice names)
> 
> **Estimated Effort**: Quick
> **Parallel Execution**: NO — single task, single file
> **Critical Path**: Task 1 → Final Verification

---

## Context

### Original Request
User requested additions to README.md:
1. How to set up and use edge-tts and OpenAI TTS
2. Recommended settings (voice selection, model selection) for best performance, referencing OpenAI's official TTS documentation

### Interview Summary
**Key Discussions**:
- Documentation-only change to a single file (README.md)
- Two new sections needed covering setup and recommendations
- User specifically referenced https://developers.openai.com/api/docs/guides/text-to-speech/ as a source

**Research Findings**:
- **Codebase analysis** (explore agent): TTS engine selected via `--tts-engine` CLI flag or config. Default engine is `openai`. Voices configured via `~/.peripatos/config.yaml` under `tts.voice_host` and `tts.voice_expert`. Auto-fallback to edge-tts if OpenAI API key missing.
- **OpenAI TTS** (librarian agent): 13 voices now available (alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse, marin, cedar). OpenAI recommends `marin` and `cedar` for best quality. Models: tts-1 (standard), tts-1-hd (HD). Max 4096 chars per request.
- **edge-tts** (librarian agent): Free, no API key. 300+ voices across 70+ languages. 17 en-US neural voices. Recommended pairs: AriaNeural+GuyNeural (professional), JennyNeural+AndrewMultilingualNeural (warm). Output: 24kHz 48kbps mono MP3.

### Metis Review
**Identified Gaps** (addressed):
- **Voice validation misconception corrected**: The code does NOT validate/restrict OpenAI voices to 6 — line 75 of openai_tts.py is a docstring, not validation. Any voice string is passed through to the API. Documentation must not claim voice restriction.
- **Section placement clarified**: New sections go between `## Bilingual Mode` (line 59) and `## CLI Reference` (line 62), not between Configuration and Persona Modes.
- **Chinese voice defaults noted**: edge-tts has zh-CN voice defaults relevant to bilingual mode users — include them.
- **Config YAML snippet needed**: Show the exact `config.yaml` structure for voice overrides.
- **Engine-specific voice names caveat**: Must document that OpenAI voices ≠ edge-tts voice IDs.

---

## Work Objectives

### Core Objective
Add comprehensive TTS documentation to README.md so users know how to set up, configure, and optimize both TTS engines.

### Concrete Deliverables
- Two new `##`-level sections inserted into README.md between `## Bilingual Mode` and `## CLI Reference`

### Definition of Done
- [ ] `grep -c "## TTS Engine Setup" README.md` returns 1
- [ ] `grep -c "## Recommended Settings" README.md` returns 1
- [ ] `git diff README.md | grep '^-[^-]' | wc -l` returns 0 (no existing lines removed)
- [ ] Section order verified: Bilingual Mode → TTS Engine Setup → Recommended Settings → CLI Reference
- [ ] `pytest --tb=short -q` passes (no accidental file corruption)

### Must Have
- Explanation of `--tts-engine` CLI flag for engine selection
- OpenAI TTS requirements (API key, which env var)
- edge-tts being free / no API key required
- Voice configuration via `~/.peripatos/config.yaml` with example YAML snippet
- Engine-specific voice name caveat (OpenAI short names vs edge-tts Neural voice IDs)
- Auto-fallback behavior (OpenAI configured → key missing → edge-tts with warning)
- OpenAI voice list with defaults highlighted (alloy host, onyx expert)
- edge-tts voice list with defaults highlighted (AriaNeural host, GuyNeural expert)
- Chinese voice defaults for bilingual mode (XiaoxiaoNeural, YunxiNeural)
- tts-1 vs tts-1-hd model comparison (tts-1 is default, not user-configurable)
- Alternative edge-tts voice pair recommendations

### Must NOT Have (Guardrails)
- **Do NOT claim voices are restricted/validated to any set** — the code has no voice validation, any string is passed to the API
- **Do NOT document `gpt-4o-mini-tts` model** — the code only references tts-1/tts-1-hd and may not support newer API shapes
- **Do NOT document the speed parameter** — not exposed by Peripatos
- **Do NOT modify any existing README sections** — additions only between Bilingual Mode and CLI Reference
- **Do NOT add edge-tts installation instructions** — it's a pip dependency, installed automatically
- **Do NOT document implementation details** — no chunking logic, retry mechanisms, rate limits, or chunk sizes
- **Do NOT create any files other than editing README.md**
- **Do NOT over-document** — keep total addition to ~80-120 lines, matching README's concise style

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **Automated tests**: None needed (documentation-only change)
- **Framework**: pytest (for regression check only)

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **Documentation**: Use Bash — grep for section headers, verify ordering, check Markdown validity, run pytest for regression

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — single task):
└── Task 1: Add TTS documentation sections to README.md [quick]

Wave FINAL (After Task 1 — verification):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → F1-F4
Max Concurrent: 1 (Wave 1), 4 (Wave FINAL)
```

### Dependency Matrix

| Task | Depends On | Blocks |
|------|-----------|--------|
| 1    | —         | F1-F4  |
| F1   | 1         | —      |
| F2   | 1         | —      |
| F3   | 1         | —      |
| F4   | 1         | —      |

### Agent Dispatch Summary

- **Wave 1**: 1 task — T1 → `quick`
- **Wave FINAL**: 4 tasks — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

- [x] 1. Add TTS documentation sections to README.md

  **What to do**:
  - Insert two new `##`-level sections into `README.md` between the `## Bilingual Mode` section (currently ends at line 59) and `## CLI Reference` section (currently starts at line 62)
  - **Section 1: "## TTS Engine Setup"** — Cover these topics in this order:
    1. Engine selection: Use `--tts-engine {edge-tts,openai}` CLI flag. Default engine is `openai`.
    2. **OpenAI TTS setup**: Requires `OPENAI_API_KEY` env var. Uses the `tts-1` model by default (model selection is not currently user-configurable). Mention `tts-1-hd` exists for higher quality but is not exposed via config/CLI.
    3. **edge-tts setup**: Free, no API key required. Uses Microsoft's Azure Neural TTS service. If OpenAI is configured but the API key is missing, Peripatos automatically falls back to edge-tts with a warning.
    4. **Voice configuration**: Voices are configured in `~/.peripatos/config.yaml` (not via CLI flags). Show this exact YAML example:
       ```yaml
       tts:
         engine: openai          # or "edge-tts"
         voice_host: alloy       # voice for the host speaker
         voice_expert: onyx      # voice for the expert/guest speaker
       ```
    5. **Important**: Voice names are engine-specific. OpenAI uses short names (e.g., `alloy`, `nova`), while edge-tts uses Microsoft Neural voice IDs (e.g., `en-US-AriaNeural`). When switching engines, update your voice configuration accordingly.
  - **Section 2: "## Recommended Settings"** — Cover these topics:
    1. **OpenAI TTS voices**: Defaults are `alloy` (host) and `onyx` (expert). Available voices include: `alloy`, `ash`, `ballad`, `coral`, `echo`, `fable`, `nova`, `onyx`, `sage`, `shimmer`, `verse`, `marin`, `cedar`. OpenAI recommends `marin` and `cedar` for best quality. Present as a table with voice names. Link to OpenAI's voice preview page: https://platform.openai.com/docs/guides/text-to-speech#voice-options
    2. **OpenAI TTS models**: `tts-1` (default) — optimized for speed/low latency. `tts-1-hd` — higher audio quality. Note: Peripatos currently uses `tts-1` and model selection is not user-configurable.
    3. **edge-tts voices**: Defaults are `en-US-AriaNeural` (host) and `en-US-GuyNeural` (expert). Present recommended English voice pairs in a table format:
       - AriaNeural + GuyNeural (Professional, confident — **default**)
       - JennyNeural + AndrewMultilingualNeural (Warm, conversational)
       - EmmaMultilingualNeural + ChristopherNeural (Clear, authoritative)
    4. **Chinese voices for bilingual mode**: When using `--language zh-en`, edge-tts automatically uses Chinese neural voices: `zh-CN-XiaoxiaoNeural` (host) and `zh-CN-YunxiNeural` (expert).
    5. To browse all 300+ edge-tts voices: `edge-tts --list-voices`
    6. For edge-tts voice previews: link to https://speech.microsoft.com/portal/voicegallery

  **Must NOT do**:
  - Do NOT claim voices are restricted/validated to any set — the code passes any voice string to the API
  - Do NOT document `gpt-4o-mini-tts` model — not referenced in Peripatos code
  - Do NOT document the speed parameter — not exposed by Peripatos
  - Do NOT modify any existing README sections — additions only
  - Do NOT add `pip install edge-tts` instructions — it's auto-installed as a dependency
  - Do NOT document implementation details (chunking, retry, rate limits, chunk sizes)
  - Do NOT add a troubleshooting section
  - Keep total addition to ~80-120 lines of markdown, matching the concise style of existing README sections

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file documentation edit with clear content specification. No complex logic or multi-file coordination.
  - **Skills**: []
    - No specialized skills needed — this is a straightforward markdown edit.
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed
    - `frontend-ui-ux`: Not a UI task
    - `git-master`: Commit handled by orchestrator, not a complex git operation

  **Parallelization**:
  - **Can Run In Parallel**: NO (only task)
  - **Parallel Group**: Wave 1 (solo)
  - **Blocks**: F1, F2, F3, F4
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL - Be Exhaustive):

  **Pattern References** (existing code to follow):
  - `README.md:48-53` — Persona Modes section: demonstrates the README's documentation style (brief intro, bullet list with bold labels, concise descriptions). Mirror this format for voice recommendations.
  - `README.md:56-59` — Bilingual Mode section: shows how to document a feature with usage context and an example. Follow this pattern for TTS setup.
  - `README.md:34-44` — Configuration section: shows how API keys and config are currently documented. New sections should complement, not duplicate this.

  **API/Type References** (contracts to implement against):
  - `peripatos/config.py:22-26` — Default TTS configuration (`engine: "openai"`, `voice_host: "alloy"`, `voice_expert: "onyx"`). The YAML example in documentation MUST match these defaults exactly.
  - `peripatos/cli.py:87-92` — CLI flag `--tts-engine` with choices `{edge-tts, openai}`. Document this flag accurately.
  - `peripatos/voice/openai_tts.py:41-47` — OpenAI TTS constructor: `model="tts-1"` default, `max_chunk_size=4096`. Confirms tts-1 is the default model.
  - `peripatos/voice/openai_tts.py:70-75` — `synthesize()` method: voice parameter is a plain string, no validation. Docstring lists 6 voices as suggestions only.
  - `peripatos/voice/edge_tts_engine.py:16-26` — edge-tts voice mapping: English defaults (AriaNeural/GuyNeural) and Chinese defaults (XiaoxiaoNeural/YunxiNeural).
  - `peripatos/voice/renderer.py:47-73` — Engine selection and fallback logic: if OpenAI configured but key missing, falls back to edge-tts with warning.
  - `peripatos/voice/renderer.py:121-133` — Voice selection: HOST speaker → `config.tts_voice_host`, EXPERT speaker → `config.tts_voice_expert`.

  **External References** (libraries and frameworks):
  - OpenAI TTS voice previews: https://platform.openai.com/docs/guides/text-to-speech#voice-options — Link to this for users to audition voices
  - OpenAI TTS API docs: https://platform.openai.com/docs/guides/text-to-speech — General reference
  - edge-tts GitHub: https://github.com/rany2/edge-tts — For `edge-tts --list-voices` command reference
  - Microsoft Voice Gallery: https://speech.microsoft.com/portal/voicegallery — For edge-tts voice previews

  **WHY Each Reference Matters**:
  - `config.py` defaults → YAML example must show these exact values as defaults
  - `cli.py` flags → Document the exact CLI flag name and choices
  - `openai_tts.py` constructor → Confirms model default and that it's not configurable
  - `openai_tts.py` synthesize → Confirms no voice validation exists (don't claim restriction)
  - `edge_tts_engine.py` voice map → Source of truth for default edge-tts voices per language
  - `renderer.py` fallback → Source for fallback behavior documentation
  - `renderer.py` voice selection → Explains how config maps to engine voice parameters

  **Acceptance Criteria**:

  > **AGENT-EXECUTABLE VERIFICATION ONLY** — No human action permitted.

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: New sections exist and are correctly placed
    Tool: Bash
    Preconditions: README.md has been edited
    Steps:
      1. Run: grep -n "## TTS Engine Setup" README.md
      2. Assert: exactly 1 match found
      3. Run: grep -n "## Recommended Settings" README.md
      4. Assert: exactly 1 match found
      5. Run: python3 -c "c=open('README.md').read(); secs=['## Bilingual Mode','## TTS Engine Setup','## Recommended Settings','## CLI Reference']; pos=[c.index(s) for s in secs]; assert pos==sorted(pos), f'Bad order: {pos}'; print('Section order: OK')"
      6. Assert: prints "Section order: OK"
    Expected Result: Both sections present, in correct order between Bilingual Mode and CLI Reference
    Failure Indicators: grep returns 0 matches, or python assertion fails with "Bad order"
    Evidence: .sisyphus/evidence/task-1-section-placement.txt

  Scenario: No existing content was removed or modified
    Tool: Bash
    Preconditions: Changes committed or staged
    Steps:
      1. Run: git diff README.md | grep '^-[^-]' | wc -l
      2. Assert: output is "0" (zero lines removed)
      3. Run: git diff README.md | grep '^+[^+]' | wc -l
      4. Assert: output is > 0 (lines were added)
    Expected Result: Only additions, zero deletions
    Failure Indicators: Any non-zero count of removed lines
    Evidence: .sisyphus/evidence/task-1-no-deletions.txt

  Scenario: Markdown is well-formed
    Tool: Bash
    Preconditions: README.md has been edited
    Steps:
      1. Run: python3 -c "c=open('README.md').read(); assert c.count('\`\`\`') % 2 == 0; print('Code blocks balanced: OK')"
      2. Assert: prints "Code blocks balanced: OK"
      3. Run: python3 -c "import re; c=open('README.md').read(); headers=[m.group() for m in re.finditer(r'^#{1,6} .+', c, re.MULTILINE)]; [print(h) for h in headers]"
      4. Assert: all new headers use `##` level (consistent with existing)
    Expected Result: All code blocks properly closed, consistent heading levels
    Failure Indicators: Assertion error about odd count, or ### headers found for new sections
    Evidence: .sisyphus/evidence/task-1-markdown-valid.txt

  Scenario: Technical accuracy — key terms present
    Tool: Bash
    Preconditions: README.md has been edited
    Steps:
      1. Run: grep -q "alloy" README.md && echo "alloy OK" || echo "alloy MISSING"
      2. Run: grep -q "onyx" README.md && echo "onyx OK" || echo "onyx MISSING"
      3. Run: grep -q "AriaNeural" README.md && echo "AriaNeural OK" || echo "AriaNeural MISSING"
      4. Run: grep -q "GuyNeural" README.md && echo "GuyNeural OK" || echo "GuyNeural MISSING"
      5. Run: grep -q "tts-1" README.md && echo "tts-1 OK" || echo "tts-1 MISSING"
      6. Run: grep -q "config.yaml" README.md && echo "config.yaml OK" || echo "config.yaml MISSING"
      7. Run: grep -q "XiaoxiaoNeural" README.md && echo "Chinese voice OK" || echo "Chinese voice MISSING"
      8. Run: grep -q "voice_host" README.md && echo "voice_host OK" || echo "voice_host MISSING"
      9. Assert: all checks print "OK"
    Expected Result: All key technical terms are present in the README
    Failure Indicators: Any check prints "MISSING"
    Evidence: .sisyphus/evidence/task-1-technical-accuracy.txt

  Scenario: No forbidden content
    Tool: Bash
    Preconditions: README.md has been edited
    Steps:
      1. Run: grep -i "gpt-4o-mini-tts" README.md | wc -l
      2. Assert: output is "0" (model not mentioned)
      3. Run: grep -i "pip install edge-tts" README.md | wc -l
      4. Assert: output is "0" (no installation instruction)
      5. Run: grep -i "only supports" README.md | grep -i "voice" | wc -l
      6. Assert: output is "0" (no false restriction claim)
    Expected Result: No forbidden content present
    Failure Indicators: Any non-zero count
    Evidence: .sisyphus/evidence/task-1-no-forbidden.txt

  Scenario: Tests still pass (regression check)
    Tool: Bash
    Preconditions: README.md has been edited
    Steps:
      1. Run: pytest --tb=short -q
      2. Assert: exit code 0, all tests pass
    Expected Result: All existing tests pass, no regressions
    Failure Indicators: Non-zero exit code, any test failure
    Evidence: .sisyphus/evidence/task-1-regression.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-section-placement.txt — grep output showing section locations
  - [ ] task-1-no-deletions.txt — git diff verification output
  - [ ] task-1-markdown-valid.txt — code block and heading validation output
  - [ ] task-1-technical-accuracy.txt — key term presence checks
  - [ ] task-1-no-forbidden.txt — forbidden content absence checks
  - [ ] task-1-regression.txt — pytest output

  **Commit**: YES
  - Message: `docs(readme): add TTS engine setup and recommended settings sections`
  - Files: `README.md`
  - Pre-commit: `pytest --tb=short -q`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [x] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify the README contains it (grep for key terms, read sections). For each "Must NOT Have": search README for forbidden patterns — reject with line number if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [x] F2. **Code Quality Review** — `unspecified-high`
  Run `pytest --tb=short -q` to ensure no regressions. Review README.md diff for: broken Markdown syntax, unclosed code blocks, inconsistent heading levels, broken links. Check for AI slop: excessive adjectives, filler text, redundant sections, unnecessary disclaimers.
  Output: `Tests [PASS/FAIL] | Markdown [VALID/INVALID] | Style [N issues] | VERDICT`

- [x] F3. **Real Manual QA** — `unspecified-high`
  Read the full README.md top-to-bottom. Verify the new sections flow naturally from Bilingual Mode into CLI Reference. Check every config example is syntactically valid YAML. Verify every voice name mentioned actually exists (cross-reference with codebase files). Verify every CLI flag mentioned matches `cli.py`. Save evidence screenshot/output.
  Output: `Flow [OK/ISSUE] | Config syntax [OK/ISSUE] | Voice accuracy [N/N] | CLI accuracy [N/N] | VERDICT`

- [x] F4. **Scope Fidelity Check** — `deep`
  `git diff README.md` — verify ONLY additions between the Bilingual Mode and CLI Reference sections. Zero lines removed. Zero changes to any other section. No new files created. No scope creep (no troubleshooting section, no installation instructions for edge-tts, no implementation details). Flag any content not in the plan's "Must Have" list.
  Output: `Lines removed [0/N] | Other sections [CLEAN/N changes] | New files [CLEAN/N] | Scope [CLEAN/N creep] | VERDICT`

---

## Commit Strategy

- **Task 1**: `docs(readme): add TTS engine setup and recommended settings sections` — `README.md`
  - Pre-commit: `pytest --tb=short -q`

---

## Success Criteria

### Verification Commands
```bash
# Section headers present
grep -c "## TTS Engine Setup" README.md         # Expected: 1
grep -c "## Recommended Settings" README.md      # Expected: 1

# No existing content removed
git diff README.md | grep '^-[^-]' | wc -l      # Expected: 0

# Section order correct
python3 -c "
c=open('README.md').read()
secs=['## Bilingual Mode','## TTS Engine Setup','## Recommended Settings','## CLI Reference']
pos=[c.index(s) for s in secs]
assert pos==sorted(pos), f'Bad order: {pos}'
print('Section order: OK')
"

# Code blocks balanced
python3 -c "
c=open('README.md').read()
assert c.count('\`\`\`') % 2 == 0
print('Code blocks: OK')
"

# Key technical terms present
grep -q "alloy" README.md && grep -q "onyx" README.md && echo "OpenAI voices OK"
grep -q "AriaNeural" README.md && grep -q "GuyNeural" README.md && echo "edge-tts voices OK"
grep -q "tts-1" README.md && echo "Model reference OK"
grep -q "config.yaml" README.md && echo "Config reference OK"

# Tests still pass
pytest --tb=short -q                             # Expected: all pass
```

### Final Checklist
- [ ] All "Must Have" present in README.md
- [ ] All "Must NOT Have" absent from README.md
- [ ] All tests pass
- [ ] README Markdown is well-formed
- [ ] New sections match existing README tone and style
