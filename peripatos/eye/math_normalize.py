"""Mathematical notation normalization."""

import re
from typing import Dict, Tuple


class MathNormalizer:
    """Convert LaTeX math notation to spoken English text."""

    def __init__(self):
        """Initialize the normalizer with regex patterns."""
        # Greek letters mapping
        self.greek_letters: Dict[str, str] = {
            r'\alpha': 'alpha',
            r'\beta': 'beta',
            r'\gamma': 'gamma',
            r'\delta': 'delta',
            r'\epsilon': 'epsilon',
            r'\zeta': 'zeta',
            r'\eta': 'eta',
            r'\theta': 'theta',
            r'\iota': 'iota',
            r'\kappa': 'kappa',
            r'\lambda': 'lambda',
            r'\mu': 'mu',
            r'\nu': 'nu',
            r'\xi': 'xi',
            r'\pi': 'pi',
            r'\rho': 'rho',
            r'\sigma': 'sigma',
            r'\tau': 'tau',
            r'\upsilon': 'upsilon',
            r'\phi': 'phi',
            r'\chi': 'chi',
            r'\psi': 'psi',
            r'\omega': 'omega',
            # Uppercase
            r'\Gamma': 'Gamma',
            r'\Delta': 'Delta',
            r'\Theta': 'Theta',
            r'\Lambda': 'Lambda',
            r'\Xi': 'Xi',
            r'\Pi': 'Pi',
            r'\Sigma': 'Sigma',
            r'\Upsilon': 'Upsilon',
            r'\Phi': 'Phi',
            r'\Psi': 'Psi',
            r'\Omega': 'Omega',
        }

        # Operators mapping
        self.operators: Dict[str, str] = {
            r'\sum': 'the sum of',
            r'\prod': 'the product of',
            r'\int': 'the integral of',
            r'\partial': 'the partial derivative of',
        }

        # Comparison operators
        self.comparisons: Dict[str, str] = {
            r'\leq': 'less than or equal to',
            r'\geq': 'greater than or equal to',
            r'\neq': 'not equal to',
            r'\approx': 'approximately equal to',
            r'\equiv': 'equivalent to',
        }

    def normalize(self, markdown: str) -> str:
        """
        Normalize LaTeX math in markdown to spoken English.

        Args:
            markdown: Input markdown text with LaTeX math expressions

        Returns:
            Markdown with math expressions converted to spoken text
        """
        # Process display math first (to avoid conflicts with inline)
        # Handle $$...$$ delimiters
        markdown = re.sub(
            r'\$\$(.*?)\$\$',
            lambda m: self._normalize_math(m.group(1)),
            markdown,
            flags=re.DOTALL
        )

        # Handle \[...\] delimiters
        markdown = re.sub(
            r'\\\[(.*?)\\\]',
            lambda m: self._normalize_math(m.group(1)),
            markdown,
            flags=re.DOTALL
        )

        # Process inline math $...$
        markdown = re.sub(
            r'\$(.*?)\$',
            lambda m: self._normalize_math(m.group(1)),
            markdown
        )

        return markdown

    def _normalize_math(self, math_expr: str) -> str:
        """
        Normalize a single math expression to spoken text.

        Args:
            math_expr: LaTeX math expression (without delimiters)

        Returns:
            Spoken English equivalent
        """
        # Strip whitespace
        result = math_expr.strip()

        # Apply transformations in order
        result = self._normalize_fractions(result)
        result = self._normalize_sqrt(result)
        result = self._normalize_operators(result)
        result = self._normalize_comparisons(result)
        result = self._normalize_greek(result)
        result = self._normalize_subscripts(result)
        result = self._normalize_exponents(result)

        return result

    def _normalize_fractions(self, expr: str) -> str:
        """Convert \\frac{a}{b} to 'a over b'."""
        # Handle nested braces by using non-greedy matching
        pattern = r'\\frac\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        def replace_frac(match):
            numerator = match.group(1)
            denominator = match.group(2)
            return f"{numerator} over {denominator}"
        
        # Apply multiple times to handle nested fractions
        prev = None
        while prev != expr:
            prev = expr
            expr = re.sub(pattern, replace_frac, expr)
        
        return expr

    def _normalize_sqrt(self, expr: str) -> str:
        """Convert \\sqrt{x} to 'the square root of x'."""
        pattern = r'\\sqrt\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        def replace_sqrt(match):
            content = match.group(1)
            return f"the square root of {content}"
        
        return re.sub(pattern, replace_sqrt, expr)

    def _normalize_operators(self, expr: str) -> str:
        """Convert operators like \\sum, \\prod to spoken form."""
        for latex, spoken in self.operators.items():
            # Use word boundaries to avoid partial replacements
            expr = expr.replace(latex, spoken)
        return expr

    def _normalize_comparisons(self, expr: str) -> str:
        """Convert comparison operators to spoken form."""
        for latex, spoken in self.comparisons.items():
            expr = expr.replace(latex, spoken)
        return expr

    def _normalize_greek(self, expr: str) -> str:
        """Convert Greek letters to their names."""
        for latex, name in self.greek_letters.items():
            expr = expr.replace(latex, name)
        return expr

    def _normalize_exponents(self, expr: str) -> str:
        """Convert exponents like x^2, x^n to spoken form."""
        # Handle x^{...} with braces
        expr = re.sub(
            r'(\w+)\^\{([^{}]+)\}',
            lambda m: f"{m.group(1)} to the power of {m.group(2)}",
            expr
        )
        
        # Handle special cases: ^2 -> squared, ^3 -> cubed
        expr = re.sub(
            r'(\w+)\^2(?!\w)',
            r'\1 squared',
            expr
        )
        expr = re.sub(
            r'(\w+)\^3(?!\w)',
            r'\1 cubed',
            expr
        )
        
        # Handle simple exponents x^n (single character)
        expr = re.sub(
            r'(\w+)\^(\w)',
            lambda m: f"{m.group(1)} to the power of {m.group(2)}",
            expr
        )
        
        return expr

    def _normalize_subscripts(self, expr: str) -> str:
        """Convert subscripts like x_i to spoken form."""
        # For now, just remove the underscore and keep adjacent
        # x_i becomes "x i", x_{ij} becomes "x ij"
        expr = re.sub(r'_\{([^{}]+)\}', r' \1', expr)
        expr = re.sub(r'_(\w)', r' \1', expr)
        return expr
