<p align="center">
  <img src="docs/logo.png" alt="Peripatos" width="180" />
</p>

<h1 align="center">Peripatos</h1>

<p align="center">
  Turn any academic paper into a Socratic-dialogue podcast — in one command.
</p>

---

Peripatos fetches an ArXiv paper (or any PDF/HTML/Markdown), generates a natural back-and-forth dialogue between two speakers using an LLM, and synthesises the script into an MP3 with ID3v2.4 chapter markers — one chapter per dialogue turn.

PDF parsing uses [MinerU](https://mineru.net)'s cloud API for high-quality extraction (tables, formulas, headings) with a built-in PyMuPDF fallback — no heavy ML dependencies required.

## Installation

```bash
pip install git+https://github.com/yu-zou/Peripatos.git
```

## Configuration

Peripatos is configured via a single JSON file. Create a config file anywhere (e.g. `~/my-peripatos.json`) using the example below, fill in your API key, then point Peripatos to it.

Configuration is resolved in this order:
1. `--config PATH` flag
2. `~/.config/peripatos/config.json`
3. Built-in defaults

### Default configuration

```json
{
  "$schema": "https://raw.githubusercontent.com/yu-zou/Peripatos/main/schema/config.schema.json",
  "archetype": "peer",
  "output_dir": ".",
  "language": "en",
  "llm": {
    "base_url": "https://router.requesty.ai/v1",
    "api_key": "",
    "model": "openai/gpt-4o-mini"
  },
  "tts": {
    "provider": "edge",
    "base_url": "",
    "api_key": "",
    "voice": "en-US-AriaNeural",
    "voices": {
      "host": "en-US-GuyNeural",
      "interviewee": "en-US-AriaNeural"
    },
    "model": "tts-1"
  },
  "rag": {
    "embedding_model": "openai/text-embedding-3-small",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "top_k": 5,
    "cache_dir": null
  },
  "parser": {
    "mineru_token": ""
  },
  "cache": {
    "audio": true,
    "dialogue": true,
    "dir": null
  }
}
```

### Example (Edge TTS)

```json
{
  "$schema": "https://raw.githubusercontent.com/yu-zou/Peripatos/main/schema/config.schema.json",
  "llm": {
    "base_url": "https://router.requesty.ai/v1",
    "api_key": "YOUR_API_KEY",
    "model": "openai/gpt-4o-mini"
  },
  "tts": {
    "provider": "edge",
    "voice": "en-US-AriaNeural",
    "voices": {
      "host": "en-US-GuyNeural",
      "interviewee": "en-US-AriaNeural"
    }
  },
  "parser": {
    "mineru_token": "YOUR_MINERU_TOKEN"
  }
}
```

### Example (ElevenLabs)

```json
{
  "$schema": "https://raw.githubusercontent.com/yu-zou/Peripatos/main/schema/config.schema.json",
  "llm": {
    "base_url": "https://router.requesty.ai/v1",
    "api_key": "YOUR_API_KEY",
    "model": "openai/gpt-4o-mini"
  },
  "tts": {
    "provider": "elevenlabs",
    "api_key": "YOUR_ELEVENLABS_API_KEY"
  },
  "parser": {
    "mineru_token": "YOUR_MINERU_TOKEN"
  }
}
```

The `tts.provider` defaults to `"edge"` (Microsoft Edge TTS — no API key required). Set it to `"openai_compatible"` to use any OpenAI-compatible TTS endpoint, or `"elevenlabs"` for high-quality ElevenLabs voices.

The `llm.base_url` accepts any OpenAI-compatible endpoint: [Requesty](https://requesty.ai), [OpenRouter](https://openrouter.ai), or vanilla OpenAI.

### Parser Configuration

Peripatos parses PDFs using [MinerU](https://mineru.net)'s cloud API for high-quality extraction (tables, formulas, headings). If the API is unavailable, it falls back to [PyMuPDF](https://pymupdf.readthedocs.io/) for text-only extraction — no heavy ML dependencies required.

| Key | Default | Description |
|---|---|---|
| `parser.mineru_token` | `""` | MinerU API token from [mineru.net/apiManage/token](https://mineru.net/apiManage/token). Leave empty for Flash extract (free, no auth, ≤20 pages, ≤10MB). Set a token for Precision extract (≤600 pages, ≤200MB, tables/formulas). Falls back to PyMuPDF if MinerU is unavailable. |

Without a token, Peripatos uses MinerU's free Flash mode for fast extraction. With a token, Precision mode provides full-featured extraction (tables, formulas, structured headings). For longer papers, get a free token at <https://mineru.net/apiManage/token> and add it to your config.

### Reference

| Key | Default | Description |
|---|---|---|
| `archetype` | `"peer"` | Dialogue style: `peer`, `skeptic`, `tutor`, or `enthusiast`. |
| `output_dir` | `"."` | Directory for output files. |
| `language` | `"en"` | Dialogue language: `en` (English) or `zh-CN` (Mandarin Chinese). |
| `tts.provider` | `"edge"` | TTS backend: `edge` (free, no API key), `openai_compatible`, or `elevenlabs`. |
| `tts.api_key` | `""` | API key for `openai_compatible` or `elevenlabs` providers. Required for those. |
| `tts.voice` | `"en-US-AriaNeural"` (edge) / `"nova"` (openai_compatible) | Single voice for both speakers. (deprecated) |
| `tts.voices.host` | `"en-US-GuyNeural"` (edge) / `"onyx"` (openai_compatible) | Voice for the host speaker. |
| `tts.voices.interviewee` | `"en-US-AriaNeural"` (edge) / `"nova"` (openai_compatible) | Voice for the interviewee speaker. |
| `parser.mineru_token` | `""` | MinerU API token. Empty = Flash mode (free, ≤20 pages). Set token for Precision mode (≤600 pages). |
| `cache.audio` | `true` | Cache per-turn synthesized audio (keyed by text + voice + provider). |
| `cache.dialogue` | `true` | Cache generated dialogue scripts (keyed by model + archetype + language + paper content). |
| `cache.dir` | `null` | Cache directory. Defaults to `~/.cache/peripatos/`. |

### RAG Configuration

| Key | Default | Description |
|---|---|---|
| `rag.provider` | `"openai_compatible"` | Embedding backend: `"openai_compatible"` for API-based, `"local"` for `sentence-transformers` models. |
| `rag.embedding_model` | `"openai/text-embedding-3-small"` | Model name. For local: HuggingFace path (e.g., `"BAAI/bge-m3"`). For remote: API model identifier. |
| `rag.chunk_size` | `1000` | Size of text chunks for indexing (characters). |
| `rag.chunk_overlap` | `200` | Overlap between adjacent chunks (characters). |
| `rag.top_k` | `5` | Number of chunks to retrieve for each search query. |
| `rag.cache_dir` | `null` | Directory to store FAISS indices. Defaults to `~/.cache/peripatos/rag/`. |

**Deprecated**: `tts.voice` (single voice for both speakers) still works but emits a deprecation warning. Use `tts.voices.host` and `tts.voices.interviewee` instead.

### ElevenLabs TTS Configuration

When `tts.provider` is set to `"elevenlabs"`, Peripatos uses curated pre-made voices from the ElevenLabs library with automatic gender-balanced selection:

- **Host voices**: Warm, conversational podcast voices (male and female options)
- **Interviewee voices**: Articulate, authoritative expert voices (male and female options)
- **Gender enforcement**: The host and interviewee voices are always opposite genders for clear speaker distinction
- **Random selection**: Each run randomly selects from the voice pool, so you get variety across runs

To use specific ElevenLabs voice IDs instead of random selection, explicitly set `tts.voices.host` and `tts.voices.interviewee` in your config — these take precedence over random selection.

Requires `tts.api_key` set to your ElevenLabs API key from [elevenlabs.io](https://elevenlabs.io).

### Caching Configuration

Peripatos caches intermediate results to avoid redundant API calls and TTS synthesis on re-runs:

| Feature | Cache Location | Cache Key |
|---------|---------------|-----------|
| Audio (per-turn) | `~/.cache/peripatos/audio/` | SHA-256 of `(provider + voice_id + text)` |
| Dialogue (per-script) | `~/.cache/peripatos/dialogue/` | SHA-256 of `(llm_model + archetype + language + paper_content)` |

Both caches are enabled by default. To disable, set `cache.audio` or `cache.dialogue` to `false` in your config. To clear the cache, delete the cache directory.

### Logging

Peripatos outputs structured logs to stderr at INFO level, showing:
- Progress of each pipeline phase (fetching, parsing, dialogue generation, audio synthesis)
- Timing measurements for each step (e.g., "PDF parsing completed in 3.2s")
- Cache hit/miss status for audio and dialogue caching
- Voice selection decisions

Logging is always enabled — no configuration needed. Log output goes to stderr so it doesn't interfere with stdout data output.

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
14:23:04 [INFO] peripatos_core.registry: ElevenLabs voices (random): host=pNInz6obpgDQGcFmaJgB (male), interviewee=EXAVITQu4vr4xnSDxMaL (female)
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

Each timing line shows the elapsed time for that phase. Cache hits show which turn was retrieved from cache. Voice selection shows which voices were randomly assigned for ElevenLabs.

## Quick Start

```bash
# ArXiv ID
peripatos generate 1706.03762

# ArXiv URL
peripatos generate https://arxiv.org/abs/2303.08774

# Local PDF
peripatos generate ./paper.pdf --output podcast.mp3

# Choose an archetype
peripatos generate 1706.03762 --archetype tutor --output lecture.mp3

# HTML URL
peripatos generate https://example.com/article.html -o podcast.mp3

# Markdown or Text files
peripatos generate ./notes.md -o podcast.mp3
peripatos generate ./transcript.txt -o podcast.mp3
```

## CLI Reference

### `peripatos generate <source>`

| Flag | Short | Description |
|---|---|---|
| `--output` | `-o` | Output MP3 path (default: `output.mp3`) |
| `--archetype` | `-a` | Dialogue style (default: `peer`) |
| `--config` | `-c` | Path to a JSON config file |

### `peripatos list-archetypes`

Print all available archetypes with descriptions.

### `peripatos doctor`

Print diagnostic info for the resolved configuration (accepts `--config` to target a specific file, otherwise reads `~/.config/peripatos/config.json`).

## Archetypes

| Name | Style |
|---|---|
| `peer` | A curious peer interviewing an expert — accessible, conversational |
| `skeptic` | A sceptical host challenges the paper's claims — critical, rigorous |
| `tutor` | An expert guides a student through the concepts — pedagogical, patient |
| `enthusiast` | Two enthusiasts geek out over the findings — energetic, exploratory |

## Output

The generated MP3 embeds ID3v2.4 metadata:

- **Chapter markers** (`CHAP` / `CTOC`) — one per dialogue turn; skip between speakers in any chapter-aware player
- **Title & artist** — extracted from the paper

## Contributing

### Development Setup

```bash
git clone https://github.com/yu-zou/Peripatos.git
cd Peripatos
pip install -e .
```

### Running Tests

All tests run inside Docker:

```bash
# Unit tests (mocked providers)
docker compose run --rm test pytest -v

# Integration tests (requires real API keys in config)
RUN_INTEGRATION=1 docker compose run --rm test pytest -v -m integration

# Real-LLM end-to-end test (requires Peripatos/config.test.json with API key)
# Fetches arxiv 2303.08774, runs the full pipeline against a real LLM, and verifies the output MP3 contains ID3 chapter markers.
RUN_INTEGRATION=1 docker compose run --rm test pytest -v tests/test_e2e.py

# Python 3.14 wheel-install smoke test (optional, requires Docker)
docker compose run --rm install-test
```

Builds a wheel from source, installs it into a fresh Python 3.14 environment, and verifies `peripatos --help`, `list-archetypes`, and provider imports all work correctly.

## License

[MIT](LICENSE)
