import warnings
from importlib.metadata import PackageNotFoundError
from unittest.mock import patch

from memori._exceptions import (
    MemoriLegacyPackageWarning,
    warn_if_legacy_memorisdk_installed,
)


def test_warn_if_legacy_memorisdk_not_installed():
    """Test that no warning is emitted when memorisdk is not installed."""
    with patch("memori._exceptions.distribution", side_effect=PackageNotFoundError()):
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            warn_if_legacy_memorisdk_installed()

            legacy_warnings = [
                w
                for w in warning_list
                if issubclass(w.category, MemoriLegacyPackageWarning)
            ]
            assert len(legacy_warnings) == 0, (
                "Should not emit warning when memorisdk is not installed"
            )


def test_warn_if_legacy_memorisdk_installed():
    """Test that warning is emitted when memorisdk is installed."""
    with patch("memori._exceptions.distribution"):
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            warn_if_legacy_memorisdk_installed()

            legacy_warnings = [
                w
                for w in warning_list
                if issubclass(w.category, MemoriLegacyPackageWarning)
            ]
            assert len(legacy_warnings) == 1, (
                "Should emit warning when memorisdk is installed"
            )
            assert "memorisdk" in str(legacy_warnings[0].message)
            assert "pip uninstall memorisdk" in str(legacy_warnings[0].message)
            assert "pip install memori" in str(legacy_warnings[0].message)


def test_warning_message_content():
    """Test that the warning message contains helpful migration instructions."""
    with patch("memori._exceptions.distribution"):
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            warn_if_legacy_memorisdk_installed()

            legacy_warnings = [
                w
                for w in warning_list
                if issubclass(w.category, MemoriLegacyPackageWarning)
            ]
            assert len(legacy_warnings) == 1
            message = str(legacy_warnings[0].message)
            assert "memorisdk" in message
            assert "deprecated" in message
            assert "pip uninstall memorisdk" in message
            assert "pip install memori" in message


def test_legacy_warning_class_is_user_warning():
    """Test that MemoriLegacyPackageWarning is a UserWarning subclass."""
    assert issubclass(MemoriLegacyPackageWarning, UserWarning), (
        "MemoriLegacyPackageWarning should be a UserWarning subclass"
    )


def test_warn_function_imported_in_init():
    """Test that warn_if_legacy_memorisdk_installed is available in __init__.py."""
    import inspect

    import memori

    source = inspect.getsource(memori)
    assert "warn_if_legacy_memorisdk_installed" in source, (
        "warn_if_legacy_memorisdk_installed should be imported in __init__.py"
    )


def test_no_warning_when_only_memori_installed():
    """Test that importing memori package doesn't emit warning when memorisdk is not installed."""

    def mock_distribution(pkg):
        if pkg == "memorisdk":
            raise PackageNotFoundError()
        return None

    with patch("memori._exceptions.distribution", side_effect=mock_distribution):
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            warn_if_legacy_memorisdk_installed()

            legacy_warnings = [
                w
                for w in warning_list
                if issubclass(w.category, MemoriLegacyPackageWarning)
            ]
            assert len(legacy_warnings) == 0, (
                "Should not emit warning when only memori is installed"
            )
