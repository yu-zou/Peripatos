- Implemented Docling converter setup via PdfFormatOption and InputFormat to apply PdfPipelineOptions.
- Added heading-based section splitting and classification heuristics for SectionType mapping.
- Edge-tts provides async streaming API that requires wrapping in asyncio.run() for sync callers.
- Voice distinction (host/expert) achieved via tone: AriaNeural (female conversational) vs GuyNeural (male deeper) for English.
- Bilingual support with distinct Chinese voices: XiaoxiaoNeural (female) vs YunxiNeural (male).
- Async for chunks with type filtering ensures clean audio data collection from edge_tts.Communicate.stream().
- No API key/authentication required makes edge-tts ideal fallback when OpenAI is unavailable.

## Task 9: OpenAI TTS Engine (Feb 19, 2026)

### Implementation Patterns
- **Smart chunking algorithm**: Implemented 2-tier splitting strategy
  1. Split at sentence boundaries first (`. `, `? `, `! `)
  2. For sentences >4096 chars, split at clause boundaries (`, `, `; `)
  3. Hard limit enforcement: if chunk reaches 4096, split immediately
- **Lazy client initialization**: OpenAI client created only when needed (in `synthesize()`)
- **Retry logic with exponential backoff**: For rate limits, retry up to 3 times with 1s, 2s, 4s delays
- **Error wrapping**: All exceptions wrapped in custom `TTSError` for consistent error handling

### Voice Configuration
- Default voices from config.py:
  - Host: "alloy" (warmer, conversational)
  - Expert: "onyx" (deeper, authoritative)
- Model default: "tts-1" (cost-effective) instead of "tts-1-hd"

### Testing Strategy
- **15 comprehensive tests** covering:
  - Chunking logic (sentence boundaries, clause boundaries, limits)
  - API availability checks
  - Mocked API calls (using unittest.mock)
  - Different voices
  - Chunk concatenation
  - Error handling
  - Edge cases (empty strings, short text, mixed punctuation)

### Key Technical Decisions
- Used **character-by-character iteration** for boundary detection (more reliable than regex for multi-char boundaries)
- Chunk at **80% of max size** for clause boundaries (provides buffer for finding good split point)
- Preserve punctuation and spaces in chunks (maintains natural flow)


## ArXiv Fetcher Implementation (Task 7 - Implementation)

### Implementation Details
- **File**: `peripatos/eye/arxiv.py` (140 lines)
- **Test Coverage**: All 19 tests passing (100%)

### Key Implementation Decisions
1. **ID Validation**: Uses compiled regex pattern `^\d{4}\.\d{4,5}(v\d+)?$` for performance
2. **HTTP Client**: Uses stdlib `urllib.request` (no external dependencies)
3. **XML Parsing**: Uses `xml.etree.ElementTree` with namespace handling for ArXiv API
4. **Temp Directory**: Uses `tempfile.mkdtemp()` for PDF storage (configurable)
5. **Error Handling**: All failures wrapped in custom `FetchError` exception

### ArXiv API Integration
- **PDF URL**: `https://arxiv.org/pdf/{arxiv_id}`
- **Metadata API**: `http://export.arxiv.org/api/query?id_list={base_id}`
- **XML Namespace**: Uses `http://www.w3.org/2005/Atom` for parsing
- **Metadata Extract**: title, authors list, summary text

### Version Suffix Handling
- Valid IDs: `2408.09869` and `2408.09869v1` (etc.)
- Version suffix stripped for API queries but preserved in file names
- Pattern allows multi-digit versions (v1, v2, v10, etc.)

### Error Cases Tested
✓ Invalid ID format (dashes, missing dot, too short, empty, malformed version)
✓ Network failures (connection timeout, 404 responses)
✓ API parsing failures (invalid XML)
✓ Missing entry in API response

### Design Patterns Used
- Single Responsibility: validate, fetch, extract_metadata are separate methods
- Fail-Fast: validation happens before network calls
- Resource Cleanup: context managers for HTTP responses
- Type Hints: Full type annotations for public API


## Task 7: LaTeX Math Normalization

### Implementation Approach
- **TDD**: Wrote 30 comprehensive tests first, then implemented to make them pass
- **Regex-based**: No external libraries, pure regex transformations
- **Transformation order matters**: Process subscripts before exponents to handle bounds correctly (e.g., `\sum_{i=1}^{N}`)

