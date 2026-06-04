"""Peripatos Core - convert academic papers to Socratic-dialogue podcasts."""
from __future__ import annotations
import argparse
import sys
from pathlib import Path


def _save_script_json(script: "DialogueScript", output_path: Path) -> None:
    """Save a DialogueScript as JSON next to the output MP3.

    Writes to the same directory with .json extension.
    On failure, logs a warning but does not raise.
    """
    import logging
    logger = logging.getLogger(__name__)
    json_path = output_path.with_suffix(".json")
    try:
        from dataclasses import asdict
        import json
        json_path.write_text(
            json.dumps(asdict(script), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Script saved to %s", json_path)
    except Exception as exc:
        logger.warning("Could not save script JSON (%s): %s", json_path, exc)


def _get_settings(config_path=None):
    from peripatos_core.config import load_settings
    return load_settings(config_path=config_path)


def cmd_generate(args):
    """Convert a paper to a Socratic-dialogue MP3."""
    from peripatos_core.audio import AudioRenderer
    from peripatos_core.dialogue import DialogueGenerator
    from peripatos_core.fetcher import PaperFetcher
    from peripatos_core.parser import PDFParser
    from peripatos_core.registry import build_llm_provider, build_tts_provider, build_voice_map

    settings = _get_settings(args.config)
    if args.language is not None:
        settings.language = args.language

    print(f"Fetching paper: {args.source}")
    fetcher = PaperFetcher()
    fetched_path, metadata = fetcher.fetch(args.source)

    print(f"Processing source: {fetched_path.name}")
    if fetched_path.suffix.lower() == ".pdf":
        parser = PDFParser(mineru_token=settings.parser.mineru_token or None)
        parsed = parser.parse(fetched_path)
        paper_content = parsed.markdown
    elif fetched_path.suffix.lower() == ".html":
        from bs4 import BeautifulSoup  # type: ignore[reportMissingImports]

        raw_html = fetched_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(raw_html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        body = soup.body or soup
        paper_content = body.get_text(separator="\n\n", strip=True)
    else:
        paper_content = fetched_path.read_text(encoding="utf-8", errors="ignore")

    print(f"Generating dialogue (archetype={args.archetype})")
    llm = build_llm_provider(settings.llm)
    gen = DialogueGenerator(llm=llm, settings=settings)
    script = gen.generate(
        paper_content=paper_content,
        archetype=args.archetype,
        title=metadata.title,
        metadata=metadata,
    )
    print(f"  Generated {len(script.turns)} turns: {script.title}")

    # Save dialogue script JSON
    _save_script_json(script, args.output)

    print("Synthesizing audio")
    tts = build_tts_provider(settings.tts)
    from peripatos_core.archetypes import ArchetypeLoader
    archetype_prompt = ArchetypeLoader().load(args.archetype)
    voice_map = build_voice_map(settings, archetype_prompt, language=settings.language)
    renderer = AudioRenderer(tts=tts, voice_map=voice_map)
    chapters = renderer.render(script, args.output)

    print(f"Done! Output: {args.output} ({len(chapters)} chapters)")


def cmd_doctor(args):
    """Check configuration and print diagnostic info."""
    settings = _get_settings(args.config)
    from peripatos_core.registry import _resolve_voice_slots

    host_voice, interviewee_voice, source = _resolve_voice_slots(settings, language=settings.language)
    source_label = {"config": "from config", "default": "from default", "legacy": "from legacy tts.voice"}.get(source, source)

    print("Peripatos Doctor")
    print("=" * 40)
    print("LLM provider:  openai_compatible")
    print(f"LLM base_url:  {settings.llm.base_url}")
    print(f"LLM model:     {settings.llm.model}")
    print(f"LLM api_key:   {'present' if settings.llm.api_key else 'MISSING'}")
    print(f"TTS provider:  {settings.tts.provider}")
    print(f"TTS host voice:        {host_voice}  ({source_label})")
    print(f"TTS interviewee voice: {interviewee_voice}  ({source_label})")
    print(f"Default arch:  {settings.archetype}")
    print(f"Default lang:  {settings.language}")
    print(f"Output dir:    {settings.output_dir}")
    print("=" * 40)
    if not settings.llm.api_key:
        print("WARNING: llm.api_key is not set. Set it in your config file.", file=sys.stderr)


def cmd_list_archetypes(_args):
    """List available dialogue archetypes."""
    from peripatos_core.archetypes import ArchetypeLoader
    loader = ArchetypeLoader()
    available = sorted(loader.list_available())
    print("Available archetypes:")
    for name in available:
        print(f"  - {name}")


def main():
    parser = argparse.ArgumentParser(
        prog="peripatos",
        description="Convert academic papers to Socratic-dialogue podcasts.",
    )
    parser.add_argument("--config", "-c", type=Path, default=None,
                        help="Path to JSON config file.")

    subparsers = parser.add_subparsers(dest="command")

    # generate
    gen = subparsers.add_parser("generate", help="Convert a paper to MP3.")
    gen.add_argument("source",
                     help="ArXiv ID, ArXiv URL, PDF URL, local PDF path, HTML URL, or local .md/.txt file.")
    gen.add_argument("--output", "-o", type=Path, default=Path("output.mp3"),
                     help="Output MP3 file path.")
    gen.add_argument("--archetype", "-a", default="peer",
                     help="Dialogue archetype: peer, skeptic, tutor, enthusiast.")
    gen.add_argument("--config", "-c", type=Path, default=None,
                     help="Path to JSON config file.")
    gen.add_argument("--language", default=None,
                     help="Dialogue language (en, zh-CN, etc). Overrides config defaults.language.")
    gen.set_defaults(func=cmd_generate)

    # doctor
    doc = subparsers.add_parser("doctor", help="Check configuration and print diagnostic info.")
    doc.add_argument("--config", "-c", type=Path, default=None,
                     help="Path to JSON config file.")
    doc.set_defaults(func=cmd_doctor)

    # list-archetypes
    la = subparsers.add_parser("list-archetypes", help="List available dialogue archetypes.")
    la.set_defaults(func=cmd_list_archetypes)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
