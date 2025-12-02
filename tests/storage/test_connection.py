from unittest.mock import Mock, patch

import pytest

from memori.storage._connection import connection_context


def test_connection_context_with_none_factory():
    with connection_context(None) as (conn, adapter, driver):
        assert conn is None
        assert adapter is None
        assert driver is None


def test_connection_context_success():
    mock_conn = Mock()
    mock_adapter = Mock()
    mock_driver = Mock()
    conn_factory = Mock(return_value=mock_conn)

    with patch("memori.storage._connection.Registry") as mock_registry_class:
        mock_registry = Mock()
        mock_registry.adapter.return_value = mock_adapter
        mock_registry.driver.return_value = mock_driver
        mock_registry_class.return_value = mock_registry

        with connection_context(conn_factory) as (conn, adapter, driver):
            assert conn == mock_conn
            assert adapter == mock_adapter
            assert driver == mock_driver

        conn_factory.assert_called_once()
        mock_registry.adapter.assert_called_once_with(mock_conn)
        mock_registry.driver.assert_called_once_with(mock_adapter)
        mock_adapter.commit.assert_called_once()
        mock_adapter.close.assert_called_once()


def test_connection_context_exception_in_body():
    mock_conn = Mock()
    mock_adapter = Mock()
    mock_driver = Mock()
    conn_factory = Mock(return_value=mock_conn)

    with patch("memori.storage._connection.Registry") as mock_registry_class:
        mock_registry = Mock()
        mock_registry.adapter.return_value = mock_adapter
        mock_registry.driver.return_value = mock_driver
        mock_registry_class.return_value = mock_registry

        with pytest.raises(ValueError):
            with connection_context(conn_factory) as (conn, adapter, driver):
                raise ValueError("Test error")

        mock_adapter.commit.assert_not_called()
        mock_adapter.rollback.assert_called_once()
        mock_adapter.close.assert_called_once()


def test_connection_context_close_exception_suppressed():
    mock_conn = Mock()
    mock_adapter = Mock()
    mock_adapter.close.side_effect = Exception("Close failed")
    mock_driver = Mock()
    conn_factory = Mock(return_value=mock_conn)

    with patch("memori.storage._connection.Registry") as mock_registry_class:
        mock_registry = Mock()
        mock_registry.adapter.return_value = mock_adapter
        mock_registry.driver.return_value = mock_driver
        mock_registry_class.return_value = mock_registry

        with connection_context(conn_factory) as (conn, adapter, driver):
            pass

        mock_adapter.commit.assert_called_once()
        mock_adapter.close.assert_called_once()


def test_connection_context_commit_exception_propagates():
    mock_conn = Mock()
    mock_adapter = Mock()
    mock_adapter.commit.side_effect = Exception("Commit failed")
    mock_driver = Mock()
    conn_factory = Mock(return_value=mock_conn)

    with patch("memori.storage._connection.Registry") as mock_registry_class:
        mock_registry = Mock()
        mock_registry.adapter.return_value = mock_adapter
        mock_registry.driver.return_value = mock_driver
        mock_registry_class.return_value = mock_registry

        with pytest.raises(Exception, match="Commit failed"):
            with connection_context(conn_factory):
                pass

        mock_adapter.rollback.assert_called_once()
        mock_adapter.close.assert_called_once()
