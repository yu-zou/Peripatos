"""Integration tests for VLM feature across parser, CLI, and evaluation framework."""

from __future__ import annotations

import builtins
import sys
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

from peripatos.eye.parser import PDFParser, ParsingError
from peripatos.models import PaperMetadata


# ============================================================================
# Test Fixtures and Stubs
# ============================================================================


class _StubVLMDocument:
    """Stub VLM document that exports to markdown."""

    def __init__(self, markdown: str) -> None:
        self._markdown = markdown

    def export_to_markdown(self) -> str:
        return self._markdown


class _StubVLMResult:
    """Stub VLM conversion result."""

    def __init__(self, markdown: str) -> None:
        self.document = _StubVLMDocument(markdown)


class _StubVLMConverter:
    """Stub VLM converter for testing."""

    def __init__(self, markdown: str | None = None) -> None:
        self.converted = False
        self._markdown = markdown or """# Integration Test Paper

Authors: Alice, Bob

## Abstract

This is a VLM-parsed abstract with enhanced extraction capabilities.

## 1. Introduction

Introduction section with detailed content from VLM parsing.

## 2. Methodology

Methodology section with equations $x = y + z$ and tables.

## 3. Experiments

Experimental results section.

## 4. Conclusion

Conclusion section summarizing findings.

## References

[1] Reference 1
[2] Reference 2
"""

    def convert(self, source: object) -> _StubVLMResult:
        self.converted = True
        return _StubVLMResult(self._markdown)


@pytest.fixture
def stub_vlm_converter() -> _StubVLMConverter:
    """Provides a stub VLM converter for integration tests."""
    return _StubVLMConverter()


@pytest.fixture
def mock_vlm_factory(stub_vlm_converter: _StubVLMConverter, monkeypatch: pytest.MonkeyPatch) -> _StubVLMConverter:
    """Mocks the VLM converter factory to return stub converter."""

    def _create_stub(**kwargs: Any) -> _StubVLMConverter:
        return stub_vlm_converter

    monkeypatch.setattr("peripatos.eye.vlm.create_vlm_converter", _create_stub)
    return stub_vlm_converter


# ============================================================================
# Parser Integration Tests
# ============================================================================


def test_parser_with_vlm_produces_valid_metadata(
    sample_pdf_path: Path, mock_vlm_factory: _StubVLMConverter
) -> None:
    """Test PDFParser(use_vlm=True) produces valid PaperMetadata end-to-end."""
    parser = PDFParser(use_vlm=True)
    metadata = parser.parse(sample_pdf_path)

    # Verify basic metadata
    assert isinstance(metadata, PaperMetadata)
    assert metadata.title == "Integration Test Paper"
    assert metadata.authors == ["Alice", "Bob"]
    assert "VLM-parsed abstract" in metadata.abstract
    assert metadata.source_path == sample_pdf_path

    # Verify sections
    assert len(metadata.sections) > 0
    section_titles = [s.title.lower() for s in metadata.sections]
    assert any("introduction" in t for t in section_titles)
    assert any("methodology" in t for t in section_titles)
    assert any("conclusion" in t for t in section_titles)

    # Verify converter was actually called
    assert mock_vlm_factory.converted is True


