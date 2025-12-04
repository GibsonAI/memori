import sys
from unittest.mock import MagicMock


def test_import_optional_module_success(mocker):
    """Test that _import_optional_module successfully imports existing modules."""
    mock_importlib = mocker.patch("memori.storage.importlib")
    mock_module = MagicMock()
    mock_importlib.import_module.return_value = mock_module

    from memori.storage import _import_optional_module

    _import_optional_module("test.module")

    mock_importlib.import_module.assert_called_once_with("test.module")


def test_import_optional_module_handles_import_error(mocker):
    """Test that _import_optional_module gracefully handles non-existent modules without errors."""
    mock_importlib = mocker.patch("memori.storage.importlib")
    mock_importlib.import_module.side_effect = ImportError("Module not found")

    from memori.storage import _import_optional_module

    _import_optional_module("non.existent.module")

    mock_importlib.import_module.assert_called_once_with("non.existent.module")


def test_storage_module_initialization_with_all_modules(mocker):
    """Test that storage module initializes correctly when all expected adapters and drivers are present."""
    mock_importlib = mocker.patch("importlib.import_module")
    mock_module = MagicMock()
    mock_importlib.return_value = mock_module

    if "memori.storage" in sys.modules:
        del sys.modules["memori.storage"]

    import memori.storage

    expected_calls = [
        "memori.storage.adapters.sqlalchemy",
        "memori.storage.adapters.django",
        "memori.storage.adapters.mongodb",
        "memori.storage.adapters.dbapi",
        "memori.storage.drivers.mongodb",
        "memori.storage.drivers.mysql",
        "memori.storage.drivers.oracle",
        "memori.storage.drivers.postgresql",
        "memori.storage.drivers.sqlite",
    ]

    assert mock_importlib.call_count == len(expected_calls)

    for expected_module in expected_calls:
        assert any(
            call[0][0] == expected_module for call in mock_importlib.call_args_list
        )

    assert hasattr(memori.storage, "Manager")


def test_storage_module_initialization_with_missing_modules(mocker):
    """Test that storage module initializes correctly when some optional adapters or drivers are missing."""
    mock_importlib = mocker.patch("importlib.import_module")

    def import_side_effect(module_path):
        if "mongodb" in module_path or "oracle" in module_path:
            raise ImportError(f"No module named '{module_path}'")
        return MagicMock()

    mock_importlib.side_effect = import_side_effect

    if "memori.storage" in sys.modules:
        del sys.modules["memori.storage"]

    import memori.storage

    expected_calls = [
        "memori.storage.adapters.sqlalchemy",
        "memori.storage.adapters.django",
        "memori.storage.adapters.mongodb",
        "memori.storage.adapters.dbapi",
        "memori.storage.drivers.mongodb",
        "memori.storage.drivers.mysql",
        "memori.storage.drivers.oracle",
        "memori.storage.drivers.postgresql",
        "memori.storage.drivers.sqlite",
    ]

    assert mock_importlib.call_count == len(expected_calls)

    for expected_module in expected_calls:
        assert any(
            call[0][0] == expected_module for call in mock_importlib.call_args_list
        )

    assert hasattr(memori.storage, "Manager")
