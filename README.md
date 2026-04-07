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
OPENROUTER_API_KEY=your-key-here
GEMINI_API_KEY=your-key-here
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

## TTS Engine Setup

Peripatos supports two high-quality text-to-speech engines for generating dialogue audio. Configure your preferred engine using the `--tts-engine` CLI flag or the `~/.peripatos/config.yaml` file.

### Engine Selection

Use the `--tts-engine {edge-tts,openai}` CLI flag to select your engine. Default: `openai` (if `OPENAI_API_KEY` is configured).

### OpenAI TTS

OpenAI's TTS service delivers natural-sounding audio with minimal latency. Requires an API key.

*   **Setup**: Set `OPENAI_API_KEY` environment variable (get your key from https://platform.openai.com/account/api-keys)
*   **Model**: Uses `tts-1` by default (optimized for speed and low latency). Higher-quality `tts-1-hd` model is available but not currently user-configurable in Peripatos.
*   **Configuration**:
    ```yaml
    tts:
      engine: openai
      voice_host: alloy      # voice for the host speaker
      voice_expert: onyx     # voice for the expert/guest speaker
    ```

### edge-tts (Microsoft Azure Neural TTS)

Free, high-quality speech synthesis powered by Microsoft Azure. No API key required.

*   **Setup**: No configuration needed—edge-tts is automatically available as a fallback.
*   **Configuration**:
    ```yaml
    tts:
      engine: edge-tts
      voice_host: en-US-AriaNeural
      voice_expert: en-US-GuyNeural
    ```

### Automatic Fallback

If you configure `engine: openai` but `OPENAI_API_KEY` is not set, Peripatos automatically falls back to edge-tts with a warning. This ensures audio generation never fails due to missing credentials.

### Voice Configuration

Voice settings are managed in `~/.peripatos/config.yaml` under the `tts` section (not via CLI flags). Voice names are **engine-specific**:

*   **OpenAI**: Short names (e.g., `alloy`, `nova`, `shimmer`)
*   **edge-tts**: Microsoft Neural voice IDs (e.g., `en-US-AriaNeural`, `zh-CN-XiaoxiaoNeural`)

When switching TTS engines, update your voice configuration to use valid names for the new engine.

## Recommended Settings

### OpenAI TTS Voices

The default voices (`alloy` for host, `onyx` for expert) are production-tested and reliable. Available voices:

| Voice | Character | Best For |
|-------|-----------|----------|
| alloy | Neutral, professional | Default host voice |
| onyx | Deep, authoritative | Default expert voice |
| nova | Warm, bright | Friendly discussions |
| shimmer | High-pitched, energetic | Enthusiastic personas |
| ash | Calm, measured | Technical deep-dives |
| sage | Thoughtful, deliberate | Skeptical personas |
| echo | Resonant, confident | Tutor persona |
| coral | Soft, conversational | Peer persona |
| fable | Expressive, engaging | Narrative content |
| ballad | Melodic, smooth | Long-form audio |
| verse | Dynamic, varied | Varied tone dialogues |
| cedar | Rich, authoritative | **Recommended for quality** |
| marin | Polished, natural | **Recommended for quality** |

For best audio quality, try `cedar` (host) and `marin` (expert). Full voice guide: https://platform.openai.com/docs/guides/text-to-speech#voice-options

### edge-tts Voices

edge-tts uses Microsoft's extensive neural voice library. Default English voices: `en-US-AriaNeural` (host), `en-US-GuyNeural` (expert).

**Recommended English voice pairs** (all professional-grade):

*   **AriaNeural + GuyNeural** — Professional, confident. Default pair. Best for academic content.
*   **JennyNeural + AndrewMultilingualNeural** — Warm, conversational. Great for exploratory discussions.
*   **EmmaMultilingualNeural + ChristopherNeural** — Clear, authoritative. Excellent for technical explanations.

To browse all 300+ voices and hear samples: `edge-tts --list-voices` or visit https://speech.microsoft.com/portal/voicegallery

### Chinese Voices (Bilingual Mode)

When using `--language zh-en` with edge-tts, Peripatos automatically selects:

*   **Host**: `zh-CN-XiaoxiaoNeural` — Natural, engaging Mandarin
*   **Expert**: `zh-CN-YunxiNeural` — Clear, authoritative Mandarin

### TTS Model Comparison

| Aspect | OpenAI tts-1 | OpenAI tts-1-hd | edge-tts |
|--------|--------------|-----------------|----------|
| Quality | Good | Excellent | Good |
| Latency | Fast | Slower | Fast |
| Cost | Paid | Paid (higher) | Free |
| API Key Required | Yes | Yes | No |
| Voice Options | ~13 | ~13 | 300+ |
| Multilingual | Limited | Limited | Extensive |

OpenAI's `tts-1` is recommended for speed and reliability. Use `tts-1-hd` if audio quality is critical (not user-configurable in Peripatos currently). edge-tts is ideal for free, multilingual content.

## VLM Enhanced Parsing (Experimental)

Peripatos includes optional support for **Granite Docling VLM** (Vision-Language Model) to enhance PDF parsing accuracy, particularly for complex documents with tables, equations, and figures.

### Installation

```bash
pip install peripatos[vlm]
```

This installs additional dependencies: `torch`, `transformers`, and `mlx-vlm` (on Apple Silicon).

### Usage

Enable VLM parsing with the `--vlm` flag:

```bash
peripatos generate 2408.09869 --vlm
peripatos generate ./papers/attention.pdf --vlm
```

### Current Status: Performance-Limited

**⚠️ Experimental Feature:** VLM parsing is currently **not viable for production use** due to performance constraints.

**Benchmark Results** (Apple Silicon MLX, M-series chip):
- **Base Docling**: ~6.4 seconds per page
- **VLM MLX**: ~72.9 seconds per page (11.4× slower)
- **Bottleneck**: Model inference time exceeds practical thresholds for multi-page documents

**Hardware Requirements:**
- **Apple Silicon (MLX)**: Preferred, but still slow (~72.9s/page)
- **CUDA GPUs**: Possible alternative (not benchmarked)
- **CPU-only**: Extremely slow (>10 minutes/page) — not recommended

### When to Use VLM

Consider VLM for:
- Single-page documents or short papers (< 5 pages)
- Documents where base Docling extraction is insufficient
- Experimental workflows where quality trumps speed

**Recommendation:** Wait for performance improvements before using VLM in production workflows. See `.sisyphus/evidence/task-7-investigation.txt` for detailed performance analysis.

## CLI Reference

```text
usage: peripatos generate [-h] [--persona {enthusiast,peer,skeptic,tutor}]
                          [--language {en,zh-en}]
                          [--tts-engine {edge-tts,openai}]
                          [--output-dir OUTPUT_DIR]
                          [--llm-provider {anthropic,gemini,openai,openrouter}]
                          [--llm-model LLM_MODEL] [--vlm] [--verbose]
                          source

positional arguments:
  source                ArXiv ID or local PDF path

options:
  -h, --help            show this help message and exit
  --persona {enthusiast,peer,skeptic,tutor}
  --language {en,zh-en}
  --tts-engine {edge-tts,openai}
  --output-dir OUTPUT_DIR
  --llm-provider {anthropic,gemini,openai,openrouter}
  --llm-model LLM_MODEL
  --vlm                 Use Granite Docling VLM for enhanced PDF parsing (requires: pip install peripatos[vlm])
  --verbose, -v
```

> **Note:** The `--tts-engine` flag selects which engine to use, but engine-specific options — voice selection (`voice_host`, `voice_expert`) and TTS model — are not available as CLI flags. Configure these in `~/.peripatos/config.yaml` under the `tts` section. See [TTS Engine Setup](#tts-engine-setup) and [Recommended Settings](#recommended-settings) for details.

## Requirements

*   Python 3.10 or higher
*   `ffmpeg` for audio processing and chapter injection
*   API keys for at least one LLM provider (OpenAI, Anthropic, OpenRouter, or Google Gemini)

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
*   **Anthropic**: For Claude models and powerful reasoning capabilities.
*   **OpenRouter**: For unified API gateway access to multiple LLM providers.
*   **Google Gemini**: For advanced multimodal and reasoning capabilities.
*   **edge-tts**: For high-quality fallback speech synthesis.
