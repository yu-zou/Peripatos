"""Typer CLI for Peripatos Core."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import typer

app = typer.Typer(
    name="peripatos",
    help="Convert academic papers to Socratic-dialogue podcasts.",
    add_completion=False,
)

# Global state for config path (set via callback)
_config_path: Optional[Path] = None


def _get_settings(config_path: Optional[Path] = None):
    from peripatos_core.config import load_settings
    return load_settings(config_path=config_path or _config_path)


@app.callback()
def main(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to JSON config file. Overrides ~/.config/peripatos/config.json.",
        envvar=None,
    ),
) -> None:
    """Peripatos Core - convert academic papers to Socratic-dialogue podcasts."""
    global _config_path
    _config_path = config


@app.command()
def generate(
    source: str = typer.Argument(
        ...,
        help="ArXiv ID (e.g. 1706.03762), ArXiv URL, PDF URL, or local PDF path.",
    ),
    output: Path = typer.Option(
        Path("output.mp3"),
        "--output",
        "-o",
        help="Output MP3 file path.",
    ),
    archetype: str = typer.Option(
        "peer",
        "--archetype",
        "-a",
        help="Dialogue archetype: peer, skeptic, tutor, enthusiast.",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to JSON config file.",
    ),
) -> None:
    """Convert a paper to a Socratic-dialogue MP3."""
    from peripatos_core.audio import AudioRenderer
    from peripatos_core.dialogue import DialogueGenerator
    from peripatos_core.fetcher import PaperFetcher
    from peripatos_core.parser import PDFParser
    from peripatos_core.registry import build_llm_provider, build_tts_provider

    effective_config = config or _config_path
    settings = _get_settings(effective_config)

    typer.echo(f"[1/5] Fetching paper: {source}")
    fetcher = PaperFetcher()
    pdf_path, metadata = fetcher.fetch(source)

    typer.echo(f"[2/5] Parsing PDF: {pdf_path.name}")
    parser = PDFParser()
    parsed = parser.parse(pdf_path)

    typer.echo(f"[3/5] Generating dialogue (archetype={archetype})")
    llm = build_llm_provider(settings.llm)
    gen = DialogueGenerator(llm=llm, max_paper_chars=settings.llm.max_paper_chars)
    script = gen.generate(
        paper_content=parsed.markdown,
        archetype=archetype,
        title=metadata.title,
    )
    typer.echo(f"    Generated {len(script.turns)} turns: {script.title}")

    typer.echo("[4/5] Synthesizing audio")
    tts = build_tts_provider(settings.tts)
    renderer = AudioRenderer(tts=tts)
    chapters = renderer.render(script, output)

    typer.echo(f"[5/5] Done! Output: {output} ({len(chapters)} chapters)")


@app.command(name="list-archetypes")
def list_archetypes() -> None:
    """List available dialogue archetypes."""
    from peripatos_core.archetypes import ArchetypeLoader
    loader = ArchetypeLoader()
    available = sorted(loader.list_available())
    typer.echo("Available archetypes:")
    for name in available:
        typer.echo(f"  - {name}")


@app.command()
def doctor(
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to JSON config file.",
    ),
) -> None:
    """Check configuration and print diagnostic info."""
    effective_config = config or _config_path
    settings = _get_settings(effective_config)

    typer.echo("Peripatos Doctor")
    typer.echo("=" * 40)
    typer.echo(f"LLM provider:  openai_compatible")
    typer.echo(f"LLM base_url:  {settings.llm.base_url}")
    typer.echo(f"LLM model:     {settings.llm.model}")
    typer.echo(f"LLM api_key:   {'present' if settings.llm.api_key else 'MISSING'}")
    typer.echo(f"TTS provider:  {settings.tts.provider}")
    typer.echo(f"TTS voice:     {settings.tts.voice}")
    typer.echo(f"Default arch:  {settings.defaults.archetype}")
    typer.echo(f"Output dir:    {settings.defaults.output_dir}")
    typer.echo("=" * 40)
    if not settings.llm.api_key:
        typer.echo("WARNING: llm.api_key is not set. Set it in your config file.", err=True)
