# Changelog

All notable changes to Peripatos are documented here.

## [1.1.0] - 2026-05-21

### Added
- Agentic ReAct RAG pipeline replaces single-pass dialogue generator
- New source types: HTML URLs, Markdown files (.md), plain text files (.txt)
- `rag` config block: `embedding_model`, `chunk_size`, `chunk_overlap`, `top_k`, `cache_dir`
- FAISS vector store with disk cache keyed by source SHA256
- Native OpenAI function-calling tools: `search`, `read_chunk`, `list_sections`, `draft_turn`, `finalize`

### Removed
- `llm.max_paper_chars` config field (use `rag.chunk_size` instead)
- Single-pass `DialogueGenerator` (replaced by ReAct agent)

## [1.0.0] — 2026-05-21

### Added
- **Two-voice TTS**: Host and interviewee now use distinct voices by default.
  - Edge TTS defaults: `en-US-GuyNeural` (host) + `en-US-AriaNeural` (interviewee)
  - OpenAI-compatible TTS defaults: `onyx` (host) + `nova` (interviewee)
- New config schema: `tts.voices.host` and `tts.voices.interviewee`
- `peripatos doctor` now reports both voices and their source (config/default/legacy)
- Provider-aware voice defaults via `DEFAULT_VOICES` in `registry.py`

### Changed
- `peripatos doctor` output updated to show two voice lines instead of one

### Deprecated
- `tts.voice` (single voice for both speakers): still works but emits a `DeprecationWarning`.
  Use `tts.voices.host` and `tts.voices.interviewee` instead.

### Fixed
- Both speakers now use distinct voices in generated podcasts (previously both used the same voice)
