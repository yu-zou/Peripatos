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

