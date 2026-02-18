"""Tests for LaTeX math normalization."""

import pytest
from peripatos.eye.math_normalize import MathNormalizer


@pytest.fixture
def normalizer():
    """Create a MathNormalizer instance."""
    return MathNormalizer()


class TestSimpleInlineMath:
    """Test simple inline math normalization."""

    def test_exponent_squared(self, normalizer):
        """Test x^2 becomes 'x squared'."""
        result = normalizer.normalize("The equation is $x^2$.")
        assert result == "The equation is x squared."

    def test_exponent_cubed(self, normalizer):
        """Test x^3 becomes 'x cubed'."""
        result = normalizer.normalize("Volume is $x^3$.")
        assert result == "Volume is x cubed."

    def test_general_exponent(self, normalizer):
        """Test x^n becomes 'x to the power of n'."""
        result = normalizer.normalize("General form is $x^n$.")
        assert result == "General form is x to the power of n."

    def test_complex_exponent(self, normalizer):
        """Test complex exponents like x^{2n+1}."""
        result = normalizer.normalize("The term is $x^{2n+1}$.")
        assert result == "The term is x to the power of 2n+1."


class TestFractions:
    """Test fraction normalization."""

    def test_simple_fraction(self, normalizer):
        """Test \\frac{a}{b} becomes 'a over b'."""
        result = normalizer.normalize("The ratio is $\\frac{a}{b}$.")
        assert result == "The ratio is a over b."

    def test_numeric_fraction(self, normalizer):
        """Test \\frac{1}{N} becomes '1 over N'."""
        result = normalizer.normalize("The loss is $\\frac{1}{N}$")
        assert result == "The loss is 1 over N"

    def test_nested_fraction(self, normalizer):
        """Test nested fractions."""
        result = normalizer.normalize("Complex: $\\frac{x^2}{y}$.")
        assert "over" in result.lower()


class TestGreekLetters:
    """Test Greek letter normalization."""

    def test_alpha(self, normalizer):
        """Test \\alpha becomes 'alpha'."""
        result = normalizer.normalize("The parameter $\\alpha$ is important.")
        assert result == "The parameter alpha is important."

    def test_beta(self, normalizer):
        """Test \\beta becomes 'beta'."""
        result = normalizer.normalize("Set $\\beta$ to 0.5.")
        assert result == "Set beta to 0.5."

    def test_gamma(self, normalizer):
        """Test \\gamma becomes 'gamma'."""
        result = normalizer.normalize("The $\\gamma$ function.")
        assert result == "The gamma function."

    def test_multiple_greek(self, normalizer):
        """Test multiple Greek letters in one expression."""
        result = normalizer.normalize("Relation: $\\alpha + \\beta = \\gamma$.")
        assert "alpha" in result
        assert "beta" in result
        assert "gamma" in result


class TestOperators:
    """Test mathematical operator normalization."""

    def test_sum(self, normalizer):
        """Test \\sum becomes 'the sum of'."""
        result = normalizer.normalize("Total: $\\sum x_i$.")
        assert "sum" in result.lower()

    def test_product(self, normalizer):
        """Test \\prod becomes 'the product of'."""
        result = normalizer.normalize("Result: $\\prod x_i$.")
        assert "product" in result.lower()

    def test_integral(self, normalizer):
        """Test \\int becomes 'the integral of'."""
        result = normalizer.normalize("Area: $\\int f(x) dx$.")
        assert "integral" in result.lower()

    def test_partial(self, normalizer):
        """Test \\partial becomes 'the partial derivative of'."""
        result = normalizer.normalize("Gradient: $\\partial f$.")
        assert "partial" in result.lower()


class TestSqrt:
    """Test square root normalization."""

    def test_simple_sqrt(self, normalizer):
        """Test \\sqrt{x} becomes 'the square root of x'."""
        result = normalizer.normalize("Distance is $\\sqrt{x}$.")
        assert "square root" in result.lower()
        assert "of x" in result.lower()

    def test_complex_sqrt(self, normalizer):
        """Test \\sqrt{x^2 + y^2}."""
        result = normalizer.normalize("Norm: $\\sqrt{x^2 + y^2}$.")
        assert "square root" in result.lower()


class TestComparisons:
    """Test comparison operator normalization."""

    def test_leq(self, normalizer):
        """Test \\leq becomes 'less than or equal to'."""
        result = normalizer.normalize("Constraint: $x \\leq 1$.")
        assert "less than or equal to" in result.lower()

    def test_geq(self, normalizer):
        """Test \\geq becomes 'greater than or equal to'."""
        result = normalizer.normalize("Condition: $y \\geq 0$.")
        assert "greater than or equal to" in result.lower()


class TestNonMathText:
    """Test that non-math text is preserved."""

    def test_plain_text_unchanged(self, normalizer):
        """Test plain text without math is unchanged."""
        text = "This is just regular text with no math."
        result = normalizer.normalize(text)
        assert result == text

    def test_mixed_content(self, normalizer):
        """Test text with math and non-math content."""
        result = normalizer.normalize("The formula $x^2$ is simple, but important.")
        assert "The formula" in result
        assert "is simple, but important." in result
        assert "squared" in result


class TestComplexEquations:
    """Test complex nested LaTeX expressions."""

    def test_summation_with_bounds(self, normalizer):
        """Test \\sum_{i=1}^{N} x_i produces readable output."""
        result = normalizer.normalize("$\\sum_{i=1}^{N} x_i$")
        assert "sum" in result.lower()
        # Should be readable even if not perfect
        assert len(result) > 0
        assert "$" not in result

    def test_pythagorean_theorem(self, normalizer):
        """Test where x^2 + y^2 = r^2."""
        result = normalizer.normalize("where $x^2 + y^2 = r^2$")
        assert "squared" in result
        # Should handle multiple exponents
        assert result.count("squared") >= 2

    def test_display_math_double_dollar(self, normalizer):
        """Test display math with $$ delimiters."""
        result = normalizer.normalize("Equation:\n$$x^2 + y^2 = r^2$$\nEnd")
        assert "squared" in result
        assert "$$" not in result

    def test_display_math_brackets(self, normalizer):
        """Test display math with \\[ \\] delimiters."""
        result = normalizer.normalize("Formula:\n\\[x^2\\]\nDone")
        assert "squared" in result
        assert "\\[" not in result
        assert "\\]" not in result


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_string(self, normalizer):
        """Test empty string input."""
        result = normalizer.normalize("")
        assert result == ""

    def test_no_math(self, normalizer):
        """Test string with no math at all."""
        text = "Just plain text here."
        result = normalizer.normalize(text)
        assert result == text

    def test_multiple_inline_math(self, normalizer):
        """Test multiple inline math expressions."""
        result = normalizer.normalize("We have $x^2$ and $y^3$ here.")
        assert "x squared" in result
        assert "y cubed" in result

    def test_backslash_preservation(self, normalizer):
        """Test that backslashes in LaTeX are handled."""
        result = normalizer.normalize("The $\\alpha$ parameter.")
        assert "alpha" in result
        # No stray backslashes
        assert "\\" not in result or "\\n" in result  # Allow newlines

    def test_subscripts_handled(self, normalizer):
        """Test that subscripts like x_i are handled reasonably."""
        result = normalizer.normalize("Sum $\\sum x_i$ here.")
        # Should at least not crash and produce something
        assert len(result) > 0
        assert "$" not in result
