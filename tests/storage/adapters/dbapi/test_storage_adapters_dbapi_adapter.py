import pytest

from memori.storage._registry import Registry
from memori.storage.adapters.dbapi._adapter import (
    Adapter as DBAPIAdapter,
)
from memori.storage.adapters.dbapi._adapter import (
    is_dbapi_connection,
)


@pytest.fixture
def mock_psycopg2_conn(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback"])
    mock_conn.__module__ = "psycopg2"
    type(mock_conn).__module__ = "psycopg2"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute = mocker.MagicMock()
    mock_cursor.close = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    return mock_conn


@pytest.fixture
def mock_pymysql_conn(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback"])
    mock_conn.__module__ = "pymysql"
    type(mock_conn).__module__ = "pymysql.connections"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute = mocker.MagicMock()
    mock_cursor.close = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    return mock_conn


@pytest.fixture
def mock_sqlite3_conn(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback"])
    mock_conn.__module__ = "sqlite3"
    type(mock_conn).__module__ = "sqlite3"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute = mocker.MagicMock()
    mock_cursor.close = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    return mock_conn


def test_commit_psycopg2(mock_psycopg2_conn):
    adapter = DBAPIAdapter(lambda: mock_psycopg2_conn)
    result = adapter.commit()

    mock_psycopg2_conn.commit.assert_called_once()
    assert result is adapter


def test_execute_psycopg2(mock_psycopg2_conn):
    adapter = DBAPIAdapter(lambda: mock_psycopg2_conn)
    cursor = adapter.execute("SELECT 1")

    mock_psycopg2_conn.cursor.assert_called_once()
    assert cursor is not None


def test_execute_with_binds_psycopg2(mock_psycopg2_conn):
    adapter = DBAPIAdapter(lambda: mock_psycopg2_conn)
    adapter.execute("SELECT * FROM users WHERE id = %s", (1,))

    mock_psycopg2_conn.cursor.assert_called_once()
    mock_cursor = mock_psycopg2_conn.cursor.return_value
    mock_cursor.execute.assert_called_once_with(
        "SELECT * FROM users WHERE id = %s", (1,)
    )


def test_flush_psycopg2(mock_psycopg2_conn):
    adapter = DBAPIAdapter(lambda: mock_psycopg2_conn)
    result = adapter.flush()

    assert result is adapter


def test_get_dialect_psycopg2(mock_psycopg2_conn):
    adapter = DBAPIAdapter(lambda: mock_psycopg2_conn)
    assert adapter.get_dialect() == "postgresql"


def test_rollback_psycopg2(mock_psycopg2_conn):
    adapter = DBAPIAdapter(lambda: mock_psycopg2_conn)
    result = adapter.rollback()

    mock_psycopg2_conn.rollback.assert_called_once()
    assert result is adapter


def test_commit_pymysql(mock_pymysql_conn):
    adapter = DBAPIAdapter(lambda: mock_pymysql_conn)
    result = adapter.commit()

    mock_pymysql_conn.commit.assert_called_once()
    assert result is adapter


def test_execute_pymysql(mock_pymysql_conn):
    adapter = DBAPIAdapter(lambda: mock_pymysql_conn)
    cursor = adapter.execute("SELECT 1")

    mock_pymysql_conn.cursor.assert_called_once()
    assert cursor is not None


def test_get_dialect_pymysql(mock_pymysql_conn):
    adapter = DBAPIAdapter(lambda: mock_pymysql_conn)
    assert adapter.get_dialect() == "mysql"


def test_rollback_pymysql(mock_pymysql_conn):
    adapter = DBAPIAdapter(lambda: mock_pymysql_conn)
    result = adapter.rollback()

    mock_pymysql_conn.rollback.assert_called_once()
    assert result is adapter


def test_commit_sqlite3(mock_sqlite3_conn):
    adapter = DBAPIAdapter(lambda: mock_sqlite3_conn)
    result = adapter.commit()

    mock_sqlite3_conn.commit.assert_called_once()
    assert result is adapter


def test_execute_sqlite3(mock_sqlite3_conn):
    adapter = DBAPIAdapter(lambda: mock_sqlite3_conn)
    cursor = adapter.execute("SELECT 1")

    mock_sqlite3_conn.cursor.assert_called_once()
    assert cursor is not None


def test_get_dialect_sqlite3(mock_sqlite3_conn):
    adapter = DBAPIAdapter(lambda: mock_sqlite3_conn)
    assert adapter.get_dialect() == "sqlite"


def test_rollback_sqlite3(mock_sqlite3_conn):
    adapter = DBAPIAdapter(lambda: mock_sqlite3_conn)
    result = adapter.rollback()

    mock_sqlite3_conn.rollback.assert_called_once()
    assert result is adapter


def test_execute_closes_cursor_on_exception(mock_psycopg2_conn):
    adapter = DBAPIAdapter(lambda: mock_psycopg2_conn)
    mock_cursor = mock_psycopg2_conn.cursor.return_value
    mock_cursor.execute.side_effect = Exception("Query error")

    with pytest.raises(Exception, match="Query error"):
        adapter.execute("SELECT invalid")

    mock_cursor.close.assert_called_once()


def test_get_dialect_unknown_raises_error(mocker):
    mock_conn = mocker.MagicMock()
    mock_conn.__module__ = "unknown_driver"
    type(mock_conn).__module__ = "unknown_driver"
    mock_conn.cursor = mocker.MagicMock()
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    adapter = DBAPIAdapter(lambda: mock_conn)

    with pytest.raises(ValueError, match="Unable to determine dialect"):
        adapter.get_dialect()


def test_is_dbapi_connection_psycopg2(mock_psycopg2_conn):
    assert is_dbapi_connection(mock_psycopg2_conn) is True


def test_is_dbapi_connection_pymysql(mock_pymysql_conn):
    assert is_dbapi_connection(mock_pymysql_conn) is True


def test_is_dbapi_connection_sqlite3(mock_sqlite3_conn):
    assert is_dbapi_connection(mock_sqlite3_conn) is True


def test_is_dbapi_connection_rejects_non_dbapi(mocker):
    mock_conn = mocker.MagicMock()
    del mock_conn.cursor
    assert is_dbapi_connection(mock_conn) is False


def test_is_dbapi_connection_rejects_non_callable_methods(mocker):
    mock_conn = mocker.MagicMock()
    mock_conn.cursor = "not_callable"
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()
    assert is_dbapi_connection(mock_conn) is False


def test_registry_routes_psycopg2_to_dbapi_adapter(mock_psycopg2_conn):
    registry = Registry()
    adapter = registry.adapter(lambda: mock_psycopg2_conn)
    assert isinstance(adapter, DBAPIAdapter)


def test_registry_routes_pymysql_to_dbapi_adapter(mock_pymysql_conn):
    registry = Registry()
    adapter = registry.adapter(lambda: mock_pymysql_conn)
    assert isinstance(adapter, DBAPIAdapter)


def test_registry_routes_sqlite3_to_dbapi_adapter(mock_sqlite3_conn):
    registry = Registry()
    adapter = registry.adapter(lambda: mock_sqlite3_conn)
    assert isinstance(adapter, DBAPIAdapter)
