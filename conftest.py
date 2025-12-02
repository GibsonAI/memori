import pytest

from memori._config import Config
from memori.storage import Manager as StorageManager


@pytest.fixture
def mock_mysql_session(mocker):
    session = mocker.MagicMock()
    session.get_bind.return_value.dialect.name = "mysql"
    type(session).__module__ = "sqlalchemy.orm.session"

    mock_result = mocker.MagicMock()
    mock_result.mappings.return_value.fetchone.return_value = {"1": 1}
    mock_result.mappings.return_value.fetchall.return_value = []
    session.connection.return_value.exec_driver_sql.return_value = mock_result

    return session


@pytest.fixture
def mock_postgres_session(mocker):
    session = mocker.MagicMock()
    session.get_bind.return_value.dialect.name = "postgresql"
    type(session).__module__ = "sqlalchemy.orm.session"

    mock_result = mocker.MagicMock()
    mock_result.mappings.return_value.fetchone.return_value = {"one": 1}
    mock_result.mappings.return_value.fetchall.return_value = []
    session.connection.return_value.exec_driver_sql.return_value = mock_result

    return session


@pytest.fixture
def session(mock_mysql_session):
    return mock_mysql_session


@pytest.fixture
def postgres_session(mock_postgres_session):
    return mock_postgres_session


@pytest.fixture
def config(mocker, session):
    config = Config()
    config.storage = StorageManager(config)
    config.storage.adapter = mocker.MagicMock()
    config.storage.driver = mocker.MagicMock()
    return config
