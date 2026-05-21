"""Audio renderer — synthesizes dialogue turns and assembles final MP3 with chapter markers."""
from __future__ import annotations
import logging
import tempfile
import shutil
from pathlib import Path
from peripatos_core.exceptions import AudioError
from peripatos_core.providers.tts import TTSProvider
from peripatos_core.types import AudioSegment, ChapterMark, DialogueScript

logger = logging.getLogger(__name__)


class AudioRenderer:
    """Renders a DialogueScript to an MP3 file with ID3v2.4 chapter markers."""

    def __init__(
        self,
        tts: TTSProvider,
        voice_map: dict[str, str] | None = None,
    ) -> None:
        """
        Args:
            tts: TTS provider to use for synthesis.
            voice_map: Optional mapping of speaker name → TTS voice string.
                       e.g. {"Host": "en-US-AriaNeural", "Guest": "en-US-GuyNeural"}
        """
        self._tts = tts
        self._voice_map = voice_map or {}

    def render(self, script: DialogueScript, output_path: Path) -> list[ChapterMark]:
        """Render a dialogue script to an MP3 file.

        Args:
            script: The dialogue script to render.
            output_path: Where to write the final MP3.

        Returns:
            List of ChapterMark objects (one per turn).
        """
        if not script.turns:
            raise AudioError("Cannot render empty dialogue script")

        segments = self._synthesize_turns(script)
        combined_path = self._concatenate_segments(segments)
        chapters = self._compute_chapters(segments)
        self._write_with_chapters(combined_path, output_path, script.title, chapters)
        return chapters

    def _synthesize_turns(self, script: DialogueScript) -> list[AudioSegment]:
        """Synthesize each turn and return AudioSegment list."""
        segments = []
        for i, turn in enumerate(script.turns):
            voice = self._voice_map.get(turn.speaker)
            logger.debug("Synthesizing turn %d/%d: %s", i + 1, len(script.turns), turn.speaker)
            try:
                audio_path = self._tts.synthesize(turn.text, speaker_voice=voice)
            except Exception as exc:
                from peripatos_core.exceptions import TTSError
                raise TTSError(f"TTS failed for turn {i} ({turn.speaker}): {exc}") from exc

            duration_s = self._get_duration(audio_path)
            segments.append(AudioSegment(
                speaker=turn.speaker,
                text=turn.text,
                audio_path=audio_path,
                duration_s=duration_s,
            ))
        return segments

    def _get_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds using pydub."""
        try:
            from mutagen.mp3 import MP3  # type: ignore[reportMissingImports]
            return max(MP3(str(audio_path)).info.length, 0.1)
        except Exception as exc:
            logger.warning("Could not read duration from %s (using 0.1): %s", audio_path, exc)
            return 0.1

    def _concatenate_segments(self, segments: list[AudioSegment]) -> Path:
        """Concatenate all audio segments into a single MP3 file."""
        if not segments:
            raise AudioError("No audio segments to concatenate")

        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.close()
            combined_path = Path(tmp.name)
            with combined_path.open("wb") as out:
                for seg in segments:
                    try:
                        with seg.audio_path.open("rb") as inp:
                            shutil.copyfileobj(inp, out)
                    except OSError as exc:
                        logger.warning("Could not read %s, using empty segment: %s", seg.audio_path, exc)
        except Exception as exc:
            raise AudioError(f"Failed to create/export concatenated audio: {exc}") from exc
        return combined_path

    def _compute_chapters(self, segments: list[AudioSegment]) -> list[ChapterMark]:
        """Compute chapter marks from segment durations."""
        chapters = []
        cursor_ms = 0
        for seg in segments:
            duration_ms = int(seg.duration_s * 1000)
            chapters.append(ChapterMark(
                title=seg.speaker,
                start_ms=cursor_ms,
                end_ms=cursor_ms + duration_ms,
            ))
            cursor_ms += duration_ms
        return chapters

    def _write_with_chapters(
        self,
        source_path: Path,
        output_path: Path,
        title: str,
        chapters: list[ChapterMark],
    ) -> None:
        """Copy source MP3 to output and embed ID3v2.4 chapter markers."""
        import shutil
        try:
            shutil.copy2(str(source_path), str(output_path))
        except OSError as exc:
            raise AudioError(f"Failed to copy audio to output path: {exc}") from exc

        try:
            from mutagen.id3 import ID3, ID3NoHeaderError, CHAP, CTOC, TIT2, CTOCFlags  # type: ignore[reportMissingImports]
        except ImportError as exc:
            raise AudioError("mutagen is not installed") from exc

        try:
            try:
                tags = ID3(str(output_path))
            except ID3NoHeaderError:
                tags = ID3()

            # Clear existing chapter tags
            tags.delall("CHAP")
            tags.delall("CTOC")

            # Add title
            tags.add(TIT2(encoding=3, text=title))

            # Add CHAP frames
            chap_ids = []
            for i, ch in enumerate(chapters):
                chap_id = f"chp{i}"
                chap_ids.append(chap_id)
                tags.add(CHAP(
                    element_id=chap_id,
                    start_time=ch.start_ms,
                    end_time=ch.end_ms,
                    start_offset=0xFFFFFFFF,
                    end_offset=0xFFFFFFFF,
                    sub_frames=[TIT2(encoding=3, text=ch.title)],
                ))

            # Add CTOC (table of contents)
            tags.add(CTOC(
                element_id="toc",
                flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
                child_element_ids=chap_ids,
                sub_frames=[TIT2(encoding=3, text=title)],
            ))

            tags.save(str(output_path), v2_version=4)
        except AudioError:
            raise
        except Exception as exc:
            raise AudioError(f"Failed to write ID3 tags to {output_path}: {exc}") from exc
