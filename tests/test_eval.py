"""Tests for evaluation corpus module."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from peripatos.eval.corpus import CorpusEntry, get_corpus, download_corpus


class TestCorpusEntry:
    """Test CorpusEntry dataclass."""

    def test_corpus_entry_creation(self):
        """Test creating a CorpusEntry."""
        entry = CorpusEntry(
            arxiv_id="2408.09869",
            category="table-heavy",
            pdf_url="https://arxiv.org/pdf/2408.09869",
            expected_elements=["tables", "metrics", "benchmarks"]
        )
        assert entry.arxiv_id == "2408.09869"
        assert entry.category == "table-heavy"
        assert entry.pdf_url == "https://arxiv.org/pdf/2408.09869"
        assert entry.expected_elements == ["tables", "metrics", "benchmarks"]

    def test_corpus_entry_fields_required(self):
        """Test that all CorpusEntry fields are required."""
        # Should fail without all fields
        with pytest.raises(TypeError):
            CorpusEntry(
                arxiv_id="2408.09869",
                category="table-heavy",
                pdf_url="https://arxiv.org/pdf/2408.09869"
                # Missing expected_elements
            )


class TestGetCorpus:
    """Test get_corpus() function."""

    def test_get_corpus_returns_5_entries(self):
        """Test that get_corpus returns exactly 5 entries."""
        corpus = get_corpus()
        assert len(corpus) == 5

    def test_get_corpus_returns_list(self):
        """Test that get_corpus returns a list."""
        corpus = get_corpus()
        assert isinstance(corpus, list)

    def test_get_corpus_contains_corpus_entries(self):
        """Test that get_corpus returns CorpusEntry objects."""
        corpus = get_corpus()
        for entry in corpus:
            assert isinstance(entry, CorpusEntry)

    def test_get_corpus_has_math_heavy(self):
        """Test that corpus contains math-heavy category."""
        corpus = get_corpus()
        categories = [entry.category for entry in corpus]
        assert "math-heavy" in categories

    def test_get_corpus_has_table_heavy(self):
        """Test that corpus contains table-heavy category."""
        corpus = get_corpus()
        categories = [entry.category for entry in corpus]
        assert "table-heavy" in categories

    def test_get_corpus_has_code_heavy(self):
        """Test that corpus contains code-heavy category."""
        corpus = get_corpus()
        categories = [entry.category for entry in corpus]
        assert "code-heavy" in categories

    def test_get_corpus_has_multi_column(self):
        """Test that corpus contains multi-column category."""
        corpus = get_corpus()
        categories = [entry.category for entry in corpus]
        assert "multi-column" in categories

    def test_get_corpus_has_figure_heavy(self):
        """Test that corpus contains figure-heavy category."""
        corpus = get_corpus()
        categories = [entry.category for entry in corpus]
        assert "figure-heavy" in categories

    def test_get_corpus_all_have_arxiv_ids(self):
        """Test that all corpus entries have ArXiv IDs."""
        corpus = get_corpus()
        for entry in corpus:
            assert entry.arxiv_id
            assert isinstance(entry.arxiv_id, str)
            assert len(entry.arxiv_id) > 0

    def test_get_corpus_all_have_pdf_urls(self):
        """Test that all corpus entries have PDF URLs."""
        corpus = get_corpus()
        for entry in corpus:
            assert entry.pdf_url
            assert entry.pdf_url.startswith("https://arxiv.org/pdf/")

    def test_get_corpus_all_have_expected_elements(self):
        """Test that all corpus entries have expected_elements."""
        corpus = get_corpus()
        for entry in corpus:
            assert entry.expected_elements
            assert isinstance(entry.expected_elements, list)
            assert len(entry.expected_elements) > 0


class TestDownloadCorpus:
    """Test download_corpus() function."""

    def test_download_corpus_creates_output_dir(self):
        """Test that download_corpus creates output directory if needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "corpus"
            assert not output_dir.exists()
            
            # Mock urllib to avoid actual downloads
            with patch("peripatos.eval.corpus.urllib.request.urlopen"):
                with patch("peripatos.eval.corpus.Path.write_bytes"):
                    download_corpus(str(output_dir))
            
            assert output_dir.exists()

    def test_download_corpus_returns_list_of_paths(self):
        """Test that download_corpus returns list of downloaded file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "corpus"
            
            with patch("peripatos.eval.corpus.urllib.request.urlopen"):
                with patch("peripatos.eval.corpus.Path.write_bytes"):
                    result = download_corpus(str(output_dir))
            
            assert isinstance(result, list)
            assert len(result) == 5

    def test_download_corpus_skips_existing_files(self):
        """Test that download_corpus skips download if file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "corpus"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            dummy_file = output_dir / "2408.09869.pdf"
            dummy_file.write_bytes(b"dummy content")
            
            mock_urlopen = MagicMock()
            mock_response = MagicMock()
            mock_response.read.return_value = b"new content"
            mock_response.__enter__.return_value = mock_response
            mock_urlopen.return_value = mock_response
            
            with patch("peripatos.eval.corpus.urllib.request.urlopen", mock_urlopen):
                download_corpus(str(output_dir))
            
            assert dummy_file.exists()
            original_content = dummy_file.read_bytes()
            assert original_content == b"dummy content"

    def test_download_corpus_naming_convention(self):
        """Test that downloaded files follow {arxiv_id}.pdf naming convention."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "corpus"
            
            with patch("peripatos.eval.corpus.urllib.request.urlopen"):
                with patch("peripatos.eval.corpus.Path.write_bytes"):
                    result = download_corpus(str(output_dir))
            
            for path in result:
                assert path.endswith(".pdf")


class TestIntegration:
    """Integration tests for corpus module."""

    def test_corpus_entry_integration(self):
        """Test CorpusEntry with get_corpus data."""
        corpus = get_corpus()
        
        # Test first entry is valid
        entry = corpus[0]
        assert entry.arxiv_id
        assert entry.category in [
            "math-heavy", "table-heavy", "code-heavy", "multi-column", "figure-heavy"
        ]
        assert entry.pdf_url == f"https://arxiv.org/pdf/{entry.arxiv_id}"

    def test_download_corpus_integration_structure(self):
        """Test download_corpus creates expected output structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "corpus"
            
            with patch("peripatos.eval.corpus.urllib.request.urlopen"):
                with patch("peripatos.eval.corpus.Path.write_bytes"):
                    paths = download_corpus(str(output_dir))
            
            # Should return 5 paths (one per corpus entry)
            assert len(paths) == 5
            
            # All paths should be strings or Path objects
            for path in paths:
                assert isinstance(path, (str, Path))


