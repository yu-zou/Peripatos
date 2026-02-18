"""Edge TTS engine for offline speech synthesis."""

import asyncio
import edge_tts


class TTSError(Exception):
    """Exception raised for TTS engine errors."""

    pass


class EdgeTTSEngine:
    """Text-to-speech engine using edge-tts (Microsoft Edge service)."""

    # Default voice mappings
    VOICES = {
        "en": {
            "host": "en-US-AriaNeural",  # Conversational female voice
            "expert": "en-US-GuyNeural",  # Deeper male voice
        },
        "zh": {
            "host": "zh-CN-XiaoxiaoNeural",  # Chinese female voice
            "expert": "zh-CN-YunxiNeural",  # Chinese male voice
        },
    }

    def is_available(self) -> bool:
        """Check if TTS engine is available.
        
        Returns:
            bool: Always True, as edge-tts requires no API key.
        """
        return True

    def get_voices(self, language: str) -> dict:
        """Get available voices for a language.
        
        Args:
            language: Language code ('en' or 'zh')
            
        Returns:
            dict: Dictionary with 'host' and 'expert' voice names.
        """
        if language not in self.VOICES:
            raise TTSError(f"Unsupported language: {language}")
        
        return self.VOICES[language]

    async def synthesize(self, text: str, voice: str) -> bytes:
        """Synthesize speech from text using edge-tts.
        
        Args:
            text: Text to synthesize
            voice: Voice name (e.g., 'en-US-AriaNeural')
            
        Returns:
            bytes: Raw MP3 audio data
            
        Raises:
            TTSError: If synthesis fails
        """
        try:
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            return audio_data
            
        except Exception as e:
            raise TTSError(f"Failed to synthesize speech: {str(e)}")

    def synthesize_sync(self, text: str, voice: str) -> bytes:
        """Synchronous wrapper for synthesize() method.
        
        Args:
            text: Text to synthesize
            voice: Voice name (e.g., 'en-US-AriaNeural')
            
        Returns:
            bytes: Raw MP3 audio data
        """
        return asyncio.run(self.synthesize(text, voice))
