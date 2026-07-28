<p align="center">
  <img src="docs/logo.png" alt="Peripatos" width="180" />
</p>

<h1 align="center">Peripatos</h1>

<p align="center">
  Turn any academic paper into a Socratic-dialogue podcast — in one command.
</p>

---

Peripatos fetches an ArXiv paper (or any PDF/HTML/Markdown), generates a natural
back-and-forth dialogue between two speakers using an LLM, and synthesises the
script into an MP3 with ID3v2.4 chapter markers — one chapter per dialogue turn.

PDF parsing uses [MinerU](https://mineru.net)'s cloud API for high-quality
extraction (tables, formulas, headings) with a built-in PyMuPDF fallback — no
heavy ML dependencies required.

## Features

### 🎭 Archetype-based dialogue generation

Choose the tone of your podcast. Each archetype defines a unique speaker dynamic
and conversation style:

| Archetype | Style |
|-----------|-------|
| `peer` | A curious peer interviewing an expert — accessible, conversational |
| `skeptic` | A sceptical host challenges the paper's claims — critical, rigorous |
| `tutor` | An expert guides a student through the concepts — pedagogical, patient |
| `enthusiast` | Two enthusiasts geek out over the findings — energetic, exploratory |

### 🔑 Bring Your Own Key (BYOK)

Peripatos works with any OpenAI-compatible LLM endpoint — use
[Requesty](https://requesty.ai), [OpenRouter](https://openrouter.ai), or vanilla
OpenAI. TTS providers include free Microsoft Edge TTS (no API key needed),
OpenAI-compatible endpoints, or [ElevenLabs](https://elevenlabs.io) for
high-quality voices.

## Installation

```bash
pip install git+https://github.com/yu-zou/Peripatos.git
```

## Configuration

Peripatos is configured via a single JSON file. Create a config file anywhere
(e.g. `~/my-peripatos.json`), fill in your API key, then point Peripatos to it.

Configuration is resolved in this order:

1. `--config PATH` flag
2. `~/.config/peripatos/config.json`
3. Built-in defaults

### Default configuration

See [`examples/config.default.json`](examples/config.default.json) for the full
default configuration with all keys.

### Example configurations

- [Edge TTS (free, no API key)](examples/config.edge.json)
- [ElevenLabs (high-quality voices)](examples/config.elevenlabs.json)

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

## Reference

See the [full reference](docs/reference.md) for detailed documentation on:

- All configuration keys (LLM, TTS, Parser, RAG, Cache)
- ElevenLabs TTS configuration
- Caching behaviour
- Logging format

## CLI Reference

See the [CLI reference](docs/cli.md) for detailed usage of all commands:

- `peripatos generate <source>` — convert a paper into a podcast MP3
- `peripatos list-archetypes` — print all available archetypes
- `peripatos doctor` — print diagnostic config info

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, running tests, and
pull request guidelines.

## License

[MIT](LICENSE)