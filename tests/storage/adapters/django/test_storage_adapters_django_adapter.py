import pytest

from memori.storage._registry import Registry
from memori.storage.adapters.django._adapter import (
    Adapter as DjangoAdapter,
)
from memori.storage.adapters.django._adapter import (
    is_django_connection,
)


@pytest.fixture
def mock_django_postgresql_conn(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback", "vendor"])
    mock_conn.__class__.__module__ = "django.db.backends.postgresql.base"
    mock_conn.vendor = "postgresql"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute = mocker.MagicMock()
    mock_cursor.fetchone = mocker.MagicMock()
    mock_cursor.fetchall = mocker.MagicMock()
    mock_cursor.close = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    return mock_conn


@pytest.fixture
def mock_django_mysql_conn(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback", "vendor"])
    mock_conn.__class__.__module__ = "django.db.backends.mysql.base"
    mock_conn.vendor = "mysql"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute = mocker.MagicMock()
    mock_cursor.fetchone = mocker.MagicMock()
    mock_cursor.fetchall = mocker.MagicMock()
    mock_cursor.close = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    return mock_conn


@pytest.fixture
def mock_django_sqlite_conn(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback", "vendor"])
    mock_conn.__class__.__module__ = "django.db.backends.sqlite3.base"
    mock_conn.vendor = "sqlite"

    mock_cursor = mocker.MagicMock()
    mock_cursor.execute = mocker.MagicMock()
    mock_cursor.fetchone = mocker.MagicMock()
    mock_cursor.fetchall = mocker.MagicMock()
    mock_cursor.close = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    return mock_conn


def test_commit_postgresql(mock_django_postgresql_conn):
    adapter = DjangoAdapter(lambda: mock_django_postgresql_conn)
    result = adapter.commit()

    mock_django_postgresql_conn.commit.assert_called_once()
    assert result is adapter


def test_execute_postgresql(mock_django_postgresql_conn):
    adapter = DjangoAdapter(lambda: mock_django_postgresql_conn)
    cursor = adapter.execute("SELECT 1")

    mock_django_postgresql_conn.cursor.assert_called_once()
    assert cursor is not None


def test_execute_with_binds_postgresql(mock_django_postgresql_conn):
    adapter = DjangoAdapter(lambda: mock_django_postgresql_conn)
    adapter.execute("SELECT * FROM users WHERE id = %s", (1,))

    mock_django_postgresql_conn.cursor.assert_called_once()
    mock_cursor = mock_django_postgresql_conn.cursor.return_value
    mock_cursor.execute.assert_called_once_with(
        "SELECT * FROM users WHERE id = %s", (1,)
    )


def test_flush_postgresql(mock_django_postgresql_conn):
    adapter = DjangoAdapter(lambda: mock_django_postgresql_conn)
    result = adapter.flush()

    assert result is adapter


def test_get_dialect_postgresql(mock_django_postgresql_conn):
    adapter = DjangoAdapter(lambda: mock_django_postgresql_conn)
    assert adapter.get_dialect() == "postgresql"


def test_rollback_postgresql(mock_django_postgresql_conn):
    adapter = DjangoAdapter(lambda: mock_django_postgresql_conn)
    result = adapter.rollback()

    mock_django_postgresql_conn.rollback.assert_called_once()
    assert result is adapter


def test_commit_mysql(mock_django_mysql_conn):
    adapter = DjangoAdapter(lambda: mock_django_mysql_conn)
    result = adapter.commit()

    mock_django_mysql_conn.commit.assert_called_once()
    assert result is adapter


def test_execute_mysql(mock_django_mysql_conn):
    adapter = DjangoAdapter(lambda: mock_django_mysql_conn)
    cursor = adapter.execute("SELECT 1")

    mock_django_mysql_conn.cursor.assert_called_once()
    assert cursor is not None


def test_get_dialect_mysql(mock_django_mysql_conn):
    adapter = DjangoAdapter(lambda: mock_django_mysql_conn)
    assert adapter.get_dialect() == "mysql"


def test_rollback_mysql(mock_django_mysql_conn):
    adapter = DjangoAdapter(lambda: mock_django_mysql_conn)
    result = adapter.rollback()

    mock_django_mysql_conn.rollback.assert_called_once()
    assert result is adapter


def test_commit_sqlite(mock_django_sqlite_conn):
    adapter = DjangoAdapter(lambda: mock_django_sqlite_conn)
    result = adapter.commit()

    mock_django_sqlite_conn.commit.assert_called_once()
    assert result is adapter


def test_execute_sqlite(mock_django_sqlite_conn):
    adapter = DjangoAdapter(lambda: mock_django_sqlite_conn)
    cursor = adapter.execute("SELECT 1")

    mock_django_sqlite_conn.cursor.assert_called_once()
    assert cursor is not None


def test_get_dialect_sqlite(mock_django_sqlite_conn):
    adapter = DjangoAdapter(lambda: mock_django_sqlite_conn)
    assert adapter.get_dialect() == "sqlite"


def test_rollback_sqlite(mock_django_sqlite_conn):
    adapter = DjangoAdapter(lambda: mock_django_sqlite_conn)
    result = adapter.rollback()

    mock_django_sqlite_conn.rollback.assert_called_once()
    assert result is adapter


def test_execute_closes_cursor_on_exception(mock_django_postgresql_conn):
    adapter = DjangoAdapter(lambda: mock_django_postgresql_conn)
    mock_cursor = mock_django_postgresql_conn.cursor.return_value
    mock_cursor.execute.side_effect = Exception("Query error")

    with pytest.raises(Exception, match="Query error"):
        adapter.execute("SELECT invalid")

    mock_cursor.close.assert_called_once()


def test_get_dialect_unknown_raises_error(mocker):
    mock_conn = mocker.MagicMock()
    mock_conn.__class__.__module__ = "django.db.backends.unknown.base"
    mock_conn.vendor = "unknown_db"
    mock_conn.cursor = mocker.MagicMock()
    mock_conn.commit = mocker.MagicMock()
    mock_conn.rollback = mocker.MagicMock()

    adapter = DjangoAdapter(lambda: mock_conn)

    with pytest.raises(ValueError, match="Unable to determine dialect"):
        adapter.get_dialect()


def test_is_django_connection_postgresql(mock_django_postgresql_conn):
    assert is_django_connection(mock_django_postgresql_conn) is True


def test_is_django_connection_mysql(mock_django_mysql_conn):
    assert is_django_connection(mock_django_mysql_conn) is True


def test_is_django_connection_sqlite(mock_django_sqlite_conn):
    assert is_django_connection(mock_django_sqlite_conn) is True


def test_is_django_connection_rejects_non_django(mocker):
    mock_conn = mocker.MagicMock()
    mock_conn.__class__.__module__ = "psycopg2"
    assert is_django_connection(mock_conn) is False


def test_is_django_connection_rejects_non_callable_cursor(mocker):
    mock_conn = mocker.MagicMock()
    mock_conn.__class__.__module__ = "django.db.backends.postgresql.base"
    mock_conn.cursor = "not_callable"
    assert is_django_connection(mock_conn) is False


def test_registry_routes_postgresql_to_django_adapter(mock_django_postgresql_conn):
    registry = Registry()
    adapter = registry.adapter(lambda: mock_django_postgresql_conn)
    assert isinstance(adapter, DjangoAdapter)


def test_registry_routes_mysql_to_django_adapter(mock_django_mysql_conn):
    registry = Registry()
    adapter = registry.adapter(lambda: mock_django_mysql_conn)
    assert isinstance(adapter, DjangoAdapter)


def test_registry_routes_sqlite_to_django_adapter(mock_django_sqlite_conn):
    registry = Registry()
    adapter = registry.adapter(lambda: mock_django_sqlite_conn)
    assert isinstance(adapter, DjangoAdapter)
