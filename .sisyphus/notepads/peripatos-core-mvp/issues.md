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

