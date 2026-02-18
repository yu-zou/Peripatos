# Granite Docling VLM — Integration & Evaluation Plan

## TL;DR

> **Quick Summary**: Add optional `--vlm` flag to Peripatos CLI that switches from base Docling to Granite Docling VLM pipeline for enhanced PDF parsing, then evaluate quality improvement on 5 ArXiv papers using IBM's `docling-eval` framework. Stage 1 only (markdown quality comparison). This plan executes AFTER the MVP plan is complete.
> 
> **Deliverables**:
> - `--vlm` CLI flag on `peripatos generate` command
> - Optional dependency group: `pip install peripatos[vlm]`
> - VLM-aware PDF parser (extends MVP Task 5's `PDFParser`)
> - Evaluation framework using `docling-eval` + custom comparison wrapper
> - 5-paper ArXiv evaluation corpus with automated benchmark
> - Structured Markdown evaluation report with per-paper metrics and recommendation
> - pytest coverage for VLM integration and evaluation framework
> 
> **Estimated Effort**: Medium
> **Parallel Execution**: YES — 3 waves
> **Critical Path**: Task 1 → Task 3 → Task 6 → Task 9 → Task 10 → Task 11 → FINAL

---

## Context

### Original Request
User wants to integrate IBM's Granite Docling VLM (`ibm-granite/granite-docling-258M`) as an optional enhancement for the Peripatos PDF parsing pipeline. The model is intended for a future paid/premium tier. Before committing, they need an evaluation comparing base Docling vs Granite Docling on academic papers to determine if the quality improvement justifies the GPU cost.

### Interview Summary
**Key Discussions**:
- **Relationship to MVP**: Separate plan, executed AFTER MVP is complete. MVP ships with base Docling first.
- **Architecture**: Flag on existing parser (`--vlm`), same interface, different pipeline underneath. Docling natively supports this via `VlmPipeline`.
- **Evaluation**: Staged — Stage 1 = markdown quality comparison (this plan). Stage 2 = full pipeline comparison (future plan, if Stage 1 positive).
- **Test Corpus**: 5 ArXiv papers covering: math-heavy, table-heavy, code-heavy, multi-column, figures.
- **Runtime Paths**: GPU (CUDA) + CPU fallback + Apple Silicon (MLX) — all three tested.
- **Testing**: pytest for both evaluation framework and VLM integration code.
- **Output**: Structured Markdown report file.

**Research Findings**:
- **Model**: `ibm-granite/granite-docling-258M` (258M params, Apache-2.0, HuggingFace)
- **MLX variant**: `ibm-granite/granite-docling-258M-mlx`
- **Integration**: `VlmPipeline` + `VlmPipelineOptions` + `vlm_model_specs.GRANITEDOCLING_MLX` / `vlm_model_specs.GRANITEDOCLING_TRANSFORMERS`
- **Benchmarks** (vs smolDocling baseline): Tables TEDS 0.97 vs 0.82 (+18%), Equations F1 0.968 vs 0.947, Code F1 0.988 vs 0.915, Layout mAP 0.27 vs 0.23
- **Hardware**: ~4GB VRAM single-page, MLX on Apple Silicon, CPU via ONNX/GGUF (very slow ~100-1175s/page)
- **`docling-eval`**: IBM's official evaluation framework (MIT, v0.10.0) provides TEDS, layout mAP/F1, OCR metrics — eliminates need for custom metrics
- **Known gotchas**: T4 needs float32, vLLM needs revision="untied", multilingual is experimental, occasional token loops

### Metis Review
**Identified Gaps** (addressed):
- **`docling-eval` exists**: Cuts custom evaluation work ~60%. Plan uses it instead of building custom metrics.
- **CPU inference infeasible for full corpus**: ~100-1175s/page. CPU limited to 1-page smoke test.
- **Granite Docling MLX benchmark not public**: Plan includes benchmarking step before full corpus run.
- **`docling-eval` may only work with ground truth**: Assumption A6 must be validated early — if true, fall back to custom diff approach.
- **MVP parser needs converter injection**: Task 5's `PDFParser` must accept an optional converter parameter. Plan includes validation + refactoring step.
- **Optional deps not yet in pyproject.toml**: Plan adds `[vlm]` and `[eval]` extras groups.
- **Model download latency**: First `--vlm` run triggers ~500MB download. Plan includes progress indication.
- **Token loops possible**: Plan includes 60s/page timeout + 1 retry logic.

---

## Work Objectives

### Core Objective
Integrate Granite Docling VLM as an optional `--vlm` flag on the Peripatos CLI parser and evaluate whether it meaningfully improves markdown extraction quality on academic papers compared to base Docling.

### Concrete Deliverables
- `peripatos/eye/parser.py` — Extended `PDFParser` with VLM support (converter injection)
- `peripatos/eye/vlm.py` — VLM converter factory (MLX/CUDA/CPU selection, timeout/retry)
- `peripatos/eval/` — Evaluation framework module
- `peripatos/eval/compare.py` — Comparison wrapper (runs both pipelines, collects metrics)
- `peripatos/eval/corpus.py` — Corpus management (5 ArXiv papers, download/cache)
- `peripatos/eval/report.py` — Report generator (structured Markdown)
- `peripatos/cli.py` — Updated with `--vlm` flag
- `pyproject.toml` — Updated with `[vlm]` and `[eval]` optional dependency groups
- `evaluation_report.md` — Generated evaluation report (output artifact)
- `tests/test_vlm.py` — VLM integration tests
- `tests/test_eval.py` — Evaluation framework tests

### Definition of Done
- [ ] `peripatos generate --vlm <pdf>` produces an MP3 file
- [ ] `peripatos generate <pdf>` (without `--vlm`) produces identical output to before this plan — zero regressions
- [ ] `pip install peripatos[vlm]` installs VLM dependencies; base `pip install peripatos` does not
- [ ] Evaluation report exists with per-paper metrics for all 5 papers
- [ ] All pytest tests pass (including pre-existing MVP tests)
- [ ] MLX inference completes in <30s/page on Apple Silicon
- [ ] CPU smoke test completes (1 page) without crash

### Must Have
- `--vlm` CLI flag on `peripatos generate`
- Optional dependency group `[vlm]`
- VLM converter factory with MLX/CUDA/CPU backend auto-selection
- 60s/page timeout + 1 retry for VLM inference
- Graceful error when VLM deps not installed (`pip install peripatos[vlm]` message)
- Evaluation on 5 ArXiv papers using `docling-eval` metrics (or custom diff if A6 fails)
- Structured Markdown evaluation report with per-paper results + recommendation
- pytest tests for VLM integration and evaluation framework
- No changes to base pipeline behavior

### Must NOT Have (Guardrails)
- NO custom TEDS or metrics implementations — use `docling-eval` / `docling-metrics`
- NO Stage 2 evaluation (dialogue/audio quality comparison)
- NO multilingual evaluation — English papers only
- NO vLLM, ONNX, or GGUF runtime support
- NO full corpus evaluation on CPU — 1-page smoke test only
- NO interactive dashboards, Jupyter notebooks, or HTML reports
- NO modification to existing base pipeline code paths (additive only)
- NO model fine-tuning or custom training
- NO CI/CD pipeline for evaluation — manual run only
- NO over-abstraction — no factory patterns beyond what's needed for converter selection

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (from MVP — pytest)
- **Automated tests**: YES (TDD)
- **Framework**: pytest + pytest-asyncio (from MVP)
- **TDD**: Each task follows RED (failing test) → GREEN (minimal impl) → REFACTOR

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

| Deliverable Type | Verification Tool | Method |
|------------------|-------------------|--------|
| VLM integration | Bash (python) | Import, construct converter, convert single page, assert markdown output |
| CLI flag | Bash (peripatos CLI) | Run CLI with --vlm flag, verify MP3 output |
| Evaluation framework | Bash (python -m) | Run evaluation script, verify report file generated |
| Error handling | Bash (python) | Trigger error conditions, verify graceful messages |

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — validation + foundation):
├── Task 1: Validate MVP coupling assumptions (parser interface, CLI structure) [quick]
├── Task 2: Add optional dependency groups to pyproject.toml [quick]
├── Task 3: VLM converter factory (peripatos/eye/vlm.py) [deep]
└── Task 4: Evaluation corpus setup (5 ArXiv papers, download/cache) [quick]

Wave 2 (After Wave 1 — evaluation framework + parser integration):
├── Task 5: Evaluation framework (compare.py + report.py using docling-eval) [deep]
├── Task 6: Extend PDFParser with VLM support (converter injection) [unspecified-high]
├── Task 7: Single-page benchmark (timing MLX/CUDA/CPU before full run) [quick]
└── Task 8: CPU smoke test (1-page VLM on CPU) [quick]

Wave 3 (After Wave 2 — integration + reporting):
├── Task 9: CLI --vlm flag integration [quick]
├── Task 10: Run full 5-paper evaluation + generate report [unspecified-high]
└── Task 11: Integration tests + documentation [unspecified-high]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
└── Task F4: Scope fidelity check (deep)

Critical Path: Task 1 → Task 3 → Task 6 → Task 9 → Task 10 → Task 11 → FINAL
Parallel Speedup: ~55% faster than sequential
Max Concurrent: 4 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|------------|--------|------|
| 1 | MVP complete | 3, 6, 9 | 1 |
| 2 | MVP T1 complete | 6, 9 | 1 |
| 3 | 1 | 6, 7, 8 | 1 |
| 4 | — | 5, 10 | 1 |
| 5 | 4 | 10 | 2 |
| 6 | 1, 2, 3 | 9, 10 | 2 |
| 7 | 3 | 10 | 2 |
| 8 | 3 | 11 | 2 |
| 9 | 6 | 10, 11 | 3 |
| 10 | 5, 6, 7, 9 | 11 | 3 |
| 11 | 8, 9, 10 | FINAL | 3 |
| F1-F4 | ALL | — | FINAL |

### Agent Dispatch Summary

| Wave | # Parallel | Tasks → Agent Category |
|------|------------|----------------------|
| 1 | **4** | T1 → `quick`, T2 → `quick`, T3 → `deep`, T4 → `quick` |
| 2 | **4** | T5 → `deep`, T6 → `unspecified-high`, T7 → `quick`, T8 → `quick` |
| 3 | **3** | T9 → `quick`, T10 → `unspecified-high`, T11 → `unspecified-high` |
| FINAL | **4** | F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep` |

---

## TODOs

- [ ] 1. Validate MVP Coupling Assumptions

  **What to do**:
  - Read MVP's `peripatos/eye/parser.py` (Task 5 output) — check if `PDFParser` accepts a `converter` parameter or can be extended
  - Read MVP's `peripatos/cli.py` (Task 14 output) — check if argparse structure allows adding `--vlm` flag
  - Read MVP's `peripatos/models.py` (Task 3 output) — check if `PaperMetadata` has a `parser_type` field or can accept one
  - Read `pyproject.toml` (Task 1 output) — check if `[project.optional-dependencies]` section exists
  - If `PDFParser` does NOT accept a converter parameter: plan a minimal refactor (add `converter: DocumentConverter | None = None` to `__init__`)
  - Document findings: what works, what needs modification, exact line numbers
  - Write a validation report to stdout summarizing coupling status

  **Must NOT do**:
  - Do NOT modify any MVP files in this task — only read and report
  - Do NOT refactor the parser yet — that's Task 6

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Read-only validation task, no implementation
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `git-master`: No git operations needed
    - `playwright`: No browser interaction

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4)
  - **Blocks**: Tasks 3, 6, 9
  - **Blocked By**: MVP plan must be complete (all 17 tasks)

  **References** (CRITICAL):

  **Pattern References**:
  - `peripatos/eye/parser.py` — MVP Task 5 output. Check `PDFParser.__init__()` for converter parameter. The VLM plan needs to inject a custom converter here.
  - `peripatos/cli.py` — MVP Task 14 output. Check argparse subcommand structure for `generate` command. Need to add `--vlm` flag.

  **API/Type References**:
  - `peripatos/models.py` — MVP Task 3 output. Check `PaperMetadata` dataclass. May need optional `parser_type: str` field.
  - `pyproject.toml` — Check for `[project.optional-dependencies]` section structure.

  **External References**:
  - None needed — this is internal validation only

  **WHY Each Reference Matters**:
  - `parser.py`: The VLM integration's viability hinges on whether the parser can accept an external converter. If hardcoded, Task 6 must refactor.
  - `cli.py`: Need to understand existing argparse structure to add `--vlm` without breaking existing flags.
  - `models.py`: Tracking which parser produced the output is useful for the evaluation report.
  - `pyproject.toml`: Optional deps must be added here — need to know existing structure.

  **Acceptance Criteria**:

  - [ ] Validation report printed to stdout with findings for all 4 files
  - [ ] Each finding includes: file path, line number, current interface, compatibility assessment (YES/NO/REFACTOR_NEEDED)
  - [ ] If refactor needed: exact description of what changes are required (parameter name, type, default value)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Validate parser interface compatibility
    Tool: Bash (python)
    Preconditions: MVP plan fully executed, peripatos package installed
    Steps:
      1. Run: python -c "import inspect; from peripatos.eye.parser import PDFParser; sig = inspect.signature(PDFParser.__init__); print(sig)"
      2. Check if 'converter' or 'use_vlm' appears in the signature
      3. Run: python -c "from peripatos.eye.parser import PDFParser; p = PDFParser(); print(type(p))"
    Expected Result: Signature printed. Either (a) converter param exists → COMPATIBLE, or (b) no converter param → REFACTOR_NEEDED
    Failure Indicators: ImportError (MVP not complete), or parser has no extensibility point
    Evidence: .sisyphus/evidence/task-1-parser-validation.txt

  Scenario: Validate CLI structure compatibility
    Tool: Bash (python)
    Preconditions: MVP plan fully executed
    Steps:
      1. Run: peripatos generate --help
      2. Check output for existing flag structure
      3. Verify argparse uses subcommands (not flat)
    Expected Result: Help text shows `generate` subcommand with existing flags. Adding `--vlm` is feasible.
    Failure Indicators: CLI doesn't use subcommands, or generate command doesn't exist
    Evidence: .sisyphus/evidence/task-1-cli-validation.txt
  ```

  **Evidence to Capture:**
  - [ ] task-1-parser-validation.txt — Parser interface inspection results
  - [ ] task-1-cli-validation.txt — CLI help output and structure analysis

  **Commit**: NO (read-only task, no files changed)

