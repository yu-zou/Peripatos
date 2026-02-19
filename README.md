# Peripatos — Deep Learning while Moving

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Peripatos transforms dense research papers into engaging Socratic audio dialogues, allowing researchers and students to stay current while commuting, walking, or exercising. By leveraging advanced LLMs and high-quality TTS, it converts technical content from ArXiv IDs or local PDFs into natural conversations between a host and a guest, tailored to your chosen persona and language preference.

## Quick Start

### Installation

Requires Python 3.10+ and `ffmpeg`.

```bash
# Install the package
pip install -e .

# Ensure ffmpeg is installed (macOS example)
brew install ffmpeg
```

### Basic Usage

Generate a dialogue from an ArXiv ID:
```bash
peripatos generate 2408.09869
```

Or from a local PDF:
```bash
peripatos generate ./papers/attention.pdf --persona tutor --language zh-en
```

## Configuration

Configure your API keys by creating a `.env` file in the project root:

```bash
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-your-key-here
```

Default settings can be managed in `~/.peripatos/config.yaml`. The system follows a priority chain: defaults -> YAML config -> environment variables -> CLI overrides.

## Persona Modes

Choose an archetype that fits your learning goal:

*   **Skeptic**: A critical thinker who challenges assumptions and asks "Why?" Best for papers with controversial claims.
*   **Enthusiast**: An excited explorer who highlights breakthroughs and potential impact. Perfect for novel methods.
*   **Tutor**: A patient teacher explaining concepts step-by-step. Ideal for learning unfamiliar topics.
*   **Peer**: A collaborative discussant exploring the paper together. Great for casual learning of familiar topics.

## Bilingual Mode

Enable `zh-en` mode to use Chinese for explanations while preserving English technical terms. This reduces mental translation fatigue for non-native speakers while maintaining professional terminology accuracy.

Example: "Transformer 模型使用 self-attention 机制" (not "变换器模型").

## CLI Reference

```text
usage: peripatos generate [-h] [--persona {enthusiast,peer,skeptic,tutor}]
                          [--language {en,zh-en}]
                          [--tts-engine {edge-tts,openai}]
                          [--output-dir OUTPUT_DIR]
                          [--llm-provider {anthropic,openai}]
                          [--llm-model LLM_MODEL] [--verbose]
                          source

positional arguments:
  source                ArXiv ID or local PDF path

options:
  -h, --help            show this help message and exit
  --persona {enthusiast,peer,skeptic,tutor}
  --language {en,zh-en}
  --tts-engine {edge-tts,openai}
  --output-dir OUTPUT_DIR
  --llm-provider {anthropic,openai}
  --llm-model LLM_MODEL
  --verbose, -v
```

## Requirements

*   Python 3.10 or higher
*   `ffmpeg` for audio processing and chapter injection
*   API keys for OpenAI or Anthropic

## Development

Install development dependencies and run tests:

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Acknowledgments

*   **Docling**: For robust PDF document parsing.
*   **OpenAI**: For GPT-4 dialogue generation and high-fidelity TTS.
*   **edge-tts**: For high-quality fallback speech synthesis.
