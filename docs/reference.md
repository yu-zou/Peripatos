# Reference

## Configuration

### Resolution order

Configuration is resolved in this order:

1. `--config PATH` flag
2. `~/.config/peripatos/config.json`
3. Built-in defaults

### Top-level keys

| Key | Default | Description |
|-----|---------|-------------|
| `archetype` | `"peer"` | Dialogue style: `peer`, `skeptic`, `tutor`, or `enthusiast`. |
| `output_dir` | `"."` | Directory for output files. |
| `language` | `"en"` | Dialogue language: `en` (English) or `zh-CN` (Mandarin Chinese). |

### LLM

| Key | Default | Description |
|-----|---------|-------------|
| `llm.base_url` | `"https://router.requesty.ai/v1"` | OpenAI-compatible API endpoint. |
| `llm.api_key` | `""` | API key for the LLM provider. |
| `llm.model` | `"openai/gpt-4o-mini"` | Model identifier. |

### TTS

| Key | Default | Description |
|-----|---------|-------------|
| `tts.provider` | `"edge"` | TTS backend: `edge` (free, no API key), `openai_compatible`, or `elevenlabs`. |
| `tts.api_key` | `""` | API key for `openai_compatible` or `elevenlabs` providers. |
| `tts.voice` | `"en-US-AriaNeural"` (edge) / `"nova"` (openai_compatible) | **Deprecated**: single voice for both speakers. Use `voices.host` and `voices.interviewee`. |
| `tts.voices.host` | `"en-US-GuyNeural"` (edge) / `"onyx"` (openai_compatible) / `"pNInz6obpgDQGcFmaJgB"` (elevenlabs) | Voice for the host speaker. |
| `tts.voices.interviewee` | `"en-US-AriaNeural"` (edge) / `"nova"` (openai_compatible) / `"EXAVITQu4vr4xnSDxMaL"` (elevenlabs) | Voice for the interviewee speaker. |
| `tts.model` | `"tts-1"` | Model identifier for `openai_compatible` provider. |

### Parser

| Key | Default | Description |
|-----|---------|-------------|
| `parser.mineru_token` | `""` | MinerU API token. Empty = Flash mode (free, ≤20 pages). Set token for Precision mode (≤600 pages, tables/formulas). Falls back to PyMuPDF if MinerU is unavailable. |

### RAG

| Key | Default | Description |
|-----|---------|-------------|
| `rag.provider` | `"openai_compatible"` | Embedding backend: `"openai_compatible"` or `"local"`. |
| `rag.embedding_model` | `"openai/text-embedding-3-small"` | Model name. For local: HuggingFace path (e.g., `"BAAI/bge-m3"`). |
| `rag.chunk_size` | `1000` | Size of text chunks for indexing (characters). |
| `rag.chunk_overlap` | `200` | Overlap between adjacent chunks (characters). |
| `rag.top_k` | `5` | Number of chunks to retrieve for each search query. |
| `rag.cache_dir` | `null` | Directory to store FAISS indices. Defaults to `~/.cache/peripatos/rag/`. |

### Cache

| Key | Default | Description |
|-----|---------|-------------|
| `cache.audio` | `true` | Cache per-turn synthesized audio (keyed by text + voice + provider). |
| `cache.dialogue` | `true` | Cache generated dialogue scripts (keyed by model + archetype + language + paper content). |
| `cache.dir` | `null` | Cache directory. Defaults to `~/.cache/peripatos/`. |

### Parser Configuration