def test_parser_without_vlm_still_works(sample_pdf_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test backward compatibility: PDFParser() without use_vlm still works."""
    # Create a simple stub for standard converter
    standard_markdown = """# Standard Parser Paper

## Abstract

Standard parser abstract.

## 1. Introduction

Standard introduction.
"""

    class _StubStandardConverter:
        def convert(self, source: object) -> _StubVLMResult:
            return _StubVLMResult(standard_markdown)

    # Ensure VLM converter is NOT called
    vlm_called = {"value": False}

    def _fake_vlm_converter(**kwargs: Any) -> Any:
        vlm_called["value"] = True
        return _StubVLMConverter()

    monkeypatch.setattr("peripatos.eye.vlm.create_vlm_converter", _fake_vlm_converter)

    # Parse without VLM
    parser = PDFParser(converter=_StubStandardConverter())
    metadata = parser.parse(sample_pdf_path)

    # Verify standard parsing worked
    assert metadata.title == "Standard Parser Paper"
    assert "Standard parser abstract" in metadata.abstract

    # Verify VLM was NOT called (backward compatibility)
    assert vlm_called["value"] is False


def test_parser_vlm_handles_missing_dependencies(sample_pdf_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that helpful error is raised when VLM dependencies are missing."""
    original_import = builtins.__import__

    def _blocked_import(
        name: str,
        globals: dict[str, object] | None = None,
        locals: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name in {"torch", "transformers"}:
            raise ImportError("No module named 'torch'")
        return cast(object, original_import(name, globals, locals, fromlist, level))

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    parser = PDFParser(use_vlm=True)

    with pytest.raises(
        ImportError, match="VLM support requires additional dependencies. Install with: pip install peripatos\\[vlm\\]"
    ):
        parser.parse(sample_pdf_path)


def test_parser_vlm_handles_invalid_pdf_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that ParsingError is raised for nonexistent PDF paths."""

    def _fake_vlm_converter(**kwargs: Any) -> _StubVLMConverter:
        return _StubVLMConverter()

    monkeypatch.setattr("peripatos.eye.vlm.create_vlm_converter", _fake_vlm_converter)

    parser = PDFParser(use_vlm=True)

    with pytest.raises(ParsingError, match="PDF not found"):
        parser.parse("/nonexistent/path/paper.pdf")


# ============================================================================
# CLI Integration Tests
# ============================================================================


def test_cli_vlm_flag_integration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that --vlm flag is properly parsed and accessible in CLI."""
    from peripatos.cli import create_parser

    parser = create_parser()
    args = parser.parse_args(["generate", "2408.09869", "--vlm"])

    vlm = cast(bool, args.vlm)
    assert vlm is True


def test_cli_vlm_flag_defaults_to_false() -> None:
    """Test that VLM flag defaults to False for backward compatibility."""
    from peripatos.cli import create_parser

    parser = create_parser()
    args = parser.parse_args(["generate", "2408.09869"])

    vlm = cast(bool, getattr(args, "vlm", False))
    assert vlm is False


def test_cli_vlm_flag_in_help_text(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --vlm flag is documented in CLI help."""
    from peripatos.cli import create_parser

    parser = create_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["generate", "--help"])
    captured = capsys.readouterr()

    assert "--vlm" in captured.out
    assert "Granite Docling VLM" in captured.out or "vlm" in captured.out.lower()


# ============================================================================
# Evaluation Framework Integration Tests
# ============================================================================


def test_eval_run_comparison_with_vlm_converter(tmp_path: Path) -> None:
    """Test that run_comparison() works with VLM converter."""
    from peripatos.eval.compare import run_comparison

    # Create a test PDF file
    test_pdf = tmp_path / "test_paper.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 stub")

    # Create stub converters
    base_markdown = "# Base Paper\n\n## Abstract\n\nBase abstract with 50 chars."
    vlm_markdown = "# VLM Paper\n\n## Abstract\n\nVLM abstract with enhanced extraction (60 chars)."

    base_converter = _StubVLMConverter(markdown=base_markdown)
    vlm_converter = _StubVLMConverter(markdown=vlm_markdown)

    # Run comparison
    result = run_comparison(test_pdf, base_converter=base_converter, vlm_converter=vlm_converter)

    # Verify result structure
    assert result.paper_id == "test_paper"
    assert result.source_path == test_pdf
    assert result.base_markdown == base_markdown
    assert result.vlm_markdown == vlm_markdown

    # Verify metrics computed
    assert "char_count" in result.base_metrics
    assert "char_count" in result.vlm_metrics
    assert "char_count" in result.deltas

    # Verify timing recorded
    assert "base_seconds" in result.timing
    assert "vlm_seconds" in result.timing
    assert result.timing["base_seconds"] >= 0
    assert result.timing["vlm_seconds"] >= 0


def test_eval_comparison_metrics_differ_correctly(tmp_path: Path) -> None:
    """Test that evaluation metrics correctly capture differences between base and VLM."""
    from peripatos.eval.compare import run_comparison

    test_pdf = tmp_path / "comparison_test.pdf"
    test_pdf.write_bytes(b"%PDF-1.4 stub")

    # Base: 1 table, 1 equation, 100 chars
    base_markdown = """# Base
| col1 | col2 |
|------|------|
| a    | b    |

$$x = y$$

Content here."""

    # VLM: 2 tables, 2 equations, 200 chars (approximately)
    vlm_markdown = """# VLM Enhanced
| col1 | col2 |
|------|------|
| a    | b    |

| col3 | col4 |
|------|------|
| c    | d    |

$$x = y$$
$$a = b$$

Enhanced content with more detail and additional information."""

    base_converter = _StubVLMConverter(markdown=base_markdown)
    vlm_converter = _StubVLMConverter(markdown=vlm_markdown)

    result = run_comparison(test_pdf, base_converter=base_converter, vlm_converter=vlm_converter)

    # Base should have fewer chars, tables, equations than VLM
    assert result.vlm_metrics["char_count"] > result.base_metrics["char_count"]
    assert result.vlm_metrics["table_count"] > result.base_metrics["table_count"]
    assert result.vlm_metrics["equation_count"] > result.base_metrics["equation_count"]

    # Deltas should reflect positive percentage increases
    assert result.deltas["char_count"] > 0
    assert result.deltas["table_count"] > 0
    assert result.deltas["equation_count"] > 0


# ============================================================================
# End-to-End Integration Test
# ============================================================================


def test_end_to_end_vlm_workflow(sample_pdf_path: Path, mock_vlm_factory: _StubVLMConverter) -> None:
    """Test complete workflow: parse PDF with VLM, verify output, ensure no errors."""
    # Step 1: Parse PDF with VLM
    parser = PDFParser(use_vlm=True)
    metadata = parser.parse(sample_pdf_path)

    # Step 2: Verify parsing succeeded
    assert metadata.title
    assert metadata.abstract
    assert len(metadata.sections) > 0

    # Step 3: Verify sections have expected structure
    has_abstract = any(s.title.lower() == "abstract" for s in metadata.sections)
    has_introduction = any("introduction" in s.title.lower() for s in metadata.sections)
    assert has_abstract or has_introduction  # At least one key section

    # Step 4: Verify content is not empty
    total_content_length = sum(len(s.content) for s in metadata.sections)
    assert total_content_length > 100  # Reasonable content extracted

    # Step 5: Verify VLM converter was invoked
    assert mock_vlm_factory.converted is True
