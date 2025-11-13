"""
Centralized logging configuration for Memoriai
"""

import logging
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
            if not cls._initialized:
                logger.remove()

            # Always intercept other loggers (LiteLLM, OpenAI, httpcore, etc.)
            cls._disable_other_loggers()

            # ALWAYS suppress LiteLLM's own logger to avoid duplicate logs
            # We'll show LiteLLM logs through our interceptor only
            try:
                import litellm

                litellm.suppress_debug_info = True
                litellm.set_verbose = False
                # Set litellm's logger to ERROR level to prevent duplicate logs
                litellm_logger = logging.getLogger("LiteLLM")
                litellm_logger.setLevel(logging.ERROR)
            except ImportError:
                # LiteLLM is an optional dependency, skip if not installed
                pass

            if verbose:
                logger.add(
                    sys.stderr,
                    level="DEBUG",
                    format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | {message}",
                    colorize=True,
                    backtrace=True,
                    diagnose=True,
                )
            else:
                logger.add(
                    sys.stderr,
                    level="ERROR",
                    format="<level>{level}</level>: {message}",
                    colorize=False,
                    backtrace=False,
                    diagnose=False,
                )

            if settings.log_to_file:
                log_path = Path(settings.log_file_path)
                log_path.parent.mkdir(parents=True, exist_ok=True)

                if settings.structured_logging:
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
        """
        Intercept all logs from the standard `logging` module and redirect them to Loguru.
        This ensures all log output is controlled and formatted by Loguru.
        """

        # Suppress asyncio internal DEBUG logs entirely
        # These logs like "[asyncio] Using selector: KqueueSelector" provide no value to users
        logging.getLogger("asyncio").setLevel(logging.WARNING)

        class InterceptStandardLoggingHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                # Filter DEBUG/INFO logs from OpenAI, httpcore, LiteLLM, httpx, asyncio
                # Only show their ERROR logs, but keep all Memori DEBUG logs
                suppressed_loggers = (
                    "openai",
                    "httpcore",
                    "LiteLLM",
                    "httpx",
                    "asyncio",
                )
                if record.name.startswith(suppressed_loggers):
                    # Only emit ERROR and above for these loggers
                    if record.levelno < logging.ERROR:
                        return

                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno

                frame, depth = logging.currentframe(), 2
                while (
                    frame is not None and frame.f_code.co_filename == logging.__file__
                ):
                    frame = frame.f_back
                    depth += 1

                formatted_message = f"[{record.name}] {record.getMessage()}"

                logger.opt(depth=depth, exception=record.exc_info).log(
                    level, formatted_message
                )

        logging.basicConfig(
            handlers=[InterceptStandardLoggingHandler()], level=0, force=True
        )


def get_logger(name: str = "memori") -> "logger":
    """Convenience function to get a logger"""
    return LoggingManager.get_logger(name)
