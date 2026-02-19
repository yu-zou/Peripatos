"""Bilingual code-switching functionality for Chinese+English dialogue generation.

This module provides:
1. BilingualProcessor: Processes dialogue scripts to preserve technical terms in English
2. get_bilingual_prompt_modifier: Generates prompt instructions for bilingual output
"""

import re
from typing import Final

from peripatos.models import DialogueScript, DialogueTurn, LanguageMode


# Technical terms that must remain in English when using ZH_EN mode
TECHNICAL_TERMS: Final[frozenset[str]] = frozenset(
    {
        "Transformer",
        "Attention Mechanism",
        "Self-Attention",
        "Cross-Attention",
        "Multi-Head Attention",
        "Gradient Descent",
        "Stochastic Gradient Descent",
        "Loss Function",
        "Backpropagation",
        "Neural Network",
        "Encoder",
        "Decoder",
        "Embedding",
        "Optimizer",
        "Regularization",
        "Overfitting",
        "Underfitting",
        "Hyperparameter",
        "Convolutional",
        "Recurrent",
        "LSTM",
        "GRU",
        "Softmax",
        "ReLU",
        "Sigmoid",
        "Batch Normalization",
        "Layer Normalization",
        "Dropout",
        "Attention",
        "Query",
        "Key",
        "Value",
        "Feed-Forward",
        "Residual Connection",
        "Positional Encoding",
        "Token",
        "Vocabulary",
        "Cross-Entropy",
        "Activation Function",
    }
)


def get_bilingual_prompt_modifier(language_mode: LanguageMode) -> str:
    """Generate prompt instruction for bilingual code-switching.

    Args:
        language_mode: The target language mode for dialogue generation

    Returns:
        Prompt modifier string to append to system prompts.
        Empty string for EN mode (no modification needed).
    """
    if language_mode == LanguageMode.ZH_EN:
        return (
            "Explain the concepts in Mandarin Chinese (简体中文), "
            "but keep all technical terms in English. "
            "For example, say 'Transformer 模型' not '变换器模型'. "
            "This helps listeners learn technical vocabulary precisely."
        )
    return ""


class BilingualProcessor:
    """Processes dialogue scripts for bilingual code-switching (Chinese + English).

    For ZH_EN mode:
    - Ensures technical terms from the whitelist remain in English
    - Preserves mixed-language text structure for TTS compatibility

    For EN mode:
    - Returns script unchanged (pass-through)
    """

    def process(self, script: DialogueScript) -> DialogueScript:
        """Process a dialogue script for bilingual requirements.

        Args:
            script: The dialogue script to process

        Returns:
            Processed dialogue script with technical terms preserved in English
            (for ZH_EN mode) or unchanged (for EN mode)
        """
        if script.language_mode != LanguageMode.ZH_EN:
            # EN mode: pass through unchanged
            return script

        # Process each turn to preserve technical terms
        processed_turns = [
            DialogueTurn(
                speaker=turn.speaker,
                text=self._preserve_technical_terms(turn.text),
                section_ref=turn.section_ref,
            )
            for turn in script.turns
        ]

        return DialogueScript(
            paper_metadata=script.paper_metadata,
            turns=processed_turns,
            persona_type=script.persona_type,
            language_mode=script.language_mode,
        )

    def _preserve_technical_terms(self, text: str) -> str:
        """Ensure technical terms in the whitelist remain in English.

        This is a safety check - the LLM should already produce correct output
        via the bilingual prompt modifier, but this validates/enforces the whitelist.

        Args:
            text: The dialogue text to process

        Returns:
            Text with technical terms preserved in English
        """
        # For now, trust the LLM output - the prompt modifier should handle this
        # In the future, we could add regex-based validation/correction here
        # if we detect terms being translated incorrectly

        # Current strategy: Pass through (LLM does the heavy lifting via prompts)
        # This method exists as a hook for future enhancements
        return text