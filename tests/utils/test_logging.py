import logging
import re

import pytest
from loguru import logger

from memori.config.settings import LoggingSettings
from memori.utils.logging import LoggingManager

TIMESTAMP_REGEX = re.compile(r"\d{2}:\d{2}:\d{2}")


@pytest.fixture(autouse=True)
def reset_logging():
    """A fixture to ensure logging is reset after each test."""
    yield
    logger.remove()


def test_memori_logger_works_in_verbose(capsys):
    """
    Tests that Memori's own Loguru logger still works
    and includes the new formatting (e.g., timestamp).
    """
    settings = LoggingSettings()
    LoggingManager.setup_logging(settings, verbose=True)

    test_message = "This is a Memori info log."
    logger.info(test_message)

    captured = capsys.readouterr()
    log_output = captured.err

    assert test_message in log_output
    assert "INFO" in log_output
    assert TIMESTAMP_REGEX.search(log_output), "Log output should contain a timestamp"


def test_standard_logger_intercepts_all_levels(capsys):
    """
    Tests that the intercept handler correctly captures
    different log levels from the standard logging module.
    """
    settings = LoggingSettings()
    LoggingManager.setup_logging(settings, verbose=True)

    std_logger = logging.getLogger("a_standard_test_logger")

    std_logger.debug("This is a DEBUG message.")
    std_logger.warning("This is a WARNING message.")
    std_logger.error("This is an ERROR message.")

    captured = capsys.readouterr()
    log_output = captured.err

    assert "This is a DEBUG message." in log_output
    assert "This is a WARNING message." in log_output
    assert "This is an ERROR message." in log_output

    assert "[a_standard_test_logger]" in log_output

    assert "DEBUG" in log_output
    assert "WARNING" in log_output
    assert "ERROR" in log_output
    assert "[WARNING]" not in log_output, "Log level should not be duplicated"


def test_standard_logger_exception_handling(capsys):
    """
    Tests that the intercept handler correctly captures
    exceptions and backtraces from the standard logging module.
    """
    settings = LoggingSettings()
    LoggingManager.setup_logging(settings, verbose=True)

    capsys.readouterr()

    std_logger = logging.getLogger("an_exception_logger")
    test_message = "An error occurred"

    try:
        raise ValueError("This is a test exception")
    except ValueError:
        std_logger.exception(test_message)

    captured = capsys.readouterr()
    log_output = captured.err

    assert test_message in log_output
    assert "[an_exception_logger]" in log_output
    assert "ERROR" in log_output
    assert "Traceback (most recent call last)" in log_output

    assert "ValueError" in log_output
    assert "This is a test exception" in log_output
