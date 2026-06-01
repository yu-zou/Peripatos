"""Audio renderer — synthesizes dialogue turns and assembles final MP3 with chapter markers."""
from __future__ import annotations
import logging
import tempfile
from pathlib import Path
from pydub import AudioSegment as PydubAudioSegment  # type: ignore[reportMissingImports]

from peripatos_core.exceptions import AudioError, TTSError
from peripatos_core.providers.tts import TTSProvider
from peripatos_core.types import AudioSegment, Chapter, ChapterMark, DialogueScript, DialogueTurn

logger = logging.getLogger(__name__)

_AUDIO_DIR = Path(__file__).parent / "audio"


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
            List of ChapterMark objects (one per chapter).
        """
        if not script.chapters or not any(ch.turns for ch in script.chapters):
            raise AudioError("Cannot render empty dialogue script")

        chapter_segments: list[list[AudioSegment]] = []
        all_chapter_marks: list[ChapterMark] = []
        cumulative_ms = 0

        # PREPEND: Intro chapter
        if script.intro_turns:
            intro_segments: list[AudioSegment] = []
            for turn in script.intro_turns:
                seg = self._synthesize_segment(turn)
                intro_segments.append(seg)
                cumulative_ms += int(seg.duration_s * 1000)
            all_chapter_marks.append(ChapterMark(
                title="Introduction",
                start_ms=0,
                end_ms=cumulative_ms,
            ))
            chapter_segments.append(intro_segments)

        # MAIN: Content chapters
        for chapter in script.chapters:
            start_ms = cumulative_ms
            segments: list[AudioSegment] = []

            # Synthesize transition audio if this chapter has one
            if chapter.transition_in_text:
                seg = self._synthesize_transition(chapter)
                segments.append(seg)
                cumulative_ms += int(seg.duration_s * 1000)

            # Synthesize turns in this chapter
            for turn in chapter.turns:
                seg = self._synthesize_segment(turn)
                segments.append(seg)
                cumulative_ms += int(seg.duration_s * 1000)

            chapter_segments.append(segments)
            all_chapter_marks.append(ChapterMark(
                title=chapter.title,
                start_ms=start_ms,
                end_ms=cumulative_ms,
            ))

        # APPEND: Outro chapter
        if script.outro_turns:
            outro_start_ms = cumulative_ms
            outro_segments: list[AudioSegment] = []
            for turn in script.outro_turns:
                seg = self._synthesize_segment(turn)
                outro_segments.append(seg)
                cumulative_ms += int(seg.duration_s * 1000)
            all_chapter_marks.append(ChapterMark(
                title="Outro",
                start_ms=outro_start_ms,
                end_ms=cumulative_ms,
            ))
            chapter_segments.append(outro_segments)

        all_segments = [seg for group in chapter_segments for seg in group]
        dialogue_audio = self._concatenate_segments(all_segments)

        # Mix intro and outro music
        final_audio, intro_offset_ms = self._mix_music(dialogue_audio)

        # Shift all chapter marks by intro offset
        for mark in all_chapter_marks:
            mark.start_ms += intro_offset_ms
            mark.end_ms += intro_offset_ms

        # Export final audio to temp file, then write with ID3 chapters
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        final_path = Path(tmp.name)
        final_audio.export(str(final_path), format="mp3")

        self._write_with_chapters(final_path, output_path, script.title, all_chapter_marks)
        return all_chapter_marks

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

    def _synthesize_segment(self, turn: DialogueTurn) -> AudioSegment:
        """Synthesize a single dialogue turn."""
        voice = self._voice_map.get(turn.speaker)
        try:
            audio_path = self._tts.synthesize(turn.text, speaker_voice=voice)
        except Exception as exc:
            raise TTSError(f"TTS failed for turn ({turn.speaker}): {exc}") from exc
        duration_s = self._get_duration(audio_path)
        return AudioSegment(
            speaker=turn.speaker, text=turn.text,
            audio_path=audio_path, duration_s=duration_s,
        )

    def _synthesize_transition(self, chapter: Chapter) -> AudioSegment:
        """Synthesize a chapter transition."""
        assert chapter.transition_in_text is not None, \
            "chapter.transition_in_text must not be None when synthesizing transition"
        host_voice = self._voice_map.get("Host")
        if host_voice is None and chapter.turns:
            host_voice = self._voice_map.get(chapter.turns[0].speaker)
        try:
            audio_path = self._tts.synthesize(
                chapter.transition_in_text, speaker_voice=host_voice,
            )
        except Exception as exc:
            raise TTSError(
                f"TTS failed for transition in chapter '{chapter.title}': {exc}"
            ) from exc
        duration_s = self._get_duration(audio_path)
        return AudioSegment(
            speaker="Host", text=chapter.transition_in_text,
            audio_path=audio_path, duration_s=duration_s,
        )

    def _concatenate_segments(self, segments: list[AudioSegment]) -> PydubAudioSegment:
        """Concatenate all audio segments into a single pydub AudioSegment.

        Uses pydub for proper audio concatenation instead of raw byte merging.
        """
        if not segments:
            raise AudioError("No audio segments to concatenate")

        try:
            combined = PydubAudioSegment.from_mp3(str(segments[0].audio_path))
            for seg in segments[1:]:
                try:
                    chunk = PydubAudioSegment.from_mp3(str(seg.audio_path))
                    combined = combined.append(chunk)
                except Exception as exc:
                    logger.warning("Could not load %s, skipping: %s", seg.audio_path, exc)
        except Exception as exc:
            raise AudioError(f"Failed to concatenate audio segments: {exc}") from exc
        return combined

    def _compute_chapters(
        self,
        chapter_segments: list[list[AudioSegment]],
        chapters: list[Chapter],
    ) -> list[ChapterMark]:
        """Compute chapter marks from per-chapter segment groups.

        Returns one ChapterMark per chapter. The mark title comes from
        chapter.title (content-based), not from speaker names.
        """
        marks: list[ChapterMark] = []
        cumulative_ms = 0

        for chapter, segments in zip(chapters, chapter_segments):
            chapter_start_ms = cumulative_ms
            for seg in segments:
                cumulative_ms += int(seg.duration_s * 1000)

            marks.append(ChapterMark(
                title=chapter.title,
                start_ms=chapter_start_ms,
                end_ms=cumulative_ms,
            ))

        return marks

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

    def _load_music(self, filename: str) -> PydubAudioSegment:
        """Load an MP3 from peripatos_core/audio/.

        Raises AudioError if the file is not found.
        """
        music_path = _AUDIO_DIR / filename
        resolved = music_path.resolve()
        if not resolved.is_relative_to(_AUDIO_DIR.resolve()):
            raise AudioError(f"Music file must be inside {_AUDIO_DIR}")
        if not resolved.exists():
            raise AudioError(f"Music file not found: {resolved}")
        try:
            return PydubAudioSegment.from_mp3(str(music_path))
        except Exception as exc:
            raise AudioError(f"Failed to load music file {music_path}: {exc}") from exc

    def _mix_music(self, dialogue: PydubAudioSegment) -> tuple[PydubAudioSegment, int]:
        """Prepend intro music and append outro music with fade effects.

        Args:
            dialogue: The dialogue audio as a pydub AudioSegment.

        Returns:
            Tuple of (mixed audio as pydub AudioSegment, intro_duration_ms offset).
        """
        intro_music = self._load_music("intro.mp3")
        outro_music = self._load_music("outro.mp3")

        intro_duration_ms = len(intro_music)

        # Intro: fade-out music, placed before dialogue
        intro_music = intro_music.fade_out(duration=500)
        combined = intro_music.append(dialogue)

        # Outro: fade-in + fade-out, appended after dialogue
        outro_music = outro_music.fade_in(duration=300).fade_out(duration=1000)
        combined = combined.append(outro_music)

        return combined, intro_duration_ms