### Key Patterns Implemented
1. **Fractions**: `\frac{a}{b}` → "a over b" (handles nested braces)
2. **Exponents**: 
   - `x^2` → "x squared"
   - `x^3` → "x cubed"
   - `x^n` → "x to the power of n"
   - `x^{2n+1}` → "x to the power of 2n+1"
3. **Greek letters**: `\alpha`, `\beta`, etc. → spelled out names
4. **Operators**: `\sum`, `\prod`, `\int`, `\partial` → "the sum of", etc.
5. **Comparisons**: `\leq`, `\geq` → "less than or equal to", etc.
6. **Roots**: `\sqrt{x}` → "the square root of x"
7. **Subscripts**: `x_i` → "x i" (simplified handling)

### Delimiters Supported
- Inline: `$...$`
- Display: `$$...$$` and `\[...\]`

### Test Coverage
- Simple patterns (exponents, fractions, Greek)
- Complex nested expressions (summations with bounds)
- Edge cases (empty strings, no math, multiple expressions)
- All delimiters
- Non-math text preservation

### Output Quality
- QA scenario produces readable spoken approximations
- Not perfect transcription, but conceptually clear
- Example: `$\sum_{i=1}^{N} x_i$` → "the sum of i=1 to the power of N x i"

## Task 8: Brain Dialogue Generator (Feb 19, 2026)

### Implementation Patterns
- **Lazy LLM client initialization** via importlib to avoid hard dependency imports at module load.
- **Retry with exponential backoff** on rate-limit errors (1s, 2s, 4s) for both OpenAI and Anthropic.
- **Persona prompts** kept distinct for HOST and EXPERT roles to satisfy archetype requirements.

### Testing Strategy
- Mocked OpenAI/Anthropic clients through importlib patching to verify message construction.
- JSON parsing tests ensure DialogueTurn mapping and error handling for invalid responses.

## Task 12: Bilingual Code-Switching (Feb 19, 2026)

**Approach:**
- Followed TDD: wrote 7 comprehensive tests before implementation
- Created BilingualProcessor class with simple pass-through design
- Trust LLM output via prompt modifier rather than complex post-processing

**Technical Decisions:**
1. **Prompt Modifier Strategy**: Generate bilingual instruction string to append to system prompts
   - ZH_EN mode: Explicit instruction to use Chinese explanations + English technical terms
   - EN mode: Empty string (no modification)
   - Example instruction includes concrete example ("Transformer 模型" not "变换器模型")

2. **Technical Term Whitelist**: Defined 40+ common ML/NLP terms to preserve in English
   - Stored as frozenset for immutability and O(1) lookup
   - Includes: Transformer, Attention, LSTM, Optimizer, etc.

3. **BilingualProcessor Design**: Minimal processing, trust LLM
   - EN mode: Pass through unchanged (early return)
   - ZH_EN mode: Hook for future validation, currently trusts LLM output
   - Preserves all DialogueScript metadata (speakers, section refs, persona)

4. **Test Coverage**: 7 tests covering:
   - Prompt modifier generation (ZH_EN and EN modes)
   - Technical term preservation
   - EN mode pass-through
   - Speaker order and metadata preservation
   - Edge case: lowercase technical terms

**Pattern Reuse:**
- Dataclass construction follows generator.py pattern
- Used LanguageMode enum from models.py
- Followed type hint conventions (Python 3.10+ with typing.Final)

**Integration Readiness:**
- Ready for dialogue generator to append bilingual_modifier to system prompts
- BilingualProcessor can be chained after DialogueScript generation
- No breaking changes to existing models

**Verification:**
- All 7 tests pass in 0.04s
- QA scenario validates prompt modifier contains Chinese and English references
- Evidence saved to .sisyphus/evidence/task-12-bilingual-prompt.txt

## Task 11: Audio Renderer Orchestrator

### Implementation Summary
- Created `AudioRenderer` class in `peripatos/voice/renderer.py`
- Implements TTS engine selection with OpenAI-first, edge-tts fallback strategy
- Routes voices based on speaker roles (HOST/EXPERT)
- Provides `add_silence_padding()` method for 300ms silence between turns
- Includes progress callback support for CLI integration

### Key Design Decisions
1. **Engine Selection Logic**: Checks `is_available()` on OpenAI engine first, falls back to edge-tts with warning log
2. **Separation of Concerns**: `render()` produces AudioSegment list, `add_silence_padding()` handles merging with silence
3. **Duration Calculation**: Uses pydub to calculate exact duration, with fallback estimation if ffprobe unavailable
4. **Voice Mapping**: Simple switch based on `SpeakerRole.HOST` vs `SpeakerRole.EXPERT`

