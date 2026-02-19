import importlib
import json
import time

from peripatos.brain.personas import get_persona_prompts
from peripatos.config import PeripatosConfig
from peripatos.models import (
    DialogueScript,
    DialogueTurn,
    LanguageMode,
    LLMProvider,
    PaperMetadata,
    PersonaType,
    SectionInfo,
    SpeakerRole,
)


class GenerationError(Exception):
    pass


class DialogueGenerator:
    def __init__(self, max_chunk_size: int = 2000, max_retries: int = 3) -> None:
        self.max_chunk_size = max_chunk_size
        self.max_retries = max_retries
        self._openai_client = None
        self._anthropic_client = None
        self._openrouter_client = None
        self._gemini_client = None
        self._gemini_types = None

    def generate(self, paper: PaperMetadata, config: PeripatosConfig) -> DialogueScript:
        persona_type = self._resolve_persona(config.persona)
        language_mode = self._resolve_language(config.language)
        prompts = get_persona_prompts(persona_type)
        system_prompt = self._build_system_prompt(prompts)

        turns: list[DialogueTurn] = []
        for section in paper.sections:
            chunks = self._chunk_text(section.content)
            for chunk in chunks:
                content = self._build_user_prompt(section, chunk)
                response_text = self._call_llm(config, system_prompt, content)
                turns.extend(self._parse_response(response_text, section.title))

        return DialogueScript(
            paper_metadata=paper,
            turns=turns,
            persona_type=persona_type,
            language_mode=language_mode,
        )

    def _resolve_persona(self, persona: str) -> PersonaType:
        try:
            return PersonaType(persona)
        except ValueError as exc:
            raise GenerationError(f"Unknown persona '{persona}'") from exc

    def _resolve_language(self, language: str) -> LanguageMode:
        if language == "en":
            return LanguageMode.EN
        if language == "zh-en":
            return LanguageMode.ZH_EN
        raise GenerationError(f"Unknown language '{language}'")

    def _build_system_prompt(self, prompts: dict) -> str:
        return (
            "Generate a dialogue between HOST and EXPERT. "
            "HOST role: "
            f"{prompts['host_system']} "
            "EXPERT role: "
            f"{prompts['expert_system']} "
            "Output ONLY a JSON array of objects with keys 'speaker' and 'text'. "
            "Speaker must be HOST or EXPERT."
        )

    def _build_user_prompt(self, section: SectionInfo, content: str) -> str:
        return f"Section: {section.title}\n\n{content}"

    def _call_llm(self, config: PeripatosConfig, system_prompt: str, content: str) -> str:
        try:
            provider = LLMProvider(config.llm_provider)
        except ValueError as exc:
            raise GenerationError(f"Unsupported LLM provider '{config.llm_provider}'") from exc
        if provider == LLMProvider.OPENAI:
            return self._call_openai(config, system_prompt, content)
        if provider == LLMProvider.ANTHROPIC:
            return self._call_anthropic(config, system_prompt, content)
        if provider == LLMProvider.OPENROUTER:
            return self._call_openrouter(config, system_prompt, content)
        if provider == LLMProvider.GEMINI:
            return self._call_gemini(config, system_prompt, content)
        raise GenerationError(f"Unsupported LLM provider '{config.llm_provider}'")

    def _call_openai(self, config: PeripatosConfig, system_prompt: str, content: str) -> str:
        if self._openai_client is None:
            try:
                openai_module = importlib.import_module("openai")
            except ImportError as exc:
                raise GenerationError("OpenAI client not available") from exc
            self._openai_client = openai_module.OpenAI(api_key=config.openai_api_key)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                completion = self._openai_client.chat.completions.create(
                    model=config.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content},
                    ],
                )
                return completion.choices[0].message.content
            except Exception as exc:
                last_error = exc
                if "rate_limit" in str(exc).lower():
                    time.sleep(2 ** attempt)
                    continue
                raise GenerationError(f"OpenAI API call failed: {exc}") from exc

        raise GenerationError(f"OpenAI API call failed: {last_error}")

    def _call_anthropic(self, config: PeripatosConfig, system_prompt: str, content: str) -> str:
        if self._anthropic_client is None:
            try:
                anthropic_module = importlib.import_module("anthropic")
            except ImportError as exc:
                raise GenerationError("Anthropic client not available") from exc
            self._anthropic_client = anthropic_module.Anthropic(api_key=config.anthropic_api_key)

        last_error = None
        for attempt in range(self.max_retries):
            try:
                message = self._anthropic_client.messages.create(
                    model=config.llm_model,
                    system=system_prompt,
                    messages=[{"role": "user", "content": content}],
                )
                return message.content[0].text
            except Exception as exc:
                last_error = exc
                if "rate_limit" in str(exc).lower():
                    time.sleep(2 ** attempt)
                    continue
                raise GenerationError(f"Anthropic API call failed: {exc}") from exc

        raise GenerationError(f"Anthropic API call failed: {last_error}")

    def _call_openrouter(self, config: PeripatosConfig, system_prompt: str, content: str) -> str:
        if self._openrouter_client is None:
            try:
                openai_module = importlib.import_module("openai")
            except ImportError as exc:
                raise GenerationError("OpenAI client not available (required for OpenRouter)") from exc
            self._openrouter_client = openai_module.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=config.openrouter_api_key
            )

        last_error = None
        for attempt in range(self.max_retries):
            try:
                completion = self._openrouter_client.chat.completions.create(
                    model=config.llm_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content},
                    ],
                )
                return completion.choices[0].message.content
            except Exception as exc:
                last_error = exc
                if "rate_limit" in str(exc).lower():
                    time.sleep(2 ** attempt)
                    continue
                raise GenerationError(f"OpenRouter API call failed: {exc}") from exc

        raise GenerationError(f"OpenRouter API call failed: {last_error}")

    def _call_gemini(self, config: PeripatosConfig, system_prompt: str, content: str) -> str:
        if self._gemini_client is None:
            try:
                genai_module = importlib.import_module("google.genai")
                types_module = importlib.import_module("google.genai.types")
            except ImportError as exc:
                raise GenerationError("Google GenAI client not available") from exc
            self._gemini_client = genai_module.Client(api_key=config.gemini_api_key)
            self._gemini_types = types_module

        last_error = None
        for attempt in range(self.max_retries):
            try:
                gen_config = self._gemini_types.GenerateContentConfig(  # pyright: ignore[reportOptionalMemberAccess]
                    system_instruction=system_prompt
                )
                response = self._gemini_client.models.generate_content(
                    model=config.llm_model,
                    contents=content,
                    config=gen_config
                )
                return response.text
            except Exception as exc:
                last_error = exc
                if ("rate_limit" in str(exc).lower() or 
                    "resource_exhausted" in str(exc).lower() or 
                    "429" in str(exc)):
                    time.sleep(2 ** attempt)
                    continue
                raise GenerationError(f"Gemini API call failed: {exc}") from exc

        raise GenerationError(f"Gemini API call failed: {last_error}")

    def _parse_response(self, response_text: str, section_ref: str) -> list[DialogueTurn]:
        try:
            payload = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise GenerationError("Invalid JSON response from LLM") from exc

        if not isinstance(payload, list):
            raise GenerationError("Invalid JSON response from LLM")

        turns: list[DialogueTurn] = []
        for item in payload:
            speaker_value = str(item.get("speaker", "")).upper()
            if speaker_value == "HOST":
                speaker = SpeakerRole.HOST
            elif speaker_value == "EXPERT":
                speaker = SpeakerRole.EXPERT
            else:
                raise GenerationError("Invalid speaker value in JSON response")
            text = item.get("text", "")
            turns.append(DialogueTurn(speaker=speaker, text=text, section_ref=section_ref))
        return turns

    def _chunk_text(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.max_chunk_size:
            return [text]

        boundaries = {". ", "? ", "! "}
        chunks = []
        current = ""
        i = 0
        while i < len(text):
            current += text[i]
            if i + 1 < len(text):
                two_char = text[i : i + 2]
                if two_char in boundaries:
                    current += text[i + 1]
                    if len(current) >= self.max_chunk_size:
                        chunks.append(current)
                        current = ""
                    else:
                        chunks.append(current)
                        current = ""
                    i += 2
                    continue
            if len(current) >= self.max_chunk_size:
                chunks.append(current)
                current = ""
            i += 1

        if current:
            chunks.append(current)

        return chunks