- [ ] 2. Add Optional Dependency Groups to pyproject.toml

  **What to do**:
  - Write RED test first: test that `peripatos[vlm]` extras group exists in pyproject.toml and contains expected packages (use `tomllib` from Python 3.11+ stdlib)
  - Add `[project.optional-dependencies]` section to `pyproject.toml`:
    ```toml
    [project.optional-dependencies]
    vlm = [
        "torch>=2.0",
        "transformers>=4.40",
        "accelerate",
        "mlx-vlm>=0.4; sys_platform == 'darwin' and platform_machine == 'arm64'",
    ]
    eval = [
        "docling-eval>=0.10",
    ]
    ```
  - MLX dependency is included in `vlm` with a platform marker — Apple Silicon users get it automatically via `pip install peripatos[vlm]`
  - No separate `vlm-mlx` extra needed (simplifies user-facing messaging)
  - Verify: `pip install -e .[vlm,eval]` succeeds
  - Verify: `pip install -e .` (base) does NOT install torch/transformers/docling-eval

  **Must NOT do**:
  - Do NOT add `torch` to base dependencies — it must remain optional
  - Do NOT pin exact versions — use minimum version constraints
  - Do NOT add vLLM, ONNX, or GGUF dependencies

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single-file modification with clear spec
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `git-master`: Simple change, no complex git needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4)
  - **Blocks**: Tasks 6, 9
  - **Blocked By**: MVP Task 1 (pyproject.toml must exist)

  **References** (CRITICAL):

  **Pattern References**:
  - `pyproject.toml` — MVP Task 1 output. Check existing structure and dependencies section to know where to add optional-dependencies.

  **API/Type References**:
  - Python packaging spec: `[project.optional-dependencies]` format in pyproject.toml

  **External References**:
  - `docling-eval` PyPI: `pip install docling-eval` — verify package name and minimum version
  - HuggingFace model card `ibm-granite/granite-docling-258M` — lists required dependencies (torch, transformers)
  - Docling VLM docs: `docling-project.github.io/docling/usage/vision_models/` — lists MLX dependencies

  **WHY Each Reference Matters**:
  - `pyproject.toml`: Must match existing structure; adding optional deps in wrong format breaks packaging
  - Model card: Authoritative source for which packages Granite Docling requires
  - Docling VLM docs: Confirms MLX-specific dependencies

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: `tests/test_packaging.py`
  - [ ] Test: parse pyproject.toml, assert `vlm` and `eval` groups exist with expected packages (including `mlx-vlm` with platform marker in `vlm` group)
  - [ ] `pytest tests/test_packaging.py` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Optional VLM deps install correctly
    Tool: Bash
    Preconditions: Clean virtualenv
    Steps:
      1. Run: pip install -e ".[vlm]"
      2. Run: python -c "import torch; import transformers; print('VLM deps OK')"
      3. Run: pip install -e ".[eval]"
      4. Run: python -c "import docling_eval; print('Eval deps OK')"
    Expected Result: Both print OK messages without ImportError
    Failure Indicators: ImportError for any package, pip install failure
    Evidence: .sisyphus/evidence/task-2-optional-deps.txt

  Scenario: Base install does NOT include VLM deps
    Tool: Bash
    Preconditions: Fresh virtualenv
    Steps:
      1. Run: pip install -e .
      2. Run: python -c "import torch" and expect ImportError
      3. Run: python -c "import docling_eval" and expect ImportError
    Expected Result: Both imports raise ImportError (deps not installed in base)
    Failure Indicators: torch or docling_eval imports succeed without explicit [vlm] install
    Evidence: .sisyphus/evidence/task-2-base-install-isolation.txt
  ```

  **Evidence to Capture:**
  - [ ] task-2-optional-deps.txt — VLM and eval dependency installation output
  - [ ] task-2-base-install-isolation.txt — Verification that base install doesn't include VLM deps

  **Commit**: YES
  - Message: `chore(deps): add vlm and eval optional dependency groups`
  - Files: `pyproject.toml`, `tests/test_packaging.py`
  - Pre-commit: `pytest tests/test_packaging.py`

- [ ] 3. VLM Converter Factory

  **What to do**:
  - Write RED tests first in `tests/test_vlm.py`:
    - Test `create_vlm_converter()` returns a `DocumentConverter` with `VlmPipeline`
    - Test backend auto-detection: MLX on macOS with Apple Silicon, CUDA if `torch.cuda.is_available()`, CPU fallback
    - Test timeout wrapper: mock VLM inference taking >60s, assert it raises `TimeoutError`
    - Test retry logic: mock first call failing, second succeeding, assert result returned
    - Test graceful import error: when torch/transformers not installed, `create_vlm_converter()` raises `ImportError` with helpful message mentioning `pip install peripatos[vlm]`
  - Implement `peripatos/eye/vlm.py`:
    - `create_vlm_converter(backend: str | None = None, timeout: int = 60) -> DocumentConverter`
    - Backend auto-detection logic:
      1. If `backend="mlx"` or (auto and macOS Apple Silicon): use `vlm_model_specs.GRANITEDOCLING_MLX`
      2. If `backend="cuda"` or (auto and `torch.cuda.is_available()`): use `vlm_model_specs.GRANITEDOCLING_TRANSFORMERS`
      3. If `backend="cpu"` or (auto fallback): use `vlm_model_specs.GRANITEDOCLING_TRANSFORMERS` with CPU device
    - Wrap converter with timeout: 60s per page default, configurable
    - Retry logic: 1 retry on failure (handles occasional token loops)
    - Lazy imports: `torch`, `transformers`, `mlx_vlm` imported inside function, not at module level
    - Clear error if VLM deps not installed: `ImportError("VLM support requires additional dependencies. Install with: pip install peripatos[vlm]")`
  - Create `peripatos/eye/__init__.py` update if needed to export `create_vlm_converter`

  **Must NOT do**:
  - Do NOT import torch/transformers at module top level — lazy imports only
  - Do NOT add vLLM, ONNX, or GGUF backend options
  - Do NOT modify existing `parser.py` — that's Task 6
  - Do NOT create abstract base classes or factory patterns beyond the single function

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex logic (backend detection, timeout, retry, lazy imports, error handling) requires careful implementation
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser interaction needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4)
  - **Blocks**: Tasks 6, 7, 8
  - **Blocked By**: Task 1 (soft dependency — start in parallel, but if T1 finds API incompatibilities, T3 must adjust before completion)

  **References** (CRITICAL):

  **Pattern References**:
  - `peripatos/eye/parser.py` — MVP Task 5 output. See how `DocumentConverter` is currently constructed to match patterns.

  **API/Type References**:
  - Docling VLM API (from HuggingFace model card, fetched 2026-02-19):
    ```python
    from docling.datamodel import vlm_model_specs
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import VlmPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.pipeline.vlm_pipeline import VlmPipeline

    pipeline_options = VlmPipelineOptions(vlm_options=vlm_model_specs.GRANITEDOCLING_MLX)
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(
            pipeline_cls=VlmPipeline, pipeline_options=pipeline_options
        )}
    )
    ```
  - `vlm_model_specs.GRANITEDOCLING_MLX` — Apple Silicon MLX backend
  - `vlm_model_specs.GRANITEDOCLING_TRANSFORMERS` — CUDA/CPU Transformers backend

  **External References**:
  - Docling VLM docs: `https://docling-project.github.io/docling/usage/vision_models/` — backend selection, AcceleratorOptions
  - HuggingFace model card: `https://huggingface.co/ibm-granite/granite-docling-258M` — integration examples, dtype requirements (bfloat16 for modern GPU, float32 for T4)

  **WHY Each Reference Matters**:
  - Model card + VLM docs: The ONLY authoritative source for the correct API. Using stale patterns will break.
  - `parser.py`: Must match the converter construction pattern used in base Docling to ensure output compatibility.

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: `tests/test_vlm.py`
  - [ ] Tests: backend detection, timeout, retry, import error handling
  - [ ] `pytest tests/test_vlm.py` → PASS (all tests)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: VLM converter factory creates valid converter on Apple Silicon
    Tool: Bash (python)
    Preconditions: macOS Apple Silicon, peripatos[vlm] installed (MLX deps auto-included via platform marker)
    Steps:
      1. Run: python -c "
         from peripatos.eye.vlm import create_vlm_converter
         conv = create_vlm_converter()
         print(type(conv))
         print('Backend: MLX' if 'mlx' in str(conv) else 'Backend: other')
         "
      2. Verify output shows DocumentConverter type
    Expected Result: Prints `<class 'docling.document_converter.DocumentConverter'>` and auto-selects MLX on Apple Silicon
    Failure Indicators: ImportError, wrong backend selected, or converter creation fails
    Evidence: .sisyphus/evidence/task-3-converter-factory.txt

  Scenario: Graceful error when VLM deps missing
    Tool: Bash (python)
    Preconditions: Fresh virtualenv with only base peripatos installed (no [vlm])
    Steps:
      1. Run: python -c "
         try:
             from peripatos.eye.vlm import create_vlm_converter
             create_vlm_converter()
             print('FAIL: no error raised')
         except ImportError as e:
             msg = str(e)
             assert 'pip install' in msg.lower() or 'peripatos[vlm]' in msg, f'Bad message: {msg}'
             print(f'PASS: {msg}')
         "
    Expected Result: ImportError raised with message containing 'pip install peripatos[vlm]'
    Failure Indicators: No error raised, or error message doesn't mention installation command
    Evidence: .sisyphus/evidence/task-3-import-error.txt
  ```

  **Evidence to Capture:**
  - [ ] task-3-converter-factory.txt — Converter creation output on Apple Silicon
  - [ ] task-3-import-error.txt — Import error handling verification

  **Commit**: YES
  - Message: `feat(eye): add VLM converter factory with MLX/CUDA/CPU support`
  - Files: `peripatos/eye/vlm.py`, `tests/test_vlm.py`
  - Pre-commit: `pytest tests/test_vlm.py`

- [ ] 4. Evaluation Corpus Setup

  **What to do**:
  - Write RED tests first in `tests/test_eval.py`:
    - Test `get_corpus()` returns list of 5 `CorpusEntry` objects with arxiv_id, category, expected_elements
    - Test `download_corpus(output_dir)` downloads PDFs to cache directory
    - Test `download_corpus()` skips already-cached files
  - Implement `peripatos/eval/__init__.py` and `peripatos/eval/corpus.py`:
    - Define 5 ArXiv papers (hardcoded IDs — agent should verify these IDs are valid and substitute if needed):
      1. **Math-heavy**: `2501.17887` (Docling paper — has formulas, tables, diagrams)
      2. **Table-heavy**: `2408.09869` (docling-eval paper — benchmark tables)
      3. **Code-heavy**: `2310.06825` (a code-heavy ML paper — pick one with code listings; verify ID or substitute)
      4. **Multi-column**: `2301.13848` (a typical two-column ML/NLP paper; verify ID or substitute)
      5. **Figure-heavy**: `2312.00752` (a paper with complex figures and mixed content; verify ID or substitute)
    - `CorpusEntry` dataclass: `arxiv_id: str`, `category: str`, `pdf_url: str`, `expected_elements: list[str]`
    - `get_corpus() -> list[CorpusEntry]` — returns the 5 entries
    - `download_corpus(output_dir: Path) -> list[Path]` — downloads PDFs from ArXiv, caches to `output_dir`, returns file paths
    - Use `urllib.request` for download (stdlib, no extra deps)
    - Cache: skip download if file already exists at `output_dir/{arxiv_id}.pdf`
  - Create `peripatos/eval/` directory with `__init__.py`

  **Must NOT do**:
  - Do NOT include more than 5 papers
  - Do NOT include non-English papers
  - Do NOT use external download libraries (requests, httpx) — use urllib
  - Do NOT include the actual PDF files in the repo — download on demand

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple data module with hardcoded entries and basic download logic
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3)
  - **Blocks**: Tasks 5, 10
  - **Blocked By**: None (can start immediately)

  **References** (CRITICAL):

  **Pattern References**:
  - `peripatos/models.py` — MVP Task 3 output. Follow the same dataclass pattern for `CorpusEntry`.
  - `peripatos/eye/arxiv.py` — MVP Task 6 output. Check how ArXiv PDF URLs are constructed (`https://arxiv.org/pdf/{id}`).

  **External References**:
  - ArXiv PDF URL format: `https://arxiv.org/pdf/{arxiv_id}` (no `.pdf` extension needed, redirects to PDF)
  - Paper `2501.17887`: Docling paper (has formulas, tables, layout diagrams)
  - Paper `2408.09869`: docling-eval paper (benchmark tables, metrics)

  **WHY Each Reference Matters**:
  - `arxiv.py`: Re-use the same URL construction pattern for consistency
  - `models.py`: Follow existing dataclass conventions (field naming, type hints)

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: `tests/test_eval.py`
  - [ ] Tests: `get_corpus()` returns 5 entries, `download_corpus()` creates files, skip-if-cached logic
  - [ ] `pytest tests/test_eval.py -k corpus` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Corpus entries are complete and valid
    Tool: Bash (python)
    Preconditions: peripatos installed
    Steps:
      1. Run: python -c "
         from peripatos.eval.corpus import get_corpus
         corpus = get_corpus()
         assert len(corpus) == 5, f'Expected 5, got {len(corpus)}'
         categories = {e.category for e in corpus}
         assert 'math-heavy' in categories
         assert 'table-heavy' in categories
         assert 'code-heavy' in categories
         print(f'PASS: {len(corpus)} papers, categories: {categories}')
         "
    Expected Result: Prints PASS with 5 papers and expected categories
    Failure Indicators: Wrong count, missing categories, ImportError
    Evidence: .sisyphus/evidence/task-4-corpus-entries.txt

  Scenario: Corpus download works and caches correctly
    Tool: Bash (python)
    Preconditions: Internet access, peripatos installed
    Steps:
      1. Run: python -c "
         import tempfile, os
         from pathlib import Path
         from peripatos.eval.corpus import download_corpus
         with tempfile.TemporaryDirectory() as d:
             paths = download_corpus(Path(d))
             assert len(paths) == 5, f'Expected 5 files, got {len(paths)}'
             for p in paths:
                 size = os.path.getsize(p)
                 assert size > 10000, f'{p.name} too small: {size} bytes'
                 print(f'{p.name}: {size:,} bytes')
             # Test caching: re-run should be instant
             import time; start = time.time()
             paths2 = download_corpus(Path(d))
             elapsed = time.time() - start
             assert elapsed < 2, f'Cache miss: took {elapsed:.1f}s'
             print(f'Cache test: {elapsed:.1f}s (expected <2s)')
             print('PASS')
         "
    Expected Result: 5 PDFs downloaded (each >10KB), cache re-run <2s
    Failure Indicators: Download failure, files too small, cache not working
    Evidence: .sisyphus/evidence/task-4-corpus-download.txt
  ```

  **Evidence to Capture:**
  - [ ] task-4-corpus-entries.txt — Corpus entry validation output
  - [ ] task-4-corpus-download.txt — Download and cache verification

  **Commit**: YES
  - Message: `feat(eval): add evaluation corpus with 5 ArXiv papers`
  - Files: `peripatos/eval/__init__.py`, `peripatos/eval/corpus.py`, `tests/test_eval.py`
  - Pre-commit: `pytest tests/test_eval.py -k corpus`

- [ ] 5. Evaluation Framework (compare.py + report.py)

  **What to do**:
  - Write RED tests first in `tests/test_eval.py` (append to existing):
    - Test `run_comparison(paper_path, base_converter, vlm_converter)` returns `ComparisonResult` with metrics
    - Test `generate_report(results, output_path)` creates a Markdown file with expected sections
    - Test report contains per-paper tables and a summary recommendation
  - First, **validate Assumption A6**: Can `docling-eval` compare two pipeline outputs?
    - Try: `from docling_eval import ...` and check if it supports comparing two `DoclingDocument` objects
    - If YES: use `docling-eval` metrics directly (TEDS, OCR edit-distance, layout mAP)
    - If NO: implement custom diff-based comparison:
      - Markdown text diff (difflib.unified_diff)
      - Table count comparison
      - Equation count comparison
      - Character-level edit distance (simple Levenshtein)
      - Structure comparison (heading count, section count)
  - Implement `peripatos/eval/compare.py`:
    - `ComparisonResult` dataclass: `paper_id: str`, `base_markdown: str`, `vlm_markdown: str`, `metrics: dict`, `base_time: float`, `vlm_time: float`
    - `run_comparison(paper_path: Path, base_converter: DocumentConverter, vlm_converter: DocumentConverter) -> ComparisonResult`
      - Convert paper with base converter → markdown + timing
      - Convert paper with VLM converter → markdown + timing
      - Compute metrics (docling-eval or custom diff)
      - Return ComparisonResult
    - `run_full_evaluation(corpus_dir: Path, vlm_backend: str | None = None) -> list[ComparisonResult]`
      - Iterates over all papers in corpus
      - Creates base and VLM converters
      - Runs comparison for each
  - Implement `peripatos/eval/report.py`:
    - `generate_report(results: list[ComparisonResult], output_path: Path) -> None`
    - Sections: Summary, Per-Paper Results (table for each), Metrics Comparison (aggregated), Timing Comparison, Recommendation
    - Recommendation logic: if VLM improves ≥2 metrics by ≥5%, recommend "ADOPT". Otherwise "SKIP" or "INCONCLUSIVE".

  **Must NOT do**:
  - Do NOT build custom TEDS implementation — use docling-eval/docling-metrics if available
  - Do NOT include Stage 2 evaluation (dialogue quality)
  - Do NOT create interactive visualizations
  - Do NOT evaluate multilingual documents

  **Recommended Agent Profile**:
  - **Category**: `deep`
    - Reason: Complex logic with A6 validation gate, metrics computation, report generation, and conditional implementation path
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 6, 7, 8)
  - **Blocks**: Task 10
  - **Blocked By**: Task 4 (corpus must exist)

  **References** (CRITICAL):

  **Pattern References**:
  - `peripatos/models.py` — MVP Task 3 output. Follow dataclass conventions for `ComparisonResult`.
  - `peripatos/eye/parser.py` — MVP Task 5 output. See how `DocumentConverter` is used to understand the base conversion pattern.

  **API/Type References**:
  - `docling-eval` API: `from docling_eval import ...` — check available classes/functions for comparing documents
  - `docling.document_converter.DocumentConverter` — the converter type for both base and VLM
  - `DoclingDocument.export_to_markdown()` — returns string, the primary comparison target

  **External References**:
  - `docling-eval` GitHub: `https://github.com/docling-project/docling-eval` — README, CLI commands, evaluation flow
  - `docling-eval` PyPI: Check API surface for programmatic usage (not just CLI)

  **WHY Each Reference Matters**:
  - `docling-eval`: Determines whether we use official metrics or custom diff. This is the A6 validation gate.
  - `parser.py`: Must understand converter usage to create the same pattern for comparison.
  - `models.py`: Dataclass style consistency.

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: `tests/test_eval.py`
  - [ ] Tests: `run_comparison()` returns valid `ComparisonResult`, `generate_report()` creates Markdown with expected sections
  - [ ] `pytest tests/test_eval.py -k "compare or report"` → PASS

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Comparison produces valid metrics for a single paper
    Tool: Bash (python)
    Preconditions: peripatos[vlm,eval] installed, at least 1 paper downloaded
    Steps:
      1. Run: python -c "
         from pathlib import Path
         from peripatos.eval.corpus import get_corpus, download_corpus
         from peripatos.eval.compare import run_comparison
         from docling.document_converter import DocumentConverter
         from peripatos.eye.vlm import create_vlm_converter
         import tempfile
         with tempfile.TemporaryDirectory() as d:
             paths = download_corpus(Path(d))
             base_conv = DocumentConverter()
             vlm_conv = create_vlm_converter()
             result = run_comparison(paths[0], base_conv, vlm_conv)
             assert result.paper_id, 'Missing paper_id'
             assert len(result.base_markdown) > 100, 'Base markdown too short'
             assert len(result.vlm_markdown) > 100, 'VLM markdown too short'
             assert result.metrics, 'No metrics computed'
             print(f'Paper: {result.paper_id}')
             print(f'Base markdown: {len(result.base_markdown)} chars, VLM: {len(result.vlm_markdown)} chars')
             print(f'Metrics: {result.metrics}')
             print(f'Timing: base={result.base_time:.1f}s, vlm={result.vlm_time:.1f}s')
             print('PASS')
         "
    Expected Result: Comparison completes with non-empty markdown from both pipelines and computed metrics
    Failure Indicators: Empty markdown, no metrics, timeout, converter error
    Evidence: .sisyphus/evidence/task-5-comparison-single.txt

  Scenario: Report generation produces valid Markdown file
    Tool: Bash (python)
    Preconditions: At least one ComparisonResult available
    Steps:
      1. Create a mock ComparisonResult with realistic data
      2. Run: generate_report([mock_result], Path("/tmp/test_report.md"))
      3. Read the generated file and verify sections exist
    Expected Result: File exists at /tmp/test_report.md with sections: Summary, Per-Paper Results, Metrics, Timing, Recommendation
    Failure Indicators: File not created, missing sections, malformed Markdown
    Evidence: .sisyphus/evidence/task-5-report-generation.txt
  ```

  **Evidence to Capture:**
  - [ ] task-5-comparison-single.txt — Single paper comparison output
  - [ ] task-5-report-generation.txt — Report generation verification

  **Commit**: YES (groups with Task 6)
  - Message: `feat(eval): add evaluation framework and extend parser with VLM support`
  - Files: `peripatos/eval/compare.py`, `peripatos/eval/report.py`, `tests/test_eval.py`
  - Pre-commit: `pytest tests/test_eval.py`

- [ ] 6. Extend PDFParser with VLM Support

  **What to do**:
  - Write RED tests first in `tests/test_vlm.py` (append):
    - Test `PDFParser(use_vlm=True)` creates parser with VLM converter
    - Test `PDFParser(use_vlm=True)` output is a valid `PaperMetadata` (same type as base)
    - Test `PDFParser(use_vlm=False)` behavior is identical to pre-existing behavior
    - Test `PDFParser(converter=custom_converter)` accepts externally-provided converter
  - Based on Task 1 findings:
    - If parser already accepts converter: just add `use_vlm: bool = False` parameter that creates VLM converter
    - If parser needs refactoring: add `converter: DocumentConverter | None = None` and `use_vlm: bool = False` to `__init__`
      - `use_vlm=True` → calls `create_vlm_converter()` from `peripatos/eye/vlm.py`
      - `converter` provided → use it directly (for testing, custom converters)
      - Neither → use default `DocumentConverter()` (existing behavior preserved)
  - Add optional `parser_type: str = "standard"` field to `PaperMetadata` dataclass (or leave it out if Task 1 shows it's unnecessary)
  - Verify: all existing parser tests still pass (zero regressions)

  **Must NOT do**:
  - Do NOT change the return type of `parse()` — it must still return `PaperMetadata`
  - Do NOT change the default behavior — `PDFParser()` must work exactly as before
  - Do NOT create abstract base classes or complex inheritance
  - Do NOT import torch/transformers at module top level in parser.py

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Modifying existing MVP code requires careful regression testing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 7, 8)
  - **Blocks**: Tasks 9, 10
  - **Blocked By**: Tasks 1, 2, 3

  **References** (CRITICAL):

  **Pattern References**:
  - `peripatos/eye/parser.py` — MVP Task 5 output. THE file being modified. Read thoroughly — understand every method, every import, every usage of DocumentConverter.
  - `peripatos/eye/vlm.py` — Task 3 output. Import `create_vlm_converter()` from here.
  - `tests/test_parser.py` — MVP existing parser tests. Must ALL still pass after changes.

  **API/Type References**:
  - `peripatos/models.py:PaperMetadata` — The return type. May add optional `parser_type` field.
  - `docling.document_converter.DocumentConverter` — The type of both base and VLM converters.

  **External References**:
  - None needed — pure internal integration

  **WHY Each Reference Matters**:
  - `parser.py`: The file being extended — must understand current interface completely
  - `vlm.py`: The VLM converter factory being integrated
  - `test_parser.py`: Regression guard — all existing tests must pass
  - `models.py`: Output type may get optional field addition

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests added to `tests/test_vlm.py`: VLM parser creation, output type, regression
  - [ ] `pytest tests/test_vlm.py` → PASS
  - [ ] `pytest tests/test_parser.py` → PASS (zero regressions)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: VLM parser produces valid PaperMetadata
    Tool: Bash (python)
    Preconditions: peripatos[vlm] installed, test PDF available
    Steps:
      1. Run: python -c "
         from peripatos.eye.parser import PDFParser
         parser = PDFParser(use_vlm=True)
         result = parser.parse('tests/fixtures/sample_paper.pdf')
         print(f'Type: {type(result).__name__}')
         print(f'Title: {result.title}')
         print(f'Sections: {len(result.sections)}')
         print('PASS')
         "
    Expected Result: Returns PaperMetadata with title and sections populated
    Failure Indicators: Wrong return type, empty sections, converter error
    Evidence: .sisyphus/evidence/task-6-vlm-parser.txt

  Scenario: Base parser behavior unchanged (regression test)
    Tool: Bash (pytest)
    Preconditions: peripatos installed
    Steps:
      1. Run: pytest tests/test_parser.py -v --tb=short
      2. Verify all tests pass
    Expected Result: All pre-existing parser tests pass with 0 failures
    Failure Indicators: Any test failure = regression introduced
    Evidence: .sisyphus/evidence/task-6-regression.txt
  ```

  **Evidence to Capture:**
  - [ ] task-6-vlm-parser.txt — VLM parser output verification
  - [ ] task-6-regression.txt — Regression test results

  **Commit**: YES (groups with Task 5)
  - Message: `feat(eval): add evaluation framework and extend parser with VLM support`
  - Files: `peripatos/eye/parser.py`, `peripatos/models.py` (if modified), `tests/test_vlm.py`
  - Pre-commit: `pytest tests/` (MANDATORY — after ALL implementation tasks)

