<p align="center">
  <img src="docs/logo.png" alt="Peripatos" width="180" />
</p>

<h1 align="center">Peripatos</h1>

<p align="center">
  Turn any academic paper into a Socratic-dialogue podcast — in one command.
</p>

---

Peripatos fetches an ArXiv paper (or any PDF), generates a natural back-and-forth dialogue between two speakers using an LLM, and synthesises the script into an MP3 with ID3v2.4 chapter markers — one chapter per dialogue turn.

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
  "defaults": {
    "archetype": "peer",
    "output_dir": "."
  },
  "rag": {
    "embedding_model": "openai/text-embedding-3-small",
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "top_k": 5,
    "cache_dir": null
  }
}
```

### Example

```json
{
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
  "defaults": {
    "archetype": "peer"
  }
}
```

The `tts.provider` defaults to `"edge"` (Microsoft Edge TTS — no API key required). Set it to `"openai"` to use any OpenAI-compatible TTS endpoint instead.

The `llm.base_url` accepts any OpenAI-compatible endpoint: [Requesty](https://requesty.ai), [OpenRouter](https://openrouter.ai), or vanilla OpenAI.

### Reference

| Key | Default | Description |
|---|---|---|
| `tts.voice` | `"en-US-AriaNeural"` (edge) / `"nova"` (openai_compatible) | Single voice for both speakers. (deprecated) |
| `tts.voices.host` | `"en-US-GuyNeural"` (edge) / `"onyx"` (openai_compatible) | Voice for the host speaker. |
| `tts.voices.interviewee` | `"en-US-AriaNeural"` (edge) / `"nova"` (openai_compatible) | Voice for the interviewee speaker. |

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
