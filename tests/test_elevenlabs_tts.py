"""Tests for ElevenLabs TTS provider, voice selection, and registry integration."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from peripatos_core.cache import CacheManager, CachedTTSProvider
from peripatos_core.config import Settings, TTSConfig
from peripatos_core.exceptions import ConfigError
from peripatos_core.providers.elevenlabs_voices import EXPERT_VOICES, PODCAST_VOICES
from peripatos_core.providers.tts import ElevenLabsTTSProvider
from peripatos_core.registry import _resolve_elevenlabs_voices, build_tts_provider


# ─────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────


def make_settings(**tts_kwargs) -> Settings:
    """Create a Settings object with custom TTS config."""
    s = Settings()
    s.tts.provider = "elevenlabs"
    s.tts.api_key = "test-api-key"
    for k, v in tts_kwargs.items():
        if k == "voices":
            s.tts.voices.host = v.get("host", "")
            s.tts.voices.interviewee = v.get("interviewee", "")
        else:
            setattr(s.tts, k, v)
    return s


def make_tts_config(provider="elevenlabs", api_key="test-api-key", **kwargs) -> TTSConfig:
    """Create a TTSConfig for ElevenLabs testing."""
    cfg = TTSConfig(provider=provider, api_key=api_key, **kwargs)
    return cfg


# ─────────────────────────────────────────────────────────────────
# Voice resolution tests
# ─────────────────────────────────────────────────────────────────


class TestResolveElevenLabsVoices:
    """Tests for _resolve_elevenlabs_voices voice selection logic."""

    def test_explicit_host_and_interviewee(self):
        """Explicitly configured voices are used directly."""
        s = make_settings(
            voices={"host": "pNInz6obpgDQGcFmaJgB", "interviewee": "VR6AewLTigWG4xSOukaG"}
        )
        host, interviewee, host_gender, interviewee_gender = _resolve_elevenlabs_voices(s)
        assert host == "pNInz6obpgDQGcFmaJgB"
        assert interviewee == "VR6AewLTigWG4xSOukaG"
        assert host_gender == "config"
        assert interviewee_gender == "config"

    def test_explicit_voices_skips_random_selection(self):
        """With both voices configured, random.seed should NOT be called."""
        s = make_settings(
            voices={"host": "pNInz6obpgDQGcFmaJgB", "interviewee": "EXAVITQu4vr4xnSDxMaL"}
        )
        with patch("peripatos_core.registry.random.choice") as mock_choice:
            _resolve_elevenlabs_voices(s)
            mock_choice.assert_not_called()

    def test_no_explicit_config_opposite_genders(self):
        """Random selection produces opposite genders for host/interviewee."""
        s = make_settings()
        # Reset voices to empty to trigger random path
        s.tts.voices.host = ""
        s.tts.voices.interviewee = ""

        with patch("peripatos_core.registry.random.choice") as mock_choice:
            # First call: host_gender; second: host_voice (from PODCAST_VOICES[host_gender])
            # third: interviewee_voice (from EXPERT_VOICES[interviewee_gender])
            mock_choice.side_effect = [
                "male",  # host_gender
                PODCAST_VOICES["male"][0],  # host_voice_id
                EXPERT_VOICES["female"][0],  # interviewee_voice_id (female because opposite)
            ]
            host, interviewee, host_gender, interviewee_gender = _resolve_elevenlabs_voices(s)

        assert host == PODCAST_VOICES["male"][0]
        assert interviewee == EXPERT_VOICES["female"][0]
        assert host_gender == "male"
        assert interviewee_gender == "female"
        assert host_gender != interviewee_gender

    def test_no_explicit_config_female_host(self):
        """When host is female, interviewee is male."""
        s = make_settings()
        s.tts.voices.host = ""
        s.tts.voices.interviewee = ""

        with patch("peripatos_core.registry.random.choice") as mock_choice:
            mock_choice.side_effect = [
                "female",  # host_gender
                PODCAST_VOICES["female"][0],  # host_voice_id
                EXPERT_VOICES["male"][0],  # interviewee_voice_id (male because opposite)
            ]
            host, interviewee, host_gender, interviewee_gender = _resolve_elevenlabs_voices(s)

        assert host == PODCAST_VOICES["female"][0]
        assert interviewee == EXPERT_VOICES["male"][0]
        assert host_gender == "female"
        assert interviewee_gender == "male"

    def test_voice_ids_match_actual_pool(self):
        """Voice IDs returned belong to the actual PODCAST_VOICES and EXPERT_VOICES pools."""
        s = make_settings()
        s.tts.voices.host = ""
        s.tts.voices.interviewee = ""

        with patch("peripatos_core.registry.random.choice") as mock_choice:
            mock_choice.side_effect = [
                "male",
                PODCAST_VOICES["male"][0],
                EXPERT_VOICES["female"][0],
            ]
            host, interviewee, _, _ = _resolve_elevenlabs_voices(s)

        # Flatten all voice IDs from the pools
        all_podcast = PODCAST_VOICES["male"] + PODCAST_VOICES["female"]
        all_expert = EXPERT_VOICES["male"] + EXPERT_VOICES["female"]

        assert host in all_podcast
        assert interviewee in all_expert

    def test_host_only_configured_uses_explicit_host(self):
        """When only host is configured, use it and randomly select interviewee."""
        s = make_settings(voices={"host": "pNInz6obpgDQGcFmaJgB"})
        with patch("peripatos_core.registry.random.choice") as mock_choice:
            mock_choice.side_effect = [
                "male",
                EXPERT_VOICES["female"][0],
            ]
            host, interviewee, host_gender, interviewee_gender = _resolve_elevenlabs_voices(s)

        assert host == "pNInz6obpgDQGcFmaJgB"
        assert interviewee == EXPERT_VOICES["female"][0]
        assert host_gender == "male"
        assert interviewee_gender == "female"

    def test_interviewee_only_configured_uses_explicit_interviewee(self):
        """When only interviewee is configured, use it and randomly select host."""
        s = make_settings()
        s.tts.voices.host = ""
        s.tts.voices.interviewee = "EXAVITQu4vr4xnSDxMaL"

        with patch("peripatos_core.registry.random.choice") as mock_choice:
            mock_choice.side_effect = [
                "female",
                PODCAST_VOICES["female"][0],
            ]
            host, interviewee, host_gender, interviewee_gender = _resolve_elevenlabs_voices(s)

        assert host == PODCAST_VOICES["female"][0]
        assert interviewee == "EXAVITQu4vr4xnSDxMaL"
        assert host_gender == "female"
        assert interviewee_gender == "male"


# ─────────────────────────────────────────────────────────────────
# ElevenLabsTTSProvider tests
# ─────────────────────────────────────────────────────────────────


class TestElevenLabsTTSProviderConstructor:
    """Tests for ElevenLabsTTSProvider.__init__."""

    def test_requires_api_key(self):
        """Constructor raises ConfigError when api_key is empty."""
        cfg = make_tts_config(api_key="")
        with pytest.raises(ConfigError, match="api_key"):
            ElevenLabsTTSProvider(cfg)

    def test_accepts_valid_api_key(self):
        """Constructor succeeds when api_key is provided."""
        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)
        assert provider._api_key == "valid-key"

    def test_consecutive_failures_initialized_zero(self):
        """Circuit breaker counter starts at 0."""
        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)
        assert provider._consecutive_failures == 0


class TestElevenLabsTTSSynthesize:
    """Tests for ElevenLabsTTSProvider.synthesize()."""

    def test_synthesize_requires_speaker_voice(self):
        """synthesize() raises ConfigError when no speaker_voice is provided."""
        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)
        with pytest.raises(ConfigError, match="voice_id"):
            provider.synthesize("Hello world", speaker_voice=None)

    @patch("requests.post")
    def test_successful_synthesis_returns_mp3(self, mock_post):
        """Successful synthesis returns a Path to an MP3 file with correct content."""
        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)

        test_audio_content = b"fake-mp3-binary-data"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = test_audio_content
        mock_post.return_value = mock_response

        result = provider.synthesize("Hello world", speaker_voice="pNInz6obpgDQGcFmaJgB")

        assert isinstance(result, Path)
        assert result.suffix == ".mp3"
        assert result.read_bytes() == test_audio_content
        assert result.stat().st_size > 0

    @patch("requests.post")
    def test_synthesis_correct_api_call(self, mock_post):
        """Verify the correct API endpoint, headers, and payload are sent."""
        cfg = make_tts_config(api_key="my-api-key")
        provider = ElevenLabsTTSProvider(cfg)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"fake-data"
        mock_post.return_value = mock_response

        provider.synthesize("Test text", speaker_voice="voice-abc123")

        mock_post.assert_called_once()
        call_args, call_kwargs = mock_post.call_args

        assert call_args[0] == "https://api.elevenlabs.io/v1/text-to-speech/voice-abc123"
        assert call_kwargs["headers"]["xi-api-key"] == "my-api-key"
        assert call_kwargs["headers"]["Content-Type"] == "application/json"
        assert call_kwargs["json"]["text"] == "Test text"
        assert call_kwargs["json"]["model_id"] == "eleven_multilingual_v2"
        assert call_kwargs["json"]["voice_settings"]["stability"] == 0.5
        assert call_kwargs["json"]["voice_settings"]["similarity_boost"] == 0.75
        assert call_kwargs["params"]["output_format"] == "mp3_44100_128"
        assert call_kwargs["timeout"] == 60.0

    @patch("requests.post")
    def test_401_raises_config_error(self, mock_post):
        """HTTP 401 response raises ConfigError immediately (no retry)."""
        cfg = make_tts_config(api_key="bad-key")
        provider = ElevenLabsTTSProvider(cfg)

        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response

        with pytest.raises(ConfigError, match="Invalid ElevenLabs API key"):
            provider.synthesize("Hello", speaker_voice="voice-1")

        assert mock_post.call_count == 1

    @patch("peripatos_core.providers.tts.time.sleep")
    @patch("requests.post")
    def test_429_retries_then_succeeds(self, mock_post, mock_sleep):
        """HTTP 429 is retried with backoff, then succeeds."""
        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)

        fail_response = Mock()
        fail_response.status_code = 429
        success_response = Mock()
        success_response.status_code = 200
        success_response.content = b"audio-data"
        mock_post.side_effect = [fail_response, success_response]

        result = provider.synthesize("Hello", speaker_voice="voice-1")

        assert mock_post.call_count == 2
        assert result.read_bytes() == b"audio-data"
        mock_sleep.assert_called_once()

    @patch("peripatos_core.providers.tts.time.sleep")
    @patch("requests.post")
    def test_5xx_retries_then_succeeds(self, mock_post, mock_sleep):
        """HTTP 500 error is retried with backoff, then succeeds."""
        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)

        fail_response = Mock()
        fail_response.status_code = 500
        success_response = Mock()
        success_response.status_code = 200
        success_response.content = b"recovered-data"
        mock_post.side_effect = [
            fail_response, fail_response, fail_response, success_response,
        ]

        result = provider.synthesize("Hello", speaker_voice="voice-1")

        assert mock_post.call_count == 4
        assert mock_sleep.call_count == 3
        assert result.read_bytes() == b"recovered-data"

    @patch("peripatos_core.providers.tts.time.sleep")
    @patch("requests.post")
    def test_exhausts_retries_raises_tts_error(self, mock_post, mock_sleep):
        """After max retries, raises TTSError."""
        from peripatos_core.exceptions import TTSError

        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)

        fail_response = Mock()
        fail_response.status_code = 500
        mock_post.return_value = fail_response

        with pytest.raises(TTSError, match="synthesis failed after"):
            provider.synthesize("Hello", speaker_voice="voice-1")

        assert mock_post.call_count == 5
        assert mock_sleep.call_count == 4

    @patch("requests.post")
    def test_circuit_breaker_opens_after_consecutive_failures(self, mock_post):
        """After 3 consecutive failures, circuit breaker opens and raises TTSError immediately."""
        from peripatos_core.exceptions import TTSError

        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)

        for _ in range(3):
            fail_response = Mock()
            fail_response.status_code = 500
            mock_post.return_value = fail_response
            with patch("peripatos_core.providers.tts.time.sleep"):
                with pytest.raises(TTSError, match="synthesis failed after"):
                    provider.synthesize("Hello", speaker_voice="voice-1")

        with pytest.raises(TTSError, match="circuit breaker"):
            provider.synthesize("Hello", speaker_voice="voice-1")

    @patch("requests.post")
    def test_empty_response_content_raises_tts_error(self, mock_post):
        """Empty response body raises TTSError."""
        from peripatos_core.exceptions import TTSError

        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b""
        mock_post.return_value = mock_response

        with pytest.raises(TTSError, match="empty response body"):
            provider.synthesize("Hello", speaker_voice="voice-1")

    @patch("requests.post")
    def test_unexpected_status_code_raises_tts_error(self, mock_post):
        """Non-200, non-401, non-429, non-5xx status raises TTSError."""
        from peripatos_core.exceptions import TTSError

        cfg = make_tts_config(api_key="valid-key")
        provider = ElevenLabsTTSProvider(cfg)

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        with patch("peripatos_core.providers.tts.time.sleep"):
            with pytest.raises(TTSError):
                provider.synthesize("Hello", speaker_voice="voice-1")


# ─────────────────────────────────────────────────────────────────
# Registry integration tests
# ─────────────────────────────────────────────────────────────────


class TestBuildTTSProviderElevenLabs:
    """Tests for build_tts_provider with ElevenLabs provider."""

    def test_build_elevenlabs_returns_elevenlabs_provider(self):
        """build_tts_provider('elevenlabs') creates an ElevenLabsTTSProvider."""
        cfg = make_tts_config(provider="elevenlabs", api_key="valid-key")
        provider = build_tts_provider(cfg)
        assert isinstance(provider, ElevenLabsTTSProvider)
        assert not isinstance(provider, CachedTTSProvider)

    def test_build_elevenlabs_without_api_key_raises(self):
        """build_tts_provider('elevenlabs') without api_key raises ConfigError."""
        cfg = make_tts_config(provider="elevenlabs", api_key="")
        with pytest.raises(ConfigError, match="api_key"):
            build_tts_provider(cfg)

    def test_build_elevenlabs_with_cache_mgr_wraps_in_cached(self, tmp_path):
        """build_tts_provider with CacheManager (audio enabled) wraps in CachedTTSProvider."""
        cfg = make_tts_config(provider="elevenlabs", api_key="valid-key")
        cache_mgr = CacheManager(
            base_dir=tmp_path,
            audio_enabled=True,
            dialogue_enabled=False,
        )
        provider = build_tts_provider(cfg, cache_mgr=cache_mgr)
        assert isinstance(provider, CachedTTSProvider)
        assert isinstance(provider._delegate, ElevenLabsTTSProvider)
        assert provider._provider_name == "elevenlabs"

    def test_build_elevenlabs_with_cache_disabled_returns_unwrapped(self, tmp_path):
        """build_tts_provider with CacheManager (audio disabled) returns unwrapped provider."""
        cfg = make_tts_config(provider="elevenlabs", api_key="valid-key")
        cache_mgr = CacheManager(
            base_dir=tmp_path,
            audio_enabled=False,
            dialogue_enabled=False,
        )
        provider = build_tts_provider(cfg, cache_mgr=cache_mgr)
        assert isinstance(provider, ElevenLabsTTSProvider)
        assert not isinstance(provider, CachedTTSProvider)

    def test_build_elevenlabs_with_none_cache_returns_unwrapped(self):
        """build_tts_provider with cache_mgr=None returns unwrapped provider."""
        cfg = make_tts_config(provider="elevenlabs", api_key="valid-key")
        provider = build_tts_provider(cfg, cache_mgr=None)
        assert isinstance(provider, ElevenLabsTTSProvider)
        assert not isinstance(provider, CachedTTSProvider)

    def test_build_invalid_provider_raises_config_error(self):
        """build_tts_provider with unknown provider raises ConfigError."""
        cfg = make_tts_config(provider="invalid_provider", api_key="x")
        with pytest.raises(ConfigError, match="Unknown TTS provider"):
            build_tts_provider(cfg)

    def test_build_elevenlabs_case_insensitive(self):
        """build_tts_provider handles 'ElevenLabs' (mixed case) correctly."""
        cfg = make_tts_config(provider="ElevenLabs", api_key="valid-key")
        provider = build_tts_provider(cfg)
        assert isinstance(provider, ElevenLabsTTSProvider)
