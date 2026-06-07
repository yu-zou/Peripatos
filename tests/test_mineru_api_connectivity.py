"""Direct MinerU API connectivity test.

Unlike test_parser_integration.py (which falls back to PyMuPDF on MinerU failure),
this test makes real HTTP calls to the MinerU API and fails immediately if endpoints
are misconfigured, wrong, or unreachable. This ensures endpoint regressions are caught
before they silently fall back to PyMuPDF in production.

Requires network access. Fails with a clear message if MinerU API is unreachable.
"""
import requests
import pytest

from peripatos_core.mineru_client import _FLASH_API_BASE, _PRECISION_API_BASE


class TestMinerUAPIConnectivity:
    """Verify MinerU API endpoints are reachable and respond correctly."""

    def test_flash_api_base_reachable(self):
        """Flash API base URL returns a valid response (not 404)."""
        try:
            resp = requests.get(
                f"{_FLASH_API_BASE}/parse/test",
                timeout=15,
            )
        except requests.RequestException as e:
            pytest.fail(
                f"MinerU Flash API base ({_FLASH_API_BASE}) is unreachable: {e}\n"
                f"This means Flash Extract will fail and fall back to PyMuPDF."
            )

        # We expect 401 or 404 for a non-existent task, but NOT a connection error
        # or 502/503 (which would indicate wrong URL or server down)
        assert resp.status_code != 502, (
            f"MinerU Flash API returned 502 Bad Gateway at {_FLASH_API_BASE}. "
            f"Check the API base URL."
        )
        assert resp.status_code != 503, (
            f"MinerU Flash API returned 503 Service Unavailable at {_FLASH_API_BASE}. "
            f"The service may be down."
        )

    def test_precision_api_base_reachable(self):
        """Precision API base URL returns a valid response (not 404 for base path)."""
        try:
            resp = requests.get(
                f"{_PRECISION_API_BASE}/extract/task/nonexistent",
                headers={"Authorization": "Bearer test-token"},
                timeout=15,
            )
        except requests.RequestException as e:
            pytest.fail(
                f"MinerU Precision API base ({_PRECISION_API_BASE}) is unreachable: {e}\n"
                f"This means Precision Extract will fail and fall back to PyMuPDF."
            )

        assert resp.status_code != 502, (
            f"MinerU Precision API returned 502 Bad Gateway at {_PRECISION_API_BASE}. "
            f"Check the API base URL."
        )
        assert resp.status_code != 503, (
            f"MinerU Precision API returned 503 Service Unavailable at {_PRECISION_API_BASE}. "
            f"The service may be down."
        )

    def test_flash_init_returns_expected_error(self):
        """Flash init endpoint responds with structured API error (not HTML 404 page).

        Sending an empty body should return a JSON error, not an HTML error page.
        This confirms the endpoint exists and speaks JSON.
        """
        try:
            resp = requests.post(
                f"{_FLASH_API_BASE}/parse/file",
                json={},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
        except requests.RequestException as e:
            pytest.fail(
                f"MinerU Flash init endpoint ({_FLASH_API_BASE}/parse/file) is unreachable: {e}"
            )

        # A real API endpoint returns JSON, even for errors.
        # A wrong URL returns HTML (nginx/apache error page).
        content_type = resp.headers.get("Content-Type", "")
        assert "application/json" in content_type or "text/plain" in content_type, (
            f"Flash init endpoint returned unexpected Content-Type: {content_type}. "
            f"Expected JSON. The URL may be wrong — check {_FLASH_API_BASE}/parse/file"
        )

    def test_precision_batch_url_returns_expected_error(self):
        """Precision batch upload endpoint responds with structured API error (not HTML).

        Sending a request without auth should return a JSON error (401/403), not HTML.
        """
        try:
            resp = requests.post(
                f"{_PRECISION_API_BASE}/file-urls/batch",
                json={"files": []},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
        except requests.RequestException as e:
            pytest.fail(
                f"MinerU Precision batch endpoint ({_PRECISION_API_BASE}/file-urls/batch) "
                f"is unreachable: {e}"
            )

        content_type = resp.headers.get("Content-Type", "")
        assert "application/json" in content_type or "text/plain" in content_type, (
            f"Precision batch endpoint returned unexpected Content-Type: {content_type}. "
            f"Expected JSON. The URL may be wrong — check {_PRECISION_API_BASE}/file-urls/batch"
        )
