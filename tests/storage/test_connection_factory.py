import pytest

from memori.storage.adapters.dbapi._adapter import Adapter as DBAPIAdapter


def test_connection_factory_is_called_eagerly(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback"])
    mock_conn.__module__ = "psycopg2"
    type(mock_conn).__module__ = "psycopg2"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute = mocker.MagicMock()
    mock_cursor.close = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    call_count = [0]

    def factory():
        call_count[0] += 1
        return mock_conn

    adapter = DBAPIAdapter(factory)

    assert call_count[0] == 1

    adapter.commit()

    assert call_count[0] == 1
    mock_conn.commit.assert_called_once()


def test_connection_factory_cached_after_first_call(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback"])
    mock_conn.__module__ = "psycopg2"
    type(mock_conn).__module__ = "psycopg2"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute = mocker.MagicMock()
    mock_cursor.close = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    call_count = [0]

    def factory():
        call_count[0] += 1
        return mock_conn

    adapter = DBAPIAdapter(factory)

    adapter.commit()
    adapter.commit()

    assert call_count[0] == 1
    assert mock_conn.commit.call_count == 2


def test_non_callable_raises_error():
    # Test that passing a non-callable raises an error
    with pytest.raises(TypeError, match="conn must be a callable"):
        DBAPIAdapter("not callable")

    with pytest.raises(TypeError, match="conn must be a callable"):
        DBAPIAdapter(123)

    with pytest.raises(TypeError, match="conn must be a callable"):
        DBAPIAdapter({"not": "callable"})


def test_connection_lifecycle_close(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback", "close"])
    mock_conn.__module__ = "psycopg2"
    type(mock_conn).__module__ = "psycopg2"

    mock_cursor = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()
    mock_conn.close = mocker.MagicMock()

    def factory():
        return mock_conn

    adapter = DBAPIAdapter(factory)

    # Connection is created eagerly
    mock_conn.commit.assert_not_called()

    adapter.commit()
    mock_conn.commit.assert_called_once()

    # Close should call close on the connection and set to None
    adapter.close()
    mock_conn.close.assert_called_once()
    assert adapter.conn is None