Peripatos parses PDFs using [MinerU](https://mineru.net)'s cloud API for
high-quality extraction (tables, formulas, headings). If the API is unavailable,
it falls back to [PyMuPDF](https://pymupdf.readthedocs.io/) for text-only
extraction — no heavy ML dependencies required.

Without a token, Peripatos uses MinerU's free Flash mode for fast extraction.
With a token, Precision mode provides full-featured extraction (tables,
formulas, structured headings). For longer papers, get a free token at
<https://mineru.net/apiManage/token> and add it to your config.

## ElevenLabs TTS

When `tts.provider` is set to `"elevenlabs"`, Peripatos uses curated pre-made
voices from the ElevenLabs library with automatic gender-balanced selection:

- **Host voices**: Warm, conversational podcast voices (male and female options)
- **Interviewee voices**: Articulate, authoritative expert voices (male and female options)
- **Gender enforcement**: The host and interviewee voices are always opposite genders for clear speaker distinction
- **Random selection**: Each run randomly selects from the voice pool, so you get variety across runs

To use specific ElevenLabs voice IDs instead of random selection, explicitly set
`tts.voices.host` and `tts.voices.interviewee` in your config. You can set both
voices, or just one — the unspecified voice will be randomly selected from the
opposite gender's pool. Valid ElevenLabs voice IDs can be found in your
[ElevenLabs voice library](https://elevenlabs.io/app/voice-library).

Requires `tts.api_key` set to your ElevenLabs API key from
[elevenlabs.io](https://elevenlabs.io).

## Caching

Peripatos caches intermediate results to avoid redundant API calls and TTS
synthesis on re-runs:

| Feature | Cache Location | Cache Key |
|---------|---------------|-----------|
| Audio (per-turn) | `~/.cache/peripatos/audio/` | SHA-256 of `(provider + voice_id + text)` |
| Dialogue (per-script) | `~/.cache/peripatos/dialogue/` | SHA-256 of `(llm_model + archetype + language + paper_content)` |

Both caches are enabled by default. To disable, set `cache.audio` or
`cache.dialogue` to `false` in your config. To clear the cache, delete the
cache directory.

## Logging

Peripatos outputs structured logs to stderr at INFO level, showing:

- Progress of each pipeline phase (fetching, parsing, dialogue generation, audio synthesis)
- Timing measurements for each step
- Cache hit/miss status for audio and dialogue caching
- Voice selection decisions

Logging is always enabled — no configuration needed. Log output goes to stderr
so it doesn't interfere with stdout data output.

**Log format:**

```
HH:MM:SS [LEVEL] module: message
```

**Example output:**

```
14:23:01 [INFO] peripatos_core.cli: Loading settings completed in 0.02s
14:23:01 [INFO] peripatos_core.cli: Fetching paper completed in 1.3s
14:23:04 [INFO] peripatos_core.parser: PDF parsing completed in 2.8s
14:23:04 [INFO] peripatos_core.dialogue: Dialogue cache check completed in 0.01s
14:23:04 [INFO] peripatos_core.dialogue: Dialogue cache miss — generating new script
14:23:04 [INFO] peripatos_core.registry: ElevenLabs voices (random): host=... (male), interviewee=... (female)
14:23:05 [INFO] peripatos_core.dialogue: Phase 0 (Intro) completed in 1.2s
14:23:07 [INFO] peripatos_core.dialogue: Phase A (Chapters) completed in 2.1s
14:23:07 [INFO] peripatos_core.dialogue: RAG setup completed in 0.8s
14:23:25 [INFO] peripatos_core.dialogue: Phase B (Agent) completed in 17.4s
14:23:26 [INFO] peripatos_core.dialogue: Phase C (Post-processing) completed in 1.5s
14:23:27 [INFO] peripatos_core.dialogue: Phase 4 (Outro) completed in 0.9s
14:23:27 [INFO] peripatos_core.dialogue: Dialogue generation completed in 23.9s
14:23:27 [INFO] peripatos_core.cli: Building TTS provider completed in 0.01s
14:23:28 [INFO] peripatos_core.cache: Audio cache hit: Host (142 chars)
14:23:28 [INFO] peripatos_core.audio: Synthesized turn (Guest, 218 chars) in 1.6s
14:23:30 [INFO] peripatos_core.audio: Synthesized turn (Host, 98 chars) in 1.1s
...
14:24:15 [INFO] peripatos_core.audio: Write MP3 completed in 1.9s
14:24:15 [INFO] peripatos_core.audio: Audio rendering completed in 47.3s
14:24:15 [INFO] peripatos_core.cli: Total pipeline completed in 73.5s
```

## Schema

The canonical JSON Schema is at
[`schema/config.schema.json`](schema/config.schema.json) and is published at:

```
https://raw.githubusercontent.com/yu-zou/Peripatos/main/schema/config.schema.json
```

Add `"$schema"` to your config file for LSP autocomplete and validation in
editors that support JSON Schema.