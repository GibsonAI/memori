from memori.storage._registry import Registry
from memori.storage.adapters.dbapi._adapter import (
    Adapter as DBAPIAdapter,
)
from memori.storage.adapters.dbapi._adapter import (
    is_dbapi_connection,
)
from memori.storage.adapters.django._adapter import Adapter as DjangoAdapter
from memori.storage.adapters.sqlalchemy._adapter import Adapter as SQLAlchemyAdapter


def test_sqlalchemy_session_not_detected_as_dbapi(session):
    assert is_dbapi_connection(session) is False


def test_registry_routes_sqlalchemy_to_sqlalchemy_adapter(session):
    registry = Registry()
    adapter = registry.adapter(lambda: session)
    assert isinstance(adapter, SQLAlchemyAdapter)
    assert not isinstance(adapter, DBAPIAdapter)


def test_registry_routes_postgres_session_to_sqlalchemy_adapter(postgres_session):
    registry = Registry()
    adapter = registry.adapter(lambda: postgres_session)
    assert isinstance(adapter, SQLAlchemyAdapter)
    assert not isinstance(adapter, DBAPIAdapter)


def test_django_connection_not_detected_as_dbapi(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback", "vendor"])
    mock_conn.__class__.__module__ = "django.db.backends.postgresql.base"
    mock_conn.vendor = "postgresql"
    assert is_dbapi_connection(mock_conn) is False


def test_registry_routes_django_to_django_adapter(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback", "vendor"])
    mock_conn.__class__.__module__ = "django.db.backends.postgresql.base"
    mock_conn.vendor = "postgresql"
    mock_cursor = mocker.MagicMock()
    mock_cursor.__enter__ = mocker.MagicMock(return_value=mock_cursor)
    mock_cursor.__exit__ = mocker.MagicMock(return_value=False)
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)

    registry = Registry()
    adapter = registry.adapter(lambda: mock_conn)
    assert isinstance(adapter, DjangoAdapter)
    assert not isinstance(adapter, DBAPIAdapter)
