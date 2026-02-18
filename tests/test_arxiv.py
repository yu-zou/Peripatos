"""Tests for ArXiv fetcher."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from peripatos.eye.arxiv import ArxivFetcher, FetchError


class TestArxivFetcher:
    """Test suite for ArxivFetcher."""

    def test_validate_id_accepts_valid_arxiv_id(self):
        """Test that validate_id accepts valid ArXiv ID format (YYMM.NNNNN)."""
        fetcher = ArxivFetcher()
        
        # Should not raise for valid IDs
        assert fetcher.validate_id("2408.09869") is True
        assert fetcher.validate_id("1234.56789") is True
        assert fetcher.validate_id("0001.01234") is True

    def test_validate_id_accepts_arxiv_id_with_version(self):
        """Test that validate_id accepts ArXiv ID with version suffix (vN)."""
        fetcher = ArxivFetcher()
        
        # Should not raise for valid IDs with versions
        assert fetcher.validate_id("2408.09869v1") is True
        assert fetcher.validate_id("2408.09869v2") is True
        assert fetcher.validate_id("2408.09869v10") is True

    def test_validate_id_rejects_invalid_format_with_dashes(self):
        """Test that validate_id rejects invalid format like 'not-an-id'."""
        fetcher = ArxivFetcher()
        
        with pytest.raises(FetchError):
            fetcher.validate_id("not-an-id")

    def test_validate_id_rejects_too_short_id(self):
        """Test that validate_id rejects ID that's too short (123.456)."""
        fetcher = ArxivFetcher()
        
        with pytest.raises(FetchError):
            fetcher.validate_id("123.456")

    def test_validate_id_rejects_empty_string(self):
        """Test that validate_id rejects empty string."""
        fetcher = ArxivFetcher()
        
        with pytest.raises(FetchError):
            fetcher.validate_id("")

    def test_validate_id_rejects_missing_dot(self):
        """Test that validate_id rejects ID without dot separator."""
        fetcher = ArxivFetcher()
        
        with pytest.raises(FetchError):
            fetcher.validate_id("240809869")

    def test_validate_id_rejects_malformed_version(self):
        """Test that validate_id rejects malformed version suffix."""
        fetcher = ArxivFetcher()
        
        with pytest.raises(FetchError):
            fetcher.validate_id("2408.09869v")

    @patch('urllib.request.urlopen')
    def test_fetch_downloads_pdf_to_file(self, mock_urlopen):
        """Test that fetch downloads PDF and returns valid file path."""
        # Mock PDF download
        mock_response = Mock()
        mock_response.read.return_value = b"%PDF-1.4 fake pdf content here"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        mock_urlopen.return_value.__exit__.return_value = False
        
        fetcher = ArxivFetcher()
        path = fetcher.fetch("2408.09869")
        
        # Verify path exists and is a PDF
        assert isinstance(path, Path)
        assert path.suffix == ".pdf"
        assert path.exists()
        
        # Verify correct URL was called
        mock_urlopen.assert_called_once()
        called_url = mock_urlopen.call_args[0][0]
        assert "2408.09869" in called_url
        assert "arxiv.org/pdf" in called_url

    @patch('urllib.request.urlopen')
    def test_fetch_raises_error_on_404(self, mock_urlopen):
        """Test that fetch raises FetchError on 404 response."""
        # Mock 404 response
        mock_urlopen.side_effect = Exception("404 Not Found")
        
        fetcher = ArxivFetcher()
        
        with pytest.raises(FetchError):
            fetcher.fetch("9999.99999")

    @patch('urllib.request.urlopen')
    def test_fetch_raises_error_on_network_failure(self, mock_urlopen):
        """Test that fetch raises FetchError on network errors."""
        # Mock network error
        mock_urlopen.side_effect = Exception("Connection timeout")
        
        fetcher = ArxivFetcher()
        
        with pytest.raises(FetchError):
            fetcher.fetch("2408.09869")

    @patch('urllib.request.urlopen')
    def test_fetch_validates_id_before_download(self, mock_urlopen):
        """Test that fetch validates ID format before attempting download."""
        fetcher = ArxivFetcher()
        
        # Should raise FetchError without calling urlopen
        with pytest.raises(FetchError):
            fetcher.fetch("invalid-id")
        
        # urlopen should not be called
        mock_urlopen.assert_not_called()

    @patch('urllib.request.urlopen')
    def test_extract_metadata_parses_arxiv_api_response(self, mock_urlopen):
        """Test that extract_metadata parses XML from ArXiv API."""
        # Mock ArXiv API XML response
        xml_response = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>A Novel Approach to Deep Learning</title>
    <author><name>John Doe</name></author>
    <author><name>Jane Smith</name></author>
    <summary>This paper presents a novel approach to deep learning with impressive results.</summary>
  </entry>
