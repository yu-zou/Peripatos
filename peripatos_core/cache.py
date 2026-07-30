"""Caching layer for audio synthesis and dialogue generation."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from peripatos_core.types import DialogueScript

from peripatos_core.providers.tts import TTSProvider

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages hash-based persistent caches for audio and dialogue.

    Audio cache: per-turn MP3 files, keyed by (provider, voice_id, text).
    Dialogue cache: per-script JSON files, keyed by (model, archetype, language, paper_content).

    All writes are atomic (write to .tmp, then os.replace).
    """

    def __init__(
        self,
        base_dir: Path,
        audio_enabled: bool = True,
        dialogue_enabled: bool = True,
    ) -> None:
        self._base = Path(base_dir)
        self._audio_enabled = audio_enabled
        self._dialogue_enabled = dialogue_enabled

    # -- Audio cache ---------------------------------------------------------

    def audio_key(self, provider: str, voice_id: str, text: str) -> str:
        """Compute cache key for an audio turn."""
        raw = f"{provider}|{voice_id}|{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _audio_dir(self) -> Path:
        return self._base / "audio"

    def audio_path(self, hash_key: str) -> Path:
        return self._audio_dir() / f"{hash_key}.mp3"

    def audio_get(self, hash_key: str) -> Path | None:
        """Return cached audio path if it exists, else None."""
        if not self._audio_enabled:
            return None
        path = self.audio_path(hash_key)
        if path.exists() and path.stat().st_size > 0:
            return path
        return None

    def audio_put(self, hash_key: str, src_path: Path) -> Path:
        """Copy an audio file into the cache atomically. Returns cache path."""
        if not self._audio_enabled:
            return src_path
        cache_dir = self._audio_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        dest = self.audio_path(hash_key)
        fd, tmp_path = tempfile.mkstemp(suffix=".mp3", dir=str(cache_dir))
        os.close(fd)
        try:
            shutil.copy2(str(src_path), tmp_path)
            os.replace(tmp_path, str(dest))
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise
        return dest

    # -- Dialogue cache ------------------------------------------------------

    def dialogue_key(
        self,
        llm_model: str,
        archetype: str,
        language: str,
        paper_content: str,
        *,
        prompt_version: str = "",
    ) -> str:
        """Compute cache key for a dialogue script."""
        raw = f"{llm_model}|{archetype}|{language}|{prompt_version}|{paper_content}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _dialogue_dir(self) -> Path:
        return self._base / "dialogue"

    def dialogue_path(self, hash_key: str) -> Path:
        return self._dialogue_dir() / f"{hash_key}.json"

    def dialogue_get(self, hash_key: str) -> DialogueScript | None:
        """Load cached dialogue script if it exists, else None."""
        if not self._dialogue_enabled:
            return None
        path = self.dialogue_path(hash_key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return self._deserialize_script(data)
        except Exception as exc:
            logger.warning("Failed to load cached dialogue, regenerating: %s", exc)
            return None

    def dialogue_put(self, hash_key: str, script: DialogueScript) -> Path:
        """Serialize and write a dialogue script into the cache atomically."""
        if not self._dialogue_enabled:
            return self.dialogue_path(hash_key)
        cache_dir = self._dialogue_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        dest = self.dialogue_path(hash_key)
        data = self._serialize_script(script)
        fd, tmp_path = tempfile.mkstemp(suffix=".json", dir=str(cache_dir))
        os.close(fd)
        try:
            Path(tmp_path).write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp_path, str(dest))
        except Exception:
            Path(tmp_path).unlink(missing_ok=True)
            raise
        return dest

    @staticmethod
    def _serialize_script(script: DialogueScript) -> dict:
        """Serialize DialogueScript to a plain dict for JSON."""
        from dataclasses import asdict

        return asdict(script)

    @staticmethod
    def _deserialize_script(data: dict) -> DialogueScript:
        """Deserialize a dict back into a DialogueScript."""
        from peripatos_core.types import (
            ArchetypeId,
            Chapter,
            DialogueScript,
            DialogueTurn,
        )

        chapters = []
        for ch_data in data.get("chapters", []):
            turns = [
                DialogueTurn(
                    speaker=t["speaker"],
                    text=t["text"],
                    archetype=ArchetypeId(t["archetype"]),
                )
                for t in ch_data.get("turns", [])
            ]
            chapters.append(
                Chapter(
                    title=ch_data["title"],
                    turns=turns,
                    transition_in_text=ch_data.get("transition_in_text"),
                )
            )

        intro_turns = [
            DialogueTurn(
                speaker=t["speaker"],
                text=t["text"],
                archetype=ArchetypeId(t["archetype"]),
            )
            for t in data.get("intro_turns", [])
        ]
        outro_turns = [
            DialogueTurn(
                speaker=t["speaker"],
                text=t["text"],
                archetype=ArchetypeId(t["archetype"]),
            )
            for t in data.get("outro_turns", [])
        ]

        return DialogueScript(
            title=data["title"],
            chapters=chapters,
            intro_turns=intro_turns,
            outro_turns=outro_turns,
        )


class CachedTTSProvider(TTSProvider):
    """Wraps any TTSProvider with audio result caching.

    On cache hit, returns the cached MP3 path directly. On miss, delegates
    to the wrapped provider and stores the result.

    Usage::

        edge = EdgeTTSProvider(cfg)
        cached = CachedTTSProvider(edge, cache_mgr, provider_name="edge")
        # cached acts like any TTSProvider
    """

    def __init__(
        self,
        delegate: TTSProvider,
        cache_mgr: CacheManager,
        provider_name: str,
    ) -> None:
        self._delegate = delegate
        self._cache = cache_mgr
        self._provider_name = provider_name

    def synthesize(self, text: str, speaker_voice: str | None = None) -> Path:
        """Synthesize with caching.

        Args:
            text: Text to synthesize.
            speaker_voice: TTS voice identifier (used in cache key).

        Returns:
            Path to the MP3 file.
        """
        voice_id = speaker_voice or "default"
        cache_key = self._cache.audio_key(self._provider_name, voice_id, text)

        cached = self._cache.audio_get(cache_key)
        if cached is not None:
            logger.info(
                "Audio cache hit: %s (%d chars)",
                voice_id, len(text),
            )
            return cached

        logger.info(
            "Audio cache miss: %s (%d chars), synthesizing...",
            voice_id, len(text),
        )
        result = self._delegate.synthesize(text, speaker_voice=speaker_voice)
        self._cache.audio_put(cache_key, result)
        return result
