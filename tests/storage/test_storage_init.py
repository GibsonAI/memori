from unittest.mock import MagicMock, patch


def test_import_optional_module_success():
    """Test that _import_optional_module successfully imports existing modules."""
    with patch("importlib.import_module") as mock_import:
        from memori.storage import _import_optional_module

        mock_module = MagicMock()
        mock_import.return_value = mock_module

        _import_optional_module("sys")

        mock_import.assert_called_with("sys")


def test_import_optional_module_handles_import_error():
    """Test that _import_optional_module gracefully handles non-existent modules without errors."""
    with patch("importlib.import_module") as mock_import:
        from memori.storage import _import_optional_module

        mock_import.side_effect = ImportError("Module not found")

        _import_optional_module("non.existent.module")

        mock_import.assert_called_with("non.existent.module")


def test_storage_module_initializes_with_manager_available():
    """Test that storage module initializes correctly when all expected adapters and drivers are present."""
    import memori.storage

    assert hasattr(memori.storage, "Manager")
    assert "Manager" in memori.storage.__all__


def test_storage_module_has_import_optional_module_function():
    """Test that storage module has the _import_optional_module function."""
    import memori.storage

    assert hasattr(memori.storage, "_import_optional_module")
    assert callable(memori.storage._import_optional_module)
