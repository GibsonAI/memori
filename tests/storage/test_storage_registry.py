from memori.storage._registry import Registry
from memori.storage.adapters.sqlalchemy._adapter import (
    Adapter as SqlAlchemyStorageAdapter,
)
from memori.storage.drivers.mysql._driver import Driver as MysqlStorageDriver
from memori.storage.drivers.postgresql._driver import Driver as PostgresqlStorageDriver


def test_storage_adapter_sqlalchemy(session):
    assert isinstance(Registry().adapter(lambda: session), SqlAlchemyStorageAdapter)


def test_storage_driver_mysql(session):
    assert isinstance(
        Registry().driver(Registry().adapter(lambda: session)), MysqlStorageDriver
    )


def test_storage_driver_postgresql(postgres_session):
    assert isinstance(
        Registry().driver(Registry().adapter(lambda: postgres_session)),
        PostgresqlStorageDriver,
    )


def test_storage_driver_mariadb(mocker):
    mariadb_session = mocker.Mock()
    mariadb_session.get_bind.return_value.dialect.name = "mariadb"
    type(mariadb_session).__module__ = "sqlalchemy.orm.session"

    adapter = Registry().adapter(lambda: mariadb_session)
    driver = Registry().driver(adapter)

    assert isinstance(driver, MysqlStorageDriver)


def test_storage_driver_cockroachdb(mocker):
    cockroachdb_session = mocker.Mock()
    cockroachdb_session.get_bind.return_value.dialect.name = "cockroachdb"
    type(cockroachdb_session).__module__ = "sqlalchemy.orm.session"

    adapter = Registry().adapter(lambda: cockroachdb_session)
    driver = Registry().driver(adapter)

    assert isinstance(driver, PostgresqlStorageDriver)
