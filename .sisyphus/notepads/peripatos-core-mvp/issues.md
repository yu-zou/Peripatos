- Docling conversion requires network/model downloads in this environment; QA parse hit network timeout.
- LSP false positive: edge_tts import not resolved by language server, but package is installed and works.
- pytest-asyncio may generate RuntimeWarning for coroutines not awaited in mocked error paths; non-critical.

## Task 9: OpenAI TTS Engine (Feb 19, 2026)

### Issues Encountered
- **LSP diagnostics unavailable**: basedpyright not installed in environment
  - Workaround: Used manual import testing via `python -c` to verify module works
  - No actual runtime issues - LSP errors were environmental, not code issues

### Design Trade-offs
- **Hard limit enforcement**: If a chunk reaches exactly 4096 chars without hitting a boundary, we split anyway
  - This could split mid-word in extreme edge cases
  - Trade-off: Reliability (never exceed limit) vs. perfect linguistic splits
  - Decision: Reliability wins - API will reject oversized requests

### Potential Future Improvements
- Could add word boundary detection as 3rd-tier fallback
- Could implement more sophisticated sentence detection (handle abbreviations like "Dr.", "Mr.", etc.)
- Could add support for configurable model (tts-1 vs tts-1-hd) via config.py
- Could add audio format options (mp3, opus, aac, flac)

## Task 8: Brain Dialogue Generator (Feb 19, 2026)

### Issues Encountered
- **LSP diagnostics unavailable**: basedpyright not installed; proceeded with pytest for verification.

## Task 12: Bilingual Code-Switching Issues

**Trade-offs:**
1. **Trust LLM vs. Validation**: Current implementation trusts LLM to preserve English technical terms
   - Pro: Simpler code, leverages LLM capabilities
   - Con: No validation if LLM mistranslates terms (e.g., "Transformer" → "变换器")
   - Mitigation: _preserve_technical_terms() method exists as hook for future regex-based validation

2. **Limited Language Support**: Only Chinese+English bilingual mode implemented
   - Other language pairs (Japanese+English, Korean+English) would need separate implementations
   - Current LanguageMode.ZH_EN is hardcoded; future expansion would require new enum values

**Potential Enhancements:**
- Add regex-based validation in _preserve_technical_terms() to enforce whitelist
- Detect TTS boundary issues (e.g., add pauses at language switches)
- Support custom technical term whitelists per domain (biology, physics, etc.)
