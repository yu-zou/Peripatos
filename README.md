# Peripatos Core

Convert academic papers into Socratic-dialogue podcasts.

## Installation

```bash
pip install peripatos-core
```

## Quick Start

```bash
# Convert an ArXiv paper
peripatos convert 1706.03762 --config ~/.config/peripatos/config.json

# Convert a local PDF
peripatos convert path/to/paper.pdf --config ~/.config/peripatos/config.json

# Check configuration
peripatos doctor --config ~/.config/peripatos/config.json
```

## Configuration

Copy `config.example.json` to `~/.config/peripatos/config.json` and fill in your API key:

```json
{
  "llm": {
    "base_url": "https://router.requesty.ai/v1",
    "api_key": "YOUR_KEY_HERE",
    "model": "openai/gpt-4o-mini"
  },
  "tts": {
    "provider": "edge"
  }
}
```

## Running Tests

```bash
docker compose run --rm test pytest -v
```

## License

MIT — see [LICENSE](LICENSE).
