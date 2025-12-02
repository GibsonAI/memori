from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_conn():
    """Create a mock storage adapter connection."""
    conn = MagicMock()
    conn.execute = MagicMock()
    conn.flush = MagicMock()
    conn.commit = MagicMock()
    return conn


@pytest.fixture
def mock_single_result():
    """Create a mock result for single row queries (fetchone)."""

    def _make_result(data):
        mock_result = Mock()
        mock_result.mappings.return_value.fetchone.return_value = data
        return mock_result

    return _make_result


@pytest.fixture
def mock_multiple_results():
    """Create a mock result for multiple row queries (fetchall)."""

    def _make_result(data):
        mock_result = Mock()
        mock_result.mappings.return_value.fetchall.return_value = data
        return mock_result

    return _make_result


@pytest.fixture
def mock_empty_result():
    """Create a mock result for empty queries."""
    mock_result = Mock()
    mock_result.mappings.return_value.fetchall.return_value = []
    return mock_result