class DummyDocument:
    def __init__(self, markdown: str) -> None:
        self._markdown = markdown

    def export_to_markdown(self) -> str:
        return self._markdown


class DummyResult:
    def __init__(self, markdown: str) -> None:
        self.document = DummyDocument(markdown)


class DummyConverter:
    def __init__(self, markdown: str) -> None:
        self._markdown = markdown
        self.calls: list[Path] = []

    def convert(self, source_path: Path) -> DummyResult:
        self.calls.append(source_path)
        return DummyResult(self._markdown)


class TestComparison:
    def test_run_comparison_custom_metrics(self, tmp_path: Path) -> None:
        from peripatos.eval.compare import run_comparison

        base_md = "# Title\n\nThis is base.\n|a|b|\n"
        vlm_md = "# Title\n\nThis is vlm.\n|a|b|\n|c|d|\n$$x$$\n"
        base_converter = DummyConverter(base_md)
        vlm_converter = DummyConverter(vlm_md)

        source_path = tmp_path / "paper.pdf"
        source_path.write_text("dummy")

        result = run_comparison(
            source_path,
            base_converter=base_converter,
            vlm_converter=vlm_converter,
        )

        assert result.paper_id == "paper"
        assert result.base_markdown == base_md
        assert result.vlm_markdown == vlm_md
        assert result.base_metrics["table_count"] == 1
        assert result.vlm_metrics["table_count"] == 2
        assert result.vlm_metrics["equation_count"] == 1
        assert result.deltas["table_count"] > 0
        assert result.timing["base_seconds"] >= 0
        assert result.timing["vlm_seconds"] >= 0
        assert result.used_docling_eval is False
        assert base_converter.calls == [source_path]
        assert vlm_converter.calls == [source_path]


class TestReportGeneration:
    def test_generate_report_sections_and_recommendation(self) -> None:
        from peripatos.eval.compare import ComparisonResult
        from peripatos.eval.report import generate_report

        result = ComparisonResult(
            paper_id="paper",
            source_path=Path("/tmp/paper.pdf"),
            base_markdown="# Title\nbase",
            vlm_markdown="# Title\nvlm",
            base_metrics={
                "table_count": 10,
                "equation_count": 10,
                "heading_count": 10,
            },
            vlm_metrics={
                "table_count": 11,
                "equation_count": 12,
                "heading_count": 9,
            },
            deltas={
                "table_count": 10.0,
                "equation_count": 20.0,
                "heading_count": -10.0,
            },
            timing={"base_seconds": 1.0, "vlm_seconds": 2.0},
            used_docling_eval=False,
        )

        report = generate_report([result])

        assert "## Summary" in report
        assert "## Per-Paper Results" in report
        assert "## Metrics" in report
        assert "## Timing" in report
        assert "## Recommendation" in report
        assert "ADOPT" in report
