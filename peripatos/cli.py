from __future__ import annotations

import argparse
import logging
import sys
import traceback
from pathlib import Path
from typing import Callable, cast

try:
    from typing import override
except ImportError:
    from typing_extensions import override

from peripatos import __version__
from peripatos.brain.bilingual import BilingualProcessor, get_bilingual_prompt_modifier
from peripatos.brain.generator import DialogueGenerator, GenerationError
from peripatos.config import (
    PeripatosConfig,
    VALID_LANGUAGES,
    VALID_LLM_PROVIDERS,
    VALID_PERSONAS,
    VALID_TTS_ENGINES,
    load_config,
)
from peripatos.eye.arxiv import ArxivFetcher, FetchError
from peripatos.eye.math_normalize import MathNormalizer
from peripatos.eye.parser import PDFParser, ParsingError
from peripatos.models import (
    AudioSegment,
    ChapterMarker,
    DialogueScript,
    LanguageMode,
    PaperMetadata,
    SectionInfo,
)
from peripatos.voice.mixer import AudioMixer, MixerError
from peripatos.voice.renderer import AudioRenderer


logger = logging.getLogger(__name__)


class _DialogueGeneratorWithModifier(DialogueGenerator):
    def __init__(self, prompt_modifier: str) -> None:
        super().__init__()
        self._prompt_modifier: str = prompt_modifier

    @override
    def _build_system_prompt(self, prompts: dict[str, str]) -> str:
        return self._compose_system_prompt(prompts)

    def _compose_system_prompt(self, prompts: dict[str, str]) -> str:
        base = super()._build_system_prompt(prompts)
        if self._prompt_modifier:
            return f"{base} {self._prompt_modifier}"
        return base


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="peripatos",
        description=(
            "peripatos generate <source> - Convert a paper into Socratic audio dialogue."
        ),
    )
    _ = parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate", help="Generate audio from an ArXiv ID or PDF")

    _ = generate.add_argument("source", help="ArXiv ID or local PDF path")
    _ = generate.add_argument(
        "--persona",
        choices=sorted(VALID_PERSONAS),
        default=None,
    )
    _ = generate.add_argument(
        "--language",
        choices=sorted(VALID_LANGUAGES),
        default=None,
    )
    _ = generate.add_argument(
        "--tts-engine",
        choices=sorted(VALID_TTS_ENGINES),
        dest="tts_engine",
        default=None,
    )
    _ = generate.add_argument(
        "--output-dir",
        dest="output_dir",
        default=None,
    )
    _ = generate.add_argument(
        "--llm-provider",
        choices=sorted(VALID_LLM_PROVIDERS),
        dest="llm_provider",
        default=None,
    )
    _ = generate.add_argument(
        "--llm-model",
        dest="llm_model",
        default=None,
    )
    _ = generate.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        dest="verbose",
    )
    _ = generate.add_argument(
        "--vlm",
        action="store_true",
        dest="vlm",
        default=False,
        help="Use Granite Docling VLM for enhanced PDF parsing (requires: pip install peripatos[vlm])",
    )

    return parser


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def _build_cli_overrides(args: argparse.Namespace) -> dict[str, str]:
    overrides: dict[str, str] = {}
    persona = cast(str | None, getattr(args, "persona", None))
    language = cast(str | None, getattr(args, "language", None))
    tts_engine = cast(str | None, getattr(args, "tts_engine", None))
    output_dir = cast(str | None, getattr(args, "output_dir", None))
    llm_provider = cast(str | None, getattr(args, "llm_provider", None))
    llm_model = cast(str | None, getattr(args, "llm_model", None))

    if persona:
        overrides["persona"] = persona
    if language:
        overrides["language"] = language
    if tts_engine:
        overrides["tts_engine"] = tts_engine
    if output_dir:
        overrides["output_dir"] = output_dir
    if llm_provider:
        overrides["llm_provider"] = llm_provider
    if llm_model:
        overrides["llm_model"] = llm_model
    return overrides


def detect_source_type(source: str) -> str | None:
    if ArxivFetcher.ARXIV_ID_PATTERN.match(source):
        return "arxiv"
    path = Path(source)
    if path.exists() and path.is_file() and path.suffix.lower() == ".pdf":
        return "pdf"
    return None


def _language_mode_from_config(language: str) -> LanguageMode:
    if language == "zh-en":
        return LanguageMode.ZH_EN
    return LanguageMode.EN


def _normalize_paper(paper: PaperMetadata, normalizer: MathNormalizer) -> PaperMetadata:
    sections = [
        SectionInfo(
            title=section.title,
            content=normalizer.normalize(section.content),
            section_type=section.section_type,
        )
        for section in paper.sections
    ]
    abstract = normalizer.normalize(paper.abstract) if paper.abstract else ""
    return PaperMetadata(
        title=paper.title,
        authors=paper.authors,
        abstract=abstract,
        source_path=paper.source_path,
        sections=sections,
        arxiv_id=paper.arxiv_id,
    )


def _handle_error(message: str, exc: Exception | None, verbose: bool) -> int:
    print(f"Error: {message}", file=sys.stderr)
    if verbose and exc is not None:
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    return 1


def _resolve_source(
    source: str,
    source_type: str,
    output_dir: Path,
    verbose: bool,
) -> Path | int:
    if source_type == "arxiv":
        print("🌐 Fetching ArXiv PDF...")
        try:
            fetcher = ArxivFetcher(output_dir=str(output_dir))
            return fetcher.fetch(source)
        except FetchError as exc:
            return _handle_error(str(exc), exc, verbose)
    return Path(source)


