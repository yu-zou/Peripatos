"""Integration test for PDFParser with MinerU cloud API.

Tests the full parser path (MinerU Flash + PyMuPDF fallback) against real
APIs — NOT the full peripatos pipeline (fetch+parse+dialogue+audio).

For full end-to-end pipeline tests, see test_e2e.py.

Set RUN_INTEGRATION=1 to run. Requires network access to mineru.net.
Uses a minimal valid PDF fixture.

Note: To test MinerU Precision extract with a token, add
`parser.mineru_token` to your config.test.json.
"""
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def sample_pdf(tmp_path_factory):
    """Create a minimal valid PDF for integration testing."""
    tmp = tmp_path_factory.mktemp("integration")
    pdf = tmp / "sample.pdf"
    # This is a very minimal but valid PDF
    pdf.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/"
        b"Contents 4 0 R>>endobj\n"
        b"4 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n"
        b"endstream\nendobj\n"
        b"trailer<</Size 5/Root 1 0 R>>\n%%EOF"
    )
    return pdf


def test_mineru_flash_extract_no_token(sample_pdf):
    """Test PDFParser.parse() with MinerU Flash (no token).

    Exercises: MinerU cloud API call → fallback to PyMuPDF if unavailable.
    This does NOT test the full peripatos CLI pipeline.
    """
    from peripatos_core.parser import PDFParser

    parser = PDFParser(mineru_token=None)  # Flash mode — no auth
    result = parser.parse(sample_pdf)

    # We get some result regardless of MinerU vs PyMuPDF
    assert result.markdown, f"Expected non-empty markdown, got: {result.markdown!r}"
    assert isinstance(result.sections, list)