# Changelog

All notable changes to Peripatos are documented here.

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