### Testing Approach
- 7 tests covering all required scenarios (5+ requirement met)
- Tests verify engine selection, fallback, voice routing, silence padding, segment production, edge-tts mapping, and progress callbacks
- Extensive mocking of pydub and TTS engines to avoid external dependencies

### Technical Notes
- pydub requires ffmpeg/ffprobe for audio processing (optional in tests via mocking)
- edge-tts engine uses async internally but exposes `synthesize_sync()` wrapper
- OpenAI engine handles chunking internally for long texts

### QA Evidence
- Verified edge-tts fallback works when OPENAI_API_KEY is not set
- Evidence saved to `.sisyphus/evidence/task-11-fallback.txt`
- All 7 tests pass successfully

## Task 13: Audio Mixer with Chapter Markers

**Date:** 2026-02-19

### ffmpeg Chapter Metadata Format
- **FFMETADATA1 format structure:**
  - Header: `;FFMETADATA1` (semicolon prefix is critical)
  - Chapter sections: `[CHAPTER]` blocks with `TIMEBASE=1/1000`, `START`, `END`, `title` fields
  - Each chapter needs separate `[CHAPTER]` section
  - Millisecond timebase (1/1000) works well for audio precision
  - ffmpeg command: `ffmpeg -i input.mp3 -i metadata.txt -map_metadata 1 -codec copy output.mp3`
  - `-map_metadata 1` maps metadata from second input (index 1)
  - `-codec copy` preserves quality without re-encoding

### pydub Audio Concatenation Patterns
- **Loading audio from bytes:** `PydubAudioSegment.from_mp3(BytesIO(segment.audio_bytes))`
- **Creating silence:** `PydubAudioSegment.silent(duration=300)` (milliseconds)
- **Concatenation operator:** `audio1 + audio2` (returns new segment)
- **Duration calculation:** `len(audio)` returns milliseconds
- **Export pattern:** `audio.export(output_path, format='mp3')`
- **Chaining concatenations:** Silence and audio can be chained: `combined + silence + audio`

### Chapter Timing Calculation Approach
- **Track cumulative time:** Maintain running total of milliseconds as segments are concatenated
- **Account for silence:** Add silence duration to cumulative time between segments
- **Intro/outro silence:** Configurable padding at beginning and end of final audio
- **Chapter boundaries:** Align with section transitions for natural navigation points

### TDD Approach for Complex Integration
- **Write comprehensive mocks first:** Mock all external dependencies (pydub, subprocess, shutil)
- **Test edge cases early:** Empty segments, missing ffmpeg, invalid metadata
- **Verify format correctness:** Assert metadata file structure matches ffmpeg expectations
- **Mock operator overloading:** Need `__add__` support on Mock objects for concatenation tests
- **7 tests for thorough coverage:** Concatenation, metadata format, error handling, configuration

### Error Handling Pattern
- **Custom exception class:** `MixerError(Exception)` follows existing pattern from TTSError
- **Early validation:** Check inputs (empty segments) before expensive operations
- **Dependency checking:** Use `shutil.which('ffmpeg')` to detect missing tools
- **Helpful error messages:** Include installation instructions and visit URLs
- **Exception wrapping:** Wrap generic exceptions in MixerError with context

### Temporary File Management
- **Use tempfile.mkstemp():** Creates unique temp files with file descriptors
- **Same directory as output:** Create temp files in `output_path.parent` to avoid cross-device issues
- **Close file descriptors:** Always `os.close(temp_fd)` after mkstemp
- **Cleanup after success:** `unlink()` temp files after successful ffmpeg injection
- **Preserve on error:** Let exceptions propagate without cleanup for debugging

### Subprocess Integration
- **Use subprocess.run():** Modern API with `check=True`, `capture_output=True`, `text=True`
- **Error handling:** Catch `CalledProcessError` and extract stderr for debugging
- **Command building:** Build as list `['ffmpeg', '-i', str(path), ...]` not string
- **Path conversion:** Use `str(path)` for Path objects in subprocess commands
- **Debugging:** Log full command with `' '.join(cmd)` for reproducibility

### Testing with Real ffmpeg
- **QA scenario 1:** Create real audio with chapters, verify with ffprobe JSON output
- **QA scenario 2:** Mock ffmpeg unavailability, verify helpful error message
- **Evidence files:** Save QA results to `.sisyphus/evidence/` for verification
- **ffprobe validation:** Use `-print_format json -show_chapters` to extract chapter metadata
- **Chapter verification:** Check timebase, start/end times, and title fields in JSON output

