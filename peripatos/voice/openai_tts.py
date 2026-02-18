"""OpenAI text-to-speech integration."""

import os
import time
from typing import Optional
from openai import OpenAI
from openai import OpenAIError


class TTSError(Exception):
    """Exception raised for TTS-related errors."""
    pass


class OpenAITTSEngine:
    """OpenAI Text-to-Speech engine with smart chunking.
    
    This engine synthesizes speech using OpenAI's TTS API with the following features:
    - Smart chunking for texts exceeding 4096 character limit
    - Sentence boundary preservation
    - Clause boundary fallback for long sentences
    - Configurable voices for different speaker roles
    - Error handling with retry logic for rate limits
    
    Attributes:
        api_key: OpenAI API key. If None, attempts to read from environment.
        model: TTS model to use (default: "tts-1")
        max_chunk_size: Maximum characters per API request (default: 4096)
        max_retries: Maximum retry attempts for rate limits (default: 3)
    """
    
    # Character limit per OpenAI TTS API request
    DEFAULT_MAX_CHUNK_SIZE = 4096
    
    # Sentence boundary markers
    SENTENCE_BOUNDARIES = {'. ', '? ', '! '}
    
    # Clause boundary markers (for splitting long sentences)
    CLAUSE_BOUNDARIES = {', ', '; '}
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "tts-1",
        max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
        max_retries: int = 3
    ):
        """Initialize the OpenAI TTS engine.
        
        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            model: TTS model to use (default: "tts-1", alternative: "tts-1-hd")
            max_chunk_size: Maximum characters per chunk (default: 4096)
            max_retries: Maximum retry attempts for rate limits
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.max_chunk_size = max_chunk_size
        self.max_retries = max_retries
        self._client: Optional[OpenAI] = None
    
    def is_available(self) -> bool:
        """Check if the TTS engine is available.
        
        Returns:
            True if API key is present, False otherwise.
        """
        return bool(self.api_key)
    
    def synthesize(self, text: str, voice: str = "alloy") -> bytes:
        """Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer)
            
        Returns:
            Audio bytes in MP3 format
            
        Raises:
            TTSError: If synthesis fails or API key is missing
        """
        if not self.is_available():
            raise TTSError("OpenAI API key not available")
        
        # Initialize client lazily
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        
        # Split text into chunks if needed
        chunks = self._chunk_text(text)
        
        # Synthesize each chunk
        audio_parts = []
        for chunk in chunks:
            audio_bytes = self._synthesize_chunk(chunk, voice)
            audio_parts.append(audio_bytes)
        
        # Concatenate all audio parts
        return b"".join(audio_parts)
    
    def _synthesize_chunk(self, text: str, voice: str) -> bytes:
        """Synthesize a single chunk of text with retry logic.
        
        Args:
            text: Text chunk to synthesize (must be <= max_chunk_size)
            voice: Voice to use
            
        Returns:
            Audio bytes for this chunk
            
        Raises:
            TTSError: If synthesis fails after all retries
        """
        if not self._client:
            raise TTSError("OpenAI client not initialized")
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self._client.audio.speech.create(
                    model=self.model,
                    voice=voice,
                    input=text
                )
                return response.read()
            
            except OpenAIError as e:
                last_error = e
                # Check if it's a rate limit error
                if "rate_limit" in str(e).lower() and attempt < self.max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                # For other errors or last retry, raise immediately
                break
            
            except Exception as e:
                last_error = e
                break
        
        # If we get here, all retries failed
        raise TTSError(f"TTS synthesis failed: {last_error}")
    
    def _chunk_text(self, text: str) -> list[str]:
        """Split text into chunks respecting sentence and clause boundaries.
        
        Algorithm:
        1. If text <= max_chunk_size, return as-is
        2. Try to split at sentence boundaries (. ? !)
        3. For sentences > max_chunk_size, split at clause boundaries (, ;)
        4. Ensure no chunk exceeds max_chunk_size
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks, each <= max_chunk_size
        """
        if not text:
            return []
        
        if len(text) <= self.max_chunk_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # First, try to split into sentences
        sentences = self._split_into_sentences(text)
        
        for sentence in sentences:
            # If sentence itself is too long, split it further
            if len(sentence) > self.max_chunk_size:
                # Flush current chunk if it has content
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # Split long sentence at clause boundaries
                clause_chunks = self._split_long_sentence(sentence)
                chunks.extend(clause_chunks)
            
            # If adding this sentence would exceed limit, flush current chunk
            elif current_chunk and len(current_chunk) + len(sentence) > self.max_chunk_size:
                chunks.append(current_chunk)
                current_chunk = sentence
            
            # Otherwise, add to current chunk
            else:
                current_chunk += sentence
        
        # Add remaining chunk
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences at boundary markers.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences (with trailing punctuation and space preserved)
        """
        sentences = []
        current = ""
        
        i = 0
        while i < len(text):
            current += text[i]
            
            # Check if we're at a sentence boundary
            if i + 1 < len(text):
                two_char = text[i:i+2]
                if two_char in self.SENTENCE_BOUNDARIES:
                    # Include the space
                    current += text[i+1]
                    sentences.append(current)
                    current = ""
                    i += 2
                    continue
            
            i += 1
        
        # Add remaining text
        if current:
            sentences.append(current)
        
        return sentences
    
    def _split_long_sentence(self, sentence: str) -> list[str]:
        """Split a long sentence at clause boundaries.
        
        Args:
            sentence: Sentence that exceeds max_chunk_size
            
        Returns:
            List of chunks split at clause boundaries
        """
        if len(sentence) <= self.max_chunk_size:
            return [sentence]
        
        chunks = []
        current_chunk = ""
        
        i = 0
        while i < len(sentence):
            current_chunk += sentence[i]
            
            # Check if we're at a clause boundary and chunk is getting large
            if len(current_chunk) > self.max_chunk_size * 0.8 and i + 1 < len(sentence):
                two_char = sentence[i:i+2]
                if two_char in self.CLAUSE_BOUNDARIES:
                    # Include the space/punctuation
                    current_chunk += sentence[i+1]
                    chunks.append(current_chunk)
                    current_chunk = ""
                    i += 2
                    continue
            
            # Hard limit: if we hit max size, split here regardless
            if len(current_chunk) >= self.max_chunk_size:
                chunks.append(current_chunk)
                current_chunk = ""
            
            i += 1
        
        # Add remaining text
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks