# CLI Reference

## `peripatos generate <source>`

Convert a paper into a podcast MP3.

| Argument | Description |
|----------|-------------|
| `source` | ArXiv ID (e.g. `1706.03762`), ArXiv URL, local PDF/HTML/Markdown/Text file, or HTTP(S) URL. |

| Flag | Short | Description |
|------|-------|-------------|
| `--output` | `-o` | Output MP3 path (default: `output.mp3`). |
| `--archetype` | `-a` | Dialogue style: `peer`, `skeptic`, `tutor`, or `enthusiast` (default: `peer`). |
| `--config` | `-c` | Path to a JSON config file. |

**Examples:**

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

## `peripatos list-archetypes`

Print all available archetypes with descriptions.

## `peripatos doctor`

Print diagnostic info for the resolved configuration.

Accepts `--config` to target a specific file, otherwise reads
`~/.config/peripatos/config.json`.