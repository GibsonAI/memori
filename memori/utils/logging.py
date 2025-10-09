"""
Centralized logging configuration for Memoriai
"""

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from ..config.settings import LoggingSettings, LogLevel
from .exceptions import ConfigurationError


class LoggingManager:
    """Centralized logging management"""

    _initialized = False
    _current_config: LoggingSettings | None = None

    @classmethod
    def setup_logging(cls, settings: LoggingSettings, verbose: bool = False) -> None:
        """Setup logging configuration"""
        try:
            # Remove default handler if it exists
            if not cls._initialized:
                logger.remove()

            # CRITICAL: Always disable third-party loggers to prevent performance degradation
            # SQLAlchemy, OpenAI, and other libraries have verbose logging by default
            # which can cause 30-70% performance overhead if not disabled
            cls._disable_other_loggers()

            if verbose:
                # When verbose mode is enabled, show Memori debug logging
                logger.add(
                    sys.stderr,
                    level="DEBUG",
                    format=settings.format,
                    colorize=True,
                    backtrace=True,
                    diagnose=True,
                )
            else:
                # When verbose is False, minimize loguru output to essential logs only
                logger.add(
                    sys.stderr,
                    level="WARNING",  # Only show warnings and errors
                    format="<level>{level}</level>: {message}",  # Simplified format
                    colorize=False,
                    backtrace=False,
                    diagnose=False,
                )

            # Configure file logging if enabled
            if settings.log_to_file:
                log_path = Path(settings.log_file_path)
                log_path.parent.mkdir(parents=True, exist_ok=True)

                if settings.structured_logging:
                    # JSON structured logging
                    logger.add(
                        log_path,
                        level=settings.level.value,
                        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
                        rotation=settings.log_rotation,
                        retention=settings.log_retention,
                        compression=settings.log_compression,
                        serialize=True,
                    )
                else:
                    # Regular text logging
                    logger.add(
                        log_path,
                        level=settings.level.value,
                        format=settings.format,
                        rotation=settings.log_rotation,
                        retention=settings.log_retention,
                        compression=settings.log_compression,
                    )

            cls._initialized = True
            cls._current_config = settings
            logger.info("Logging configuration initialized")

        except Exception as e:
            raise ConfigurationError(f"Failed to setup logging: {e}") from e

    @classmethod
    def get_logger(cls, name: str) -> "logger":
        """Get a logger instance with the given name"""
        return logger.bind(name=name)

    @classmethod
    def update_log_level(cls, level: LogLevel) -> None:
        """Update the logging level"""
        if not cls._initialized:
            raise ConfigurationError("Logging not initialized")

        try:
            # Remove existing handlers and recreate with new level
            logger.remove()

            if cls._current_config:
                cls._current_config.level = level
                cls.setup_logging(cls._current_config)

        except Exception as e:
            logger.error(f"Failed to update log level: {e}")

    @classmethod
    def add_custom_handler(cls, handler_config: dict[str, Any]) -> None:
        """Add a custom logging handler"""
        try:
            logger.add(**handler_config)
            logger.debug(f"Added custom logging handler: {handler_config}")
        except Exception as e:
            logger.error(f"Failed to add custom handler: {e}")

    @classmethod
    def is_initialized(cls) -> bool:
        """Check if logging is initialized"""
        return cls._initialized

    @classmethod
    def get_current_config(cls) -> LoggingSettings | None:
        """Get current logging configuration"""
        return cls._current_config

    @classmethod
    def _disable_other_loggers(cls) -> None:
        """Disable all other loggers when verbose mode is enabled"""
        import logging

        # Set the root logger to CRITICAL and disable it
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.CRITICAL)
        root_logger.disabled = True

        # Remove all handlers from the root logger
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Disable common third-party library loggers
        third_party_loggers = [
            "urllib3",
            "requests",
            "httpx",
            "httpcore",
            "openai",
            "anthropic",
            "litellm",
            "sqlalchemy",
            "alembic",
            "asyncio",
            "concurrent.futures",
            "charset_normalizer",
            "certifi",
            "idna",
        ]

        for logger_name in third_party_loggers:
            lib_logger = logging.getLogger(logger_name)
            lib_logger.disabled = True
            lib_logger.setLevel(logging.CRITICAL)
            # Remove all handlers
            for handler in lib_logger.handlers[:]:
                lib_logger.removeHandler(handler)

        # Set all existing loggers to CRITICAL level and disable them
        for name in list(logging.Logger.manager.loggerDict.keys()):
            existing_logger = logging.getLogger(name)
            existing_logger.setLevel(logging.CRITICAL)
            existing_logger.disabled = True
            # Remove all handlers
            for handler in existing_logger.handlers[:]:
                existing_logger.removeHandler(handler)

        # Also disable warnings from the warnings module
        import warnings

        warnings.filterwarnings("ignore")

        # Override the logging module's basicConfig to prevent new loggers
        def disabled_basicConfig(*args, **kwargs):
            pass

        logging.basicConfig = disabled_basicConfig

        # Override the getLogger function to disable new loggers immediately
        original_getLogger = logging.getLogger

        def disabled_getLogger(name=None):
            logger_instance = original_getLogger(name)
            logger_instance.disabled = True
            logger_instance.setLevel(logging.CRITICAL)
            for handler in logger_instance.handlers[:]:
                logger_instance.removeHandler(handler)
            return logger_instance

        logging.getLogger = disabled_getLogger


def get_logger(name: str = "memori") -> "logger":
    """Convenience function to get a logger"""
    return LoggingManager.get_logger(name)