</feed>'''
        
        mock_response = Mock()
        mock_response.read.return_value = xml_response
        mock_urlopen.return_value.__enter__.return_value = mock_response
        mock_urlopen.return_value.__exit__.return_value = False
        
        fetcher = ArxivFetcher()
        metadata = fetcher.extract_metadata("2408.09869")
        
        # Verify metadata extracted correctly
        assert metadata["title"] == "A Novel Approach to Deep Learning"
        assert len(metadata["authors"]) == 2
        assert "John Doe" in metadata["authors"]
        assert "Jane Smith" in metadata["authors"]
        assert "novel approach" in metadata["summary"].lower()

    @patch('urllib.request.urlopen')
    def test_extract_metadata_handles_single_author(self, mock_urlopen):
        """Test that extract_metadata correctly handles papers with single author."""
        xml_response = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Single Author Paper</title>
    <author><name>Alice Johnson</name></author>
    <summary>A paper by a single author.</summary>
  </entry>
</feed>'''
        
        mock_response = Mock()
        mock_response.read.return_value = xml_response
        mock_urlopen.return_value.__enter__.return_value = mock_response
        mock_urlopen.return_value.__exit__.return_value = False
        
        fetcher = ArxivFetcher()
        metadata = fetcher.extract_metadata("2408.09869")
        
        assert metadata["title"] == "Single Author Paper"
        assert len(metadata["authors"]) == 1
        assert metadata["authors"][0] == "Alice Johnson"

    @patch('urllib.request.urlopen')
    def test_extract_metadata_validates_id_before_query(self, mock_urlopen):
        """Test that extract_metadata validates ID before making API call."""
        fetcher = ArxivFetcher()
        
        with pytest.raises(FetchError):
            fetcher.extract_metadata("not-valid-id")
        
        # urlopen should not be called
        mock_urlopen.assert_not_called()

    @patch('urllib.request.urlopen')
    def test_extract_metadata_raises_error_on_api_failure(self, mock_urlopen):
        """Test that extract_metadata raises FetchError on API errors."""
        mock_urlopen.side_effect = Exception("API Error")
        
        fetcher = ArxivFetcher()
        
        with pytest.raises(FetchError):
            fetcher.extract_metadata("2408.09869")

    @patch('urllib.request.urlopen')
    def test_extract_metadata_calls_correct_api_endpoint(self, mock_urlopen):
        """Test that extract_metadata calls correct ArXiv API endpoint."""
        xml_response = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Test Paper</title>
    <author><name>Test Author</name></author>
    <summary>Test summary.</summary>
  </entry>
</feed>'''
        
        mock_response = Mock()
        mock_response.read.return_value = xml_response
        mock_urlopen.return_value.__enter__.return_value = mock_response
        mock_urlopen.return_value.__exit__.return_value = False
        
        fetcher = ArxivFetcher()
        fetcher.extract_metadata("2408.09869")
        
        # Verify correct API endpoint URL
        mock_urlopen.assert_called_once()
        called_url = mock_urlopen.call_args[0][0]
        assert "export.arxiv.org/api/query" in called_url
        assert "id_list=2408.09869" in called_url

    def test_init_creates_valid_fetcher_instance(self):
        """Test that ArxivFetcher can be instantiated."""
        fetcher = ArxivFetcher()
        assert fetcher is not None
        assert hasattr(fetcher, 'validate_id')
        assert hasattr(fetcher, 'fetch')
        assert hasattr(fetcher, 'extract_metadata')

    @patch('urllib.request.urlopen')
    def test_fetch_with_versioned_id(self, mock_urlopen):
        """Test that fetch works with versioned ArXiv IDs (e.g., 2408.09869v1)."""
        mock_response = Mock()
        mock_response.read.return_value = b"%PDF-1.4 test content"
        mock_urlopen.return_value.__enter__.return_value = mock_response
        mock_urlopen.return_value.__exit__.return_value = False
        
        fetcher = ArxivFetcher()
        path = fetcher.fetch("2408.09869v1")
        
        assert path.suffix == ".pdf"
        assert path.exists()

    @patch('urllib.request.urlopen')
    def test_extract_metadata_with_versioned_id(self, mock_urlopen):
        """Test that extract_metadata works with versioned ArXiv IDs."""
        xml_response = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Versioned Paper</title>
    <author><name>Test Author</name></author>
    <summary>Paper with version.</summary>
  </entry>
</feed>'''
        
        mock_response = Mock()
        mock_response.read.return_value = xml_response
        mock_urlopen.return_value.__enter__.return_value = mock_response
        mock_urlopen.return_value.__exit__.return_value = False
        
        fetcher = ArxivFetcher()
        metadata = fetcher.extract_metadata("2408.09869v2")
        
        assert metadata["title"] == "Versioned Paper"
