"""Tests for package structure and metadata."""


def test_import_peripatos():
    """Test that the peripatos package can be imported."""
    import peripatos
    assert peripatos is not None


def test_version():
    """Test that version is correctly set."""
    import peripatos
    assert peripatos.__version__ == "0.1.0"