def _parse_pdf(pdf_path: Path, use_vlm: bool, verbose: bool) -> PaperMetadata | int:
    print("📄 Parsing PDF...")
    try:
        parser = PDFParser(use_vlm=use_vlm)
        return parser.parse(pdf_path)
    except ImportError as exc:
        return _handle_error(f"VLM support requires additional dependencies. Install with: pip install peripatos[vlm]. Error: {exc}", exc, verbose)
    except ParsingError as exc:
        return _handle_error(str(exc), exc, verbose)


def _generate_dialogue(
    paper: PaperMetadata,
    config: PeripatosConfig,
    verbose: bool,
) -> tuple[DialogueScript | int, str]:
    language_mode = _language_mode_from_config(config.language)
    prompt_modifier = get_bilingual_prompt_modifier(language_mode)
    generator: DialogueGenerator
    if prompt_modifier:
        generator = _DialogueGeneratorWithModifier(prompt_modifier)
    else:
        generator = DialogueGenerator()

    persona_label = config.persona.title()
    print(f"🧠 Generating dialogue ({persona_label} persona)...")
    try:
        script = generator.generate(paper, config)
    except GenerationError as exc:
        return _handle_error(str(exc), exc, verbose), ""

    if language_mode == LanguageMode.ZH_EN:
        script = BilingualProcessor().process(script)
    return script, prompt_modifier


def _progress_printer() -> Callable[[int, int], None]:
    def callback(current: int, total: int) -> None:
        print(f"🔊 Rendering audio... {current}/{total}")

    return callback


def _render_audio(
    script: DialogueScript,
    config: PeripatosConfig,
    verbose: bool,
) -> list[AudioSegment]:
    print("🔊 Rendering audio...")
    try:
        renderer = AudioRenderer(config)
        return renderer.render(script, progress_callback=_progress_printer())
    except Exception as exc:
        _ = _handle_error(str(exc), exc, verbose)
        return []


def _build_chapters(
    script: DialogueScript,
    segments: list[AudioSegment],
    silence_between_ms: int,
) -> tuple[list[ChapterMarker], int]:
    turns = list(script.turns)
    seg_list = list(segments)
    count = min(len(turns), len(seg_list))
    current_time_ms = 0
    times: dict[str, dict[str, int]] = {}
    for idx in range(count):
        turn = turns[idx]
        segment = seg_list[idx]
        title = turn.section_ref or "Section"
        if title not in times:
            times[title] = {"start": current_time_ms, "end": current_time_ms}
        duration_ms = int(round(segment.duration_seconds * 1000))
        current_time_ms += duration_ms
        if idx < count - 1:
            current_time_ms += silence_between_ms
        times[title]["end"] = current_time_ms

    chapters: list[ChapterMarker] = []
    for section in script.paper_metadata.sections:
        if section.title not in times:
            continue
        window = times[section.title]
        if window["end"] <= window["start"]:
            continue
        chapters.append(
            ChapterMarker(
                title=section.title,
                start_time_ms=window["start"],
                end_time_ms=window["end"],
            )
        )
    return chapters, current_time_ms


def _output_filename(paper: PaperMetadata, persona: str, language: str) -> str:
    base = paper.arxiv_id or paper.source_path.stem
    return f"{base}_{persona}_{language}.mp3"


def _mix_audio(
    segments: list[AudioSegment],
    chapters: list[ChapterMarker],
    output_path: Path,
    verbose: bool,
) -> Path | int:
    print("🎚️ Mixing audio...")
    mixer = AudioMixer()
    try:
        return mixer.mix(segments, chapters, output_path)
    except MixerError as exc:
        return _handle_error(str(exc), exc, verbose)


def main(argv: list[str] | None = None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)
    verbose = cast(bool, getattr(args, "verbose", False))
    _configure_logging(verbose)

    overrides = _build_cli_overrides(args)
    try:
        config: PeripatosConfig = load_config(cli_overrides=overrides)
    except ValueError as exc:
        return _handle_error(str(exc), exc, verbose)

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🔎 Detecting source...")
    source = cast(str, getattr(args, "source", ""))
    source_type = detect_source_type(source)
    if source_type is None:
        parser.error(
            f"Invalid source: {source}. Must be an ArXiv ID or existing PDF path."
        )

    resolved = _resolve_source(source, source_type, output_dir, verbose)
    if isinstance(resolved, int):
        return resolved
    pdf_path = resolved

    use_vlm = cast(bool, getattr(args, "vlm", False))
    parsed = _parse_pdf(pdf_path, use_vlm, verbose)
    if isinstance(parsed, int):
        return parsed
    paper = parsed
    if source_type == "arxiv":
        paper.arxiv_id = source

    print("🧮 Normalizing math...")
    try:
        normalizer = MathNormalizer()
        paper = _normalize_paper(paper, normalizer)
    except Exception as exc:
        return _handle_error("Failed to normalize math", exc, verbose)

    try:
        config.validate_api_keys()
    except ValueError as exc:
        return _handle_error(str(exc), exc, verbose)

    script_result, _ = _generate_dialogue(paper, config, verbose)
    if isinstance(script_result, int):
        return script_result
    script = script_result

    segments = _render_audio(script, config, verbose)
    if not segments:
        return 1

    mixer = AudioMixer()
    chapters, total_time_ms = _build_chapters(
        script,
        segments,
        mixer.silence_between_segments_ms,
    )
    output_path = output_dir / _output_filename(paper, config.persona, config.language)

    mixed = _mix_audio(segments, chapters, output_path, verbose)
    if isinstance(mixed, int):
        return mixed

    total_duration_seconds = total_time_ms / 1000.0
    print(f"✅ Output saved to: {mixed}")
    print(f"📌 Chapters: {len(chapters)}")
    print(f"⏱️ Duration: {total_duration_seconds:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
