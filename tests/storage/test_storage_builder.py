from unittest.mock import MagicMock

import pytest

from memori._config import Config
from memori.storage import Manager as StorageManager
from memori.storage._builder import Builder
from memori.storage.drivers.mysql._driver import Driver as MysqlDriver
from memori.storage.drivers.postgresql._driver import Driver as PostgresqlDriver


@pytest.fixture
def mock_config():
    """Create a mock Config object with storage."""
    config = Config()
    config.storage = StorageManager(config)
    config.storage.adapter = MagicMock()
    config.storage.driver = MagicMock()
    return config


@pytest.fixture
def builder(mock_config):
    """Create a Builder instance with mocked config."""
    return Builder(mock_config)


def test_get_supported_dialects(builder):
    """Test that _get_supported_dialects returns registered dialects."""
    supported = builder._get_supported_dialects()

    # Should contain at least mysql and postgresql
    assert "mysql" in supported
    assert "postgresql" in supported
    assert isinstance(supported, list)


def test_get_dialect_family_exact_match(builder):
    """Test dialect family detection with exact matches."""
    # Test exact matches
    assert builder._get_dialect_family("mysql") == MysqlDriver.migrations
    assert builder._get_dialect_family("postgresql") == PostgresqlDriver.migrations
    assert builder._get_dialect_family("cockroachdb") == PostgresqlDriver.migrations


def test_get_dialect_family_no_match(builder):
    """Test dialect family detection returns None for unknown dialects."""
    assert builder._get_dialect_family("invalid") is None
    assert builder._get_dialect_family("redis") is None
    assert builder._get_dialect_family("unknown") is None


def test_requires_rollback_true(builder):
    """Test rollback requirement for dialects that need it."""
    assert builder._requires_rollback("postgresql") is True
    assert builder._requires_rollback("cockroachdb") is True


def test_requires_rollback_false(builder):
    """Test rollback requirement for dialects that don't need it."""
    assert builder._requires_rollback("mysql") is False


def test_requires_rollback_unknown_dialect(builder):
    """Test rollback returns False for unknown dialects."""
    assert builder._requires_rollback("unknown") is False


def test_build_unsupported_dialect(mock_config):
    """Test that build raises NotImplementedError for unsupported dialects."""
    mock_config.storage.adapter.get_dialect.return_value = "invalid"
    builder = Builder(mock_config)

    with pytest.raises(NotImplementedError) as exc_info:
        builder.execute()

    assert "Unsupported dialect: invalid" in str(exc_info.value)
    assert "Supported dialects:" in str(exc_info.value)


def test_build_supported_dialect(mock_config):
    """Test that build works with supported dialects."""
    mock_config.storage.adapter.get_dialect.return_value = "mysql"

    # Mock the cli to avoid banner output
    builder = Builder(mock_config)
    builder.cli = MagicMock()

    # Mock schema version read
    mock_config.storage.driver.schema.version.read.return_value = len(
        MysqlDriver.migrations
    )

    result = builder.execute()

    assert result == builder
    assert mock_config.storage.driver.schema.version.read.called


def test_create_data_structures_postgresql_rollback(mock_config):
    """Test that create_data_structures triggers rollback for PostgreSQL on error."""
    mock_config.storage.adapter.get_dialect.return_value = "postgresql"

    builder = Builder(mock_config)
    builder.cli = MagicMock()

    # Simulate schema version read failure
    mock_config.storage.driver.schema.version.read.side_effect = Exception(
        "Schema error"
    )
    mock_config.storage.driver.schema.version.read.return_value = len(
        PostgresqlDriver.migrations
    )

    builder.create_data_structures()

    # Verify rollback was called for postgresql
    assert mock_config.storage.adapter.rollback.called


def test_create_data_structures_cockroachdb_rollback(mock_config):
    """Test that create_data_structures triggers rollback for CockroachDB on error."""
    mock_config.storage.adapter.get_dialect.return_value = "cockroachdb"

    builder = Builder(mock_config)
    builder.cli = MagicMock()

    # Simulate schema version read failure
    mock_config.storage.driver.schema.version.read.side_effect = Exception(
        "Schema error"
    )

    builder.create_data_structures()

    # Verify rollback was called for cockroachdb
    assert mock_config.storage.adapter.rollback.called


def test_create_data_structures_mysql_no_rollback(mock_config):
    """Test that create_data_structures does not trigger rollback for MySQL on error."""
    mock_config.storage.adapter.get_dialect.return_value = "mysql"

    builder = Builder(mock_config)
    builder.cli = MagicMock()

    # Simulate schema version read failure
    mock_config.storage.driver.schema.version.read.side_effect = Exception(
        "Schema error"
    )

    builder.create_data_structures()

    # Verify rollback was NOT called for mysql
    assert not mock_config.storage.adapter.rollback.called


def test_create_data_structures_no_migration_mapping(mock_config):
    """Test that create_data_structures raises error for unmapped dialect."""
    mock_config.storage.adapter.get_dialect.return_value = "unknown_dialect"

    builder = Builder(mock_config)
    builder.cli = MagicMock()

    # Mock to bypass the initial schema version check
    mock_config.storage.driver.schema.version.read.return_value = 0

    with pytest.raises(NotImplementedError) as exc_info:
        builder.create_data_structures()

    assert "No migration mapping found for dialect: unknown_dialect" in str(
        exc_info.value
    )
