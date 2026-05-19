# Peripatos Core

Peripatos converts academic papers into engaging Socratic-dialogue MP3 podcasts. It parses PDF content, uses LLMs to generate a natural dialogue between a host and a guest, and synthesizes the script into audio with ID3v2.4 chapter markers for each dialogue turn.

## Installation

Install the package via pip:

```bash
pip install peripatos-core
```

For development, clone the repository and install in editable mode:

```bash
git clone https://github.com/yzou/Peripatos.git
cd Peripatos
pip install -e .
```

## Configuration

Peripatos requires a configuration file for LLM access. Copy the example configuration to your local config directory:

```bash
mkdir -p ~/.config/peripatos
cp config.example.json ~/.config/peripatos/config.json
```

### Configuration Resolution

Peripatos looks for configuration in the following order:
1. Explicit path provided via the `--config` (or `-c`) flag.
2. `~/.config/peripatos/config.json`
3. Internal defaults.

### Example Configuration

```json
{
  "llm": {
    "base_url": "https://router.requesty.ai/v1",
    "api_key": "YOUR_REQUESTY_API_KEY_HERE",
    "model": "openai/gpt-4o-mini"
  },
  "tts": {
    "provider": "edge",
    "voice": "en-US-AriaNeural"
  },
  "defaults": {
    "archetype": "proxy_host",
    "output_dir": "."
  }
}
```

By default, the system uses `edge-tts` which works without an API key.

## Quick Start

Convert a paper using various source formats:

```bash
# Using an ArXiv ID
peripatos generate 1706.03762

# Using an ArXiv URL
peripatos generate https://arxiv.org/abs/2303.08774

# Using a local PDF file
peripatos generate ./papers/attention_is_all_you_need.pdf
```

## CLI Reference

### `peripatos generate`
Convert a paper to a Socratic-dialogue MP3.
- `source`: ArXiv ID, ArXiv URL, PDF URL, or local PDF path.
- `--output`, `-o`: Output MP3 file path (default: `output.mp3`).
- `--archetype`, `-a`: Dialogue archetype to use (default: `proxy_host`).
- `--config`, `-c`: Path to a specific JSON config file.

### `peripatos list-archetypes`
List all available dialogue archetypes.

### `peripatos doctor`
Check the current configuration and print diagnostic information to verify API keys and provider settings.

## Archetypes

Archetypes define the tone and structure of the generated dialogue:

- `proxy_host`: A curious host interviewing an expert guest who simplifies the paper's concepts.
- `author_persona`: The host interviews the "author" of the paper about their motivations and findings.
- `devils_advocate`: A skeptical host challenges the paper's claims, forcing a defensive but informative guest response.
- `domain_expert`: A high-level technical discussion between two experts in the field.

## Output Format

The output is a high-quality MP3 file. Peripatos embeds ID3v2.4 metadata including:
- **Chapter Markers**: Each dialogue turn is marked as a chapter, allowing you to skip between speakers in supported players.
- **Title/Artist**: Metadata extracted from the paper and archetype settings.

## Running Tests

Peripatos uses Docker for isolated testing.

```bash
# Run unit tests
docker compose run --rm test pytest -v

# Run integration tests (requires valid config/API keys)
RUN_INTEGRATION=1 docker compose run --rm test pytest -v -m integration
```

## License

MIT