- [ ] 7. Single-Page Benchmark (Timing)

  **What to do**:
  - Before running the full 5-paper evaluation, benchmark VLM inference speed on a single page
  - Download one paper from the corpus (first entry)
  - Time single-page conversion with MLX backend (primary dev machine)
  - Time single-page conversion with base Docling (for comparison)
  - Record results: `{backend, seconds_per_page, markdown_length}`
  - If MLX takes >30s/page: flag as concern but continue (evaluation corpus is only 5 papers)
  - If MLX takes >120s/page: abort full evaluation — model may be broken or hardware insufficient
  - Save timing results as evidence

  **Must NOT do**:
  - Do NOT run CUDA benchmark (may not have CUDA GPU on dev machine)
  - Do NOT run CPU benchmark (that's Task 8)
  - Do NOT modify any code — this is a measurement task

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple timing measurement, no code changes
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 8)
  - **Blocks**: Task 10 (timing data informs whether full eval is feasible)
  - **Blocked By**: Task 3 (VLM converter factory must exist)

  **References** (CRITICAL):

  **Pattern References**:
  - `peripatos/eye/vlm.py` — Task 3 output. Use `create_vlm_converter()` to create the converter.
  - `peripatos/eval/corpus.py` — Task 4 output. Use `get_corpus()` and `download_corpus()` to get a test paper.

  **External References**:
  - Docling VLM docs timing table: `https://docling-project.github.io/docling/usage/vision_models/` — SmolDocling MLX ~6s/page as reference point. Granite Docling timing not yet published.

  **WHY Each Reference Matters**:
  - `vlm.py`: Need the converter to do the benchmark
  - `corpus.py`: Need a real ArXiv paper, not a synthetic test
  - Docling docs: Reference point for expected speed (SmolDocling MLX ~6s/page)

  **Acceptance Criteria**:

  - [ ] Timing data recorded for MLX backend: seconds/page + markdown length
  - [ ] Timing data recorded for base Docling: seconds/page + markdown length
  - [ ] Go/no-go decision documented: proceed with full eval or abort

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: MLX benchmark completes in reasonable time
    Tool: Bash (python)
    Preconditions: peripatos[vlm] installed (MLX deps auto-included on Apple Silicon via platform marker), Apple Silicon Mac
    Steps:
      1. Run: python -c "
         import time
         from pathlib import Path
         from docling.document_converter import DocumentConverter
         from peripatos.eye.vlm import create_vlm_converter
         from peripatos.eval.corpus import get_corpus, download_corpus
         import tempfile

         with tempfile.TemporaryDirectory() as d:
             paths = download_corpus(Path(d))
             paper = paths[0]

             # Base timing
             base_conv = DocumentConverter()
             start = time.time()
             base_doc = base_conv.convert(source=str(paper)).document
             base_time = time.time() - start
             base_md = base_doc.export_to_markdown()

             # VLM timing
             vlm_conv = create_vlm_converter(backend='mlx')
             start = time.time()
             vlm_doc = vlm_conv.convert(source=str(paper)).document
             vlm_time = time.time() - start
             vlm_md = vlm_doc.export_to_markdown()

             print(f'Base: {base_time:.1f}s, {len(base_md)} chars')
             print(f'VLM (MLX): {vlm_time:.1f}s, {len(vlm_md)} chars')
             print(f'Speedup: {base_time/vlm_time:.1f}x' if vlm_time > 0 else 'N/A')
             if vlm_time > 120:
                 print('WARNING: VLM too slow (>120s/page). Consider aborting full eval.')
             elif vlm_time > 30:
                 print('NOTE: VLM slower than expected (>30s/page). Proceeding anyway.')
             else:
                 print('GOOD: VLM speed acceptable (<30s/page)')
             print('PASS')
         "
    Expected Result: Both conversions complete, timing data printed, go/no-go decision
    Failure Indicators: VLM conversion fails, OOM, >120s/page
    Evidence: .sisyphus/evidence/task-7-mlx-benchmark.txt

  Scenario: Timing results show VLM produces longer/richer markdown
    Tool: Bash (analysis of above output)
    Preconditions: Above scenario completed
    Steps:
      1. Compare base_md length vs vlm_md length
      2. Verify VLM markdown is non-empty and reasonable
    Expected Result: VLM markdown length >= base markdown length (VLM captures more structure)
    Failure Indicators: VLM markdown empty or shorter than base (model failure or token loop)
    Evidence: .sisyphus/evidence/task-7-mlx-benchmark.txt (same file as above)
  ```

  **Evidence to Capture:**
  - [ ] task-7-mlx-benchmark.txt — Timing results for MLX and base backends

  **Commit**: NO (measurement task, no code changes)

- [ ] 8. CPU Smoke Test

  **What to do**:
  - Run VLM conversion on a single page using CPU backend (Transformers without GPU)
  - Purpose: verify the CPU fallback path works, not benchmark speed
  - Use the same first paper from the corpus
  - Set a generous timeout (10 minutes) since CPU inference is expected to be very slow
  - Record: did it complete? How long? Was markdown output valid?
  - If OOM: document the error and recommend minimum RAM

  **Must NOT do**:
  - Do NOT run full corpus on CPU
  - Do NOT treat CPU speed as a quality gate
  - Do NOT modify any code

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Single execution, no code changes, just verification
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 5, 6, 7)
  - **Blocks**: Task 11
  - **Blocked By**: Task 3 (VLM converter factory must exist)

  **References** (CRITICAL):

  **Pattern References**:
  - `peripatos/eye/vlm.py` — Task 3 output. Use `create_vlm_converter(backend='cpu')`.
  - `peripatos/eval/corpus.py` — Task 4 output. Get a test paper.

  **WHY Each Reference Matters**:
  - `vlm.py`: Need to explicitly force CPU backend
  - `corpus.py`: Need a real paper to test with

  **Acceptance Criteria**:

  - [ ] CPU VLM conversion completes on 1 page without crash
  - [ ] Markdown output is non-empty and reasonable
  - [ ] Timing and resource usage documented

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: CPU VLM fallback works on single page
    Tool: Bash (python)
    Preconditions: peripatos[vlm] installed, no GPU required
    Steps:
      1. Run: python -c "
         import time, signal, sys
         from pathlib import Path
         from peripatos.eye.vlm import create_vlm_converter
         from peripatos.eval.corpus import get_corpus, download_corpus
         import tempfile

         def timeout_handler(signum, frame):
             print('TIMEOUT: CPU inference exceeded 10 minutes — expected for large docs')
             sys.exit(1)
         signal.signal(signal.SIGALRM, timeout_handler)
         signal.alarm(600)  # 10-minute timeout (portable, no coreutils needed)

         with tempfile.TemporaryDirectory() as d:
             paths = download_corpus(Path(d))
             vlm_conv = create_vlm_converter(backend='cpu')
             start = time.time()
             doc = vlm_conv.convert(source=str(paths[0])).document
             elapsed = time.time() - start
             signal.alarm(0)  # cancel timeout
             md = doc.export_to_markdown()
             print(f'CPU VLM: {elapsed:.1f}s, {len(md)} chars')
             assert len(md) > 50, f'Output too short: {len(md)} chars'
             print('PASS: CPU fallback works')
         "
    Expected Result: Conversion completes (may take minutes), markdown output >50 chars
    Failure Indicators: OOM, timeout (>10 min), empty output, crash
    Evidence: .sisyphus/evidence/task-8-cpu-smoke.txt

  Scenario: CPU conversion produces comparable markdown to MLX
    Tool: Bash (analysis)
    Preconditions: Task 7 MLX benchmark results available
    Steps:
      1. Compare CPU markdown length vs MLX markdown length from Task 7
      2. They should be similar (same model, different backend)
    Expected Result: CPU and MLX markdown lengths within 20% of each other
    Failure Indicators: Wildly different lengths (suggests backend-specific issues)
    Evidence: .sisyphus/evidence/task-8-cpu-smoke.txt (same file)
  ```

  **Evidence to Capture:**
  - [ ] task-8-cpu-smoke.txt — CPU smoke test results

  **Commit**: NO (measurement task, no code changes)

- [ ] 9. CLI --vlm Flag Integration

  **What to do**:
  - Write RED tests first in `tests/test_cli.py` (append):
    - Test `peripatos generate --vlm <pdf>` argument is parsed correctly
    - Test `--vlm` flag is `store_true` (default False)
    - Test VLM path produces valid output when deps installed
    - Test VLM path produces helpful error when deps NOT installed
  - Modify `peripatos/cli.py`:
    - Add `--vlm` flag to the `generate` subcommand: `parser.add_argument('--vlm', action='store_true', default=False, help='Use Granite Docling VLM for enhanced PDF parsing (requires: pip install peripatos[vlm])')`
    - In the generate command handler:
      - If `args.vlm`: try to create VLM parser, catch `ImportError`, show helpful message
      - Pass `use_vlm=args.vlm` to `PDFParser()` constructor
  - Verify: `peripatos generate --help` shows the new flag
  - Verify: `peripatos generate <pdf>` (without --vlm) works identically to before

  **Must NOT do**:
  - Do NOT change any existing CLI flags or behavior
  - Do NOT add `--backend` or `--model` flags — just `--vlm`
  - Do NOT import VLM modules at top level of cli.py

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Small, well-defined change to argparse
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Tasks 10, 11)
  - **Blocks**: Tasks 10, 11
  - **Blocked By**: Task 6 (parser must support use_vlm)

  **References** (CRITICAL):

  **Pattern References**:
  - `peripatos/cli.py` — MVP Task 14 output. THE file being modified. Understand existing argparse structure.
  - `tests/test_cli.py` — MVP existing CLI tests. Must ALL still pass.

  **API/Type References**:
  - `peripatos/eye/parser.py:PDFParser(use_vlm=True)` — Task 6 output. How to use the VLM-enabled parser.

  **WHY Each Reference Matters**:
  - `cli.py`: The file being modified — must match existing patterns
  - `test_cli.py`: Regression guard
  - `parser.py`: Must know the exact parameter name to pass

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Tests added to `tests/test_cli.py`: --vlm flag parsing, error handling
  - [ ] `pytest tests/test_cli.py` → PASS
  - [ ] All existing CLI tests still pass

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: --vlm flag appears in help output
    Tool: Bash
    Preconditions: peripatos installed
    Steps:
      1. Run: peripatos generate --help
      2. Check output contains '--vlm'
      3. Check help text mentions 'pip install peripatos[vlm]'
    Expected Result: Help output includes --vlm flag with installation instructions
    Failure Indicators: Flag not shown, or help text unclear
    Evidence: .sisyphus/evidence/task-9-vlm-help.txt

  Scenario: --vlm flag with deps installed produces MP3
    Tool: Bash
    Preconditions: peripatos[vlm] installed, test PDF available, API keys configured
    Steps:
      1. Run: peripatos generate --vlm tests/fixtures/sample_paper.pdf --output-dir /tmp/vlm-cli-test
      2. Check: ls /tmp/vlm-cli-test/*.mp3
    Expected Result: MP3 file produced in output directory
    Failure Indicators: No MP3 file, error during pipeline
    Evidence: .sisyphus/evidence/task-9-vlm-e2e.txt

  Scenario: --vlm flag without deps gives helpful error
    Tool: Bash
    Preconditions: Base peripatos installed WITHOUT [vlm] extras
    Steps:
      1. Run: peripatos generate --vlm tests/fixtures/sample_paper.pdf 2>&1
      2. Check output for error mentioning 'pip install peripatos[vlm]'
    Expected Result: Error message includes installation instructions, not a raw ImportError traceback
    Failure Indicators: Raw traceback instead of user-friendly message, or no error at all
    Evidence: .sisyphus/evidence/task-9-vlm-missing-deps.txt
  ```

  **Evidence to Capture:**
  - [ ] task-9-vlm-help.txt — CLI help output with --vlm flag
  - [ ] task-9-vlm-e2e.txt — End-to-end VLM CLI test
  - [ ] task-9-vlm-missing-deps.txt — Missing deps error handling

  **Commit**: YES
  - Message: `feat(cli): add --vlm flag to generate command`
  - Files: `peripatos/cli.py`, `tests/test_cli.py`
  - Pre-commit: `pytest tests/test_cli.py`

- [ ] 10. Run Full 5-Paper Evaluation + Generate Report

  **What to do**:
  - Run the full evaluation framework on all 5 corpus papers
  - Use MLX backend on dev machine (Apple Silicon)
  - Execute: `python -m peripatos.eval.compare --corpus <corpus_dir> --output evaluation_report.md`
  - Or equivalent programmatic invocation:
    ```python
    from peripatos.eval.compare import run_full_evaluation
    from peripatos.eval.report import generate_report
    results = run_full_evaluation(corpus_dir, vlm_backend="mlx")
    generate_report(results, Path("evaluation_report.md"))
    ```
  - Review the generated report:
    - Per-paper metrics comparison table
    - Aggregated metrics summary
    - Timing comparison (base vs VLM)
    - Automated recommendation (ADOPT / SKIP / INCONCLUSIVE)
  - If any paper fails (timeout, OOM, token loop): document the failure, skip that paper, continue with remaining
  - Save the complete report as evidence

  **Must NOT do**:
  - Do NOT modify the evaluation framework code (that's Tasks 5)
  - Do NOT run on CPU (too slow)
  - Do NOT manually edit the report — it should be fully automated
  - Do NOT include Stage 2 evaluation

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Long-running task, may hit edge cases (timeouts, token loops), needs judgment calls
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (sequential — needs all prior tasks)
  - **Parallel Group**: Wave 3 (starts after T9 completes; T9 and T11 can start before T10 finishes)
  - **Blocks**: Task 11
  - **Blocked By**: Tasks 5, 6, 7, 9

  **References** (CRITICAL):

  **Pattern References**:
  - `peripatos/eval/compare.py` — Task 5 output. The evaluation runner.
  - `peripatos/eval/report.py` — Task 5 output. The report generator.
  - `peripatos/eval/corpus.py` — Task 4 output. The corpus manager.

  **WHY Each Reference Matters**:
  - These are the tools being used to run the evaluation. Must understand the API to invoke correctly.

  **Acceptance Criteria**:

  - [ ] `evaluation_report.md` file exists
  - [ ] Report contains metrics for all 5 papers (or documents failures for skipped papers)
  - [ ] Report contains aggregated summary section
  - [ ] Report contains timing comparison
  - [ ] Report contains automated recommendation (ADOPT / SKIP / INCONCLUSIVE)
  - [ ] All evidence captured

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full evaluation completes and produces report
    Tool: Bash (python)
    Preconditions: peripatos[vlm,eval] installed, corpus downloaded, MLX available
    Steps:
      1. Run the full evaluation (may take 10-30 minutes for 5 papers)
      2. Verify report file exists
      3. Verify report has required sections
    Expected Result: evaluation_report.md exists with Summary, Per-Paper Results, Metrics, Timing, Recommendation sections
    Failure Indicators: Report missing, incomplete sections, all papers failed
    Evidence: .sisyphus/evidence/task-10-evaluation-report.md (copy of the report)

  Scenario: Report contains meaningful metrics (not zeros/NaN)
    Tool: Bash
    Preconditions: Report generated
    Steps:
      1. Run: grep -E "[0-9]+\.[0-9]+" evaluation_report.md | head -20
      2. Verify numeric values present (not all zeros, not NaN)
    Expected Result: Multiple lines with decimal numbers representing actual metrics
    Failure Indicators: All zeros, NaN values, or no numeric content
    Evidence: .sisyphus/evidence/task-10-metrics-check.txt
  ```

  **Evidence to Capture:**
  - [ ] task-10-evaluation-report.md — Copy of the generated evaluation report
  - [ ] task-10-metrics-check.txt — Verification that metrics are meaningful

  **Commit**: YES
  - Message: `docs(eval): add evaluation report for Granite Docling VLM`
  - Files: `evaluation_report.md`
  - Pre-commit: file exists with expected sections

- [ ] 11. Integration Tests + Documentation

  **What to do**:
  - Write integration tests in `tests/test_vlm_integration.py`:
    - Test full flow: `PDFParser(use_vlm=True).parse(pdf) → PaperMetadata` on a real small PDF
    - Test CLI round-trip: `peripatos generate --vlm <pdf>` produces output
    - Test eval round-trip: `run_comparison()` on a single paper produces valid results
    - Test base pipeline regression: all existing tests still pass with VLM code present
  - Update `README.md` with VLM section:
    - Add "Enhanced PDF Parsing (VLM)" section
    - Installation: `pip install peripatos[vlm]`
    - Usage: `peripatos generate --vlm <arxiv_id_or_pdf>`
    - Hardware requirements: Apple Silicon recommended, GPU optional, CPU possible but slow
    - Note: Experimental feature, evaluation results available in `evaluation_report.md`
  - Run full test suite: `pytest tests/ --tb=short` — verify zero failures

  **Must NOT do**:
  - Do NOT write documentation beyond the README VLM section
  - Do NOT create separate VLM documentation files
  - Do NOT modify the evaluation report

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration testing requires end-to-end verification across multiple modules
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO (depends on everything else)
  - **Parallel Group**: Wave 3 (after Tasks 9, 10)
  - **Blocks**: FINAL wave
  - **Blocked By**: Tasks 8, 9, 10

  **References** (CRITICAL):

  **Pattern References**:
  - `tests/` — All existing MVP test files. Follow patterns for integration tests.
  - `README.md` — MVP documentation. Add VLM section matching existing style.
  - `peripatos/eye/parser.py` — The extended parser to integration-test.
  - `peripatos/cli.py` — The updated CLI to integration-test.
  - `peripatos/eval/compare.py` — The evaluation framework to integration-test.

  **WHY Each Reference Matters**:
  - All the modules being integration-tested. Must understand their APIs to write meaningful tests.
  - `README.md`: Must match existing documentation style and structure.

  **Acceptance Criteria**:

  **TDD:**
  - [ ] Test file: `tests/test_vlm_integration.py`
  - [ ] `pytest tests/test_vlm_integration.py` → PASS
  - [ ] `pytest tests/` → PASS (ALL tests, zero failures)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full test suite passes with VLM code present
    Tool: Bash (pytest)
    Preconditions: peripatos[vlm,eval] installed
    Steps:
      1. Run: pytest tests/ --tb=short -q
      2. Verify zero failures
    Expected Result: All tests pass, including pre-existing MVP tests
    Failure Indicators: Any failure = regression or integration issue
    Evidence: .sisyphus/evidence/task-11-full-suite.txt

  Scenario: README contains VLM section
    Tool: Bash (grep)
    Preconditions: README.md updated
    Steps:
      1. Run: grep -A5 "VLM\|vlm\|Enhanced PDF" README.md
      2. Verify section exists with installation and usage instructions
    Expected Result: README contains VLM section with pip install command and CLI usage
    Failure Indicators: Section missing, or incomplete instructions
    Evidence: .sisyphus/evidence/task-11-readme-check.txt
  ```

  **Evidence to Capture:**
  - [ ] task-11-full-suite.txt — Full pytest results
  - [ ] task-11-readme-check.txt — README VLM section verification

  **Commit**: YES
  - Message: `test(vlm): add integration tests and update documentation`
  - Files: `tests/test_vlm_integration.py`, `README.md`
  - Pre-commit: `pytest tests/`

---

## Final Verification Wave

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in `.sisyphus/evidence/`. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run linter + `pytest`. Review all changed files for: `as any`/type:ignore, empty catches, print in prod, commented-out code, unused imports. Check AI slop: excessive comments, over-abstraction, generic names. Verify VLM code doesn't pollute base pipeline namespace.
  Output: `Build [PASS/FAIL] | Lint [PASS/FAIL] | Tests [N pass/N fail] | Files [N clean/N issues] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Start from clean state. Run `pip install -e .[vlm,eval]`. Execute `peripatos generate --vlm` on a test PDF. Run evaluation script on all 5 papers. Verify report is generated and contains expected sections. Test `peripatos generate` (without --vlm) still works identically. Test error path: uninstall VLM deps, run `--vlm`, verify error message.
  Output: `Scenarios [N/N pass] | Integration [N/N] | Edge Cases [N tested] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual diff. Verify 1:1 — everything in spec was built, nothing beyond spec was built. Check "Must NOT do" compliance. Verify no base pipeline files were modified (only extended). Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Contamination [CLEAN/N issues] | Unaccounted [CLEAN/N files] | VERDICT`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 2 | `chore(deps): add vlm and eval optional dependency groups` | `pyproject.toml` | `pip install -e .[vlm,eval]` |
| 3 | `feat(eye): add VLM converter factory with MLX/CUDA/CPU support` | `peripatos/eye/vlm.py`, `tests/test_vlm.py` | `pytest tests/test_vlm.py` |
| 4 | `feat(eval): add evaluation corpus with 5 ArXiv papers` | `peripatos/eval/corpus.py`, `tests/test_eval.py` | `pytest tests/test_eval.py -k corpus` |
| 5+6 | `feat(eval): add evaluation framework and extend parser with VLM support` | `peripatos/eval/compare.py`, `peripatos/eval/report.py`, `peripatos/eye/parser.py`, `tests/test_eval.py`, `tests/test_vlm.py` | `pytest tests/` |
| 9 | `feat(cli): add --vlm flag to generate command` | `peripatos/cli.py`, `tests/test_cli.py` | `pytest tests/test_cli.py` |
| 10 | `docs(eval): add evaluation report for Granite Docling VLM` | `evaluation_report.md` | file exists with expected sections |
| 11 | `test(vlm): add integration tests and update documentation` | `tests/test_vlm_integration.py`, `README.md` | `pytest tests/` |

---

## Success Criteria

### Verification Commands
```bash
# VLM flag works
peripatos generate --vlm tests/fixtures/sample_paper.pdf --output-dir /tmp/vlm-test
test -f /tmp/vlm-test/*.mp3  # Expected: file exists

# Base pipeline unchanged
peripatos generate tests/fixtures/sample_paper.pdf --output-dir /tmp/base-test
pytest tests/ -k "not vlm"  # Expected: all pass

# Optional deps work
pip install peripatos  # base only
peripatos generate --vlm 2>&1 | grep -i "install"  # Expected: error mentioning pip install peripatos[vlm]

# Evaluation report generated
python -m peripatos.eval.compare --output evaluation_report.md
test -f evaluation_report.md  # Expected: file exists
grep "TEDS\|F1\|edit" evaluation_report.md | wc -l  # Expected: 5+ lines

# All tests pass
pytest tests/ --tb=short  # Expected: 0 failures
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All tests pass (including pre-existing MVP tests)
- [ ] Evaluation report exists with metrics for all 5 papers
- [ ] `--vlm` flag works on Apple Silicon (MLX)
- [ ] Base pipeline behavior unchanged (zero regressions)
