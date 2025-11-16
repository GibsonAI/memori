"""
Utility helper functions for Memoriai
"""

import asyncio
import functools
import hashlib
import json
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypeVar

from .exceptions import MemoriError

T = TypeVar("T")


class StringUtils:
    """String manipulation utilities"""

    @staticmethod
    def generate_id(prefix: str = "") -> str:
        """Generate a unique ID"""
        unique_id = str(uuid.uuid4())
        return f"{prefix}{unique_id}" if prefix else unique_id

    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Truncate text to specified length"""
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe file system usage"""
        import re

        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(" .")
        # Ensure it's not empty
        return sanitized or "unnamed"

    @staticmethod
    def hash_text(text: str, algorithm: str = "sha256") -> str:
        """Generate hash of text"""
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(text.encode("utf-8"))
        return hash_obj.hexdigest()

    @staticmethod
    def extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
        """Extract keywords from text (simple implementation)"""
        import re

        # Simple keyword extraction - remove common stopwords
        stopwords = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "between",
            "among",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "this",
            "that",
            "these",
            "those",
            "i",
            "you",
            "he",
            "she",
            "it",
            "we",
            "they",
        }

        # Extract words (alphanumeric sequences)
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())

        # Filter out stopwords and get unique words
        keywords = list({word for word in words if word not in stopwords})

        # Sort by length (longer words often more meaningful)
        keywords.sort(key=len, reverse=True)

        return keywords[:max_keywords]


class DateTimeUtils:
    """Date and time utilities"""

    @staticmethod
    def now() -> datetime:
        """Get current datetime"""
        return datetime.now()

    @staticmethod
    def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """Format datetime to string"""
        return dt.strftime(format_str)

    @staticmethod
    def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
        """Parse datetime from string"""
        return datetime.strptime(dt_str, format_str)

    @staticmethod
    def add_days(dt: datetime, days: int) -> datetime:
        """Add days to datetime"""
        return dt + timedelta(days=days)

    @staticmethod
    def subtract_days(dt: datetime, days: int) -> datetime:
        """Subtract days from datetime"""
        return dt - timedelta(days=days)

    @staticmethod
    def is_expired(dt: datetime, expiry_hours: int = 24) -> bool:
        """Check if datetime is expired"""
        return datetime.now() > dt + timedelta(hours=expiry_hours)

    @staticmethod
    def time_ago_string(dt: datetime) -> str:
        """Generate human-readable time ago string"""
        now = datetime.now()
        diff = now - dt

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "just now"


class JsonUtils:
    """JSON handling utilities"""

    @staticmethod
    def safe_loads(json_str: str, default: Any = None) -> Any:
        """Safely load JSON string"""
        try:
            return json.loads(json_str) if json_str else default
        except (json.JSONDecodeError, TypeError):
            return default

    @staticmethod
    def safe_dumps(obj: Any, default: Any = None, indent: int = 2) -> str:
        """Safely dump object to JSON string"""
        try:
            return json.dumps(obj, default=str, indent=indent, ensure_ascii=False)
        except (TypeError, ValueError):
            return json.dumps(default or {}, indent=indent)

    @staticmethod
    def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = JsonUtils.merge_dicts(result[key], value)
            else:
                result[key] = value

        return result


class FileUtils:
    """File handling utilities"""

    @staticmethod
    def ensure_directory(path: str | Path) -> Path:
        """Ensure directory exists, create if not"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def safe_read_text(file_path: str | Path, encoding: str = "utf-8") -> str | None:
        """Safely read text file"""
        try:
            return Path(file_path).read_text(encoding=encoding)
        except (FileNotFoundError, PermissionError, UnicodeDecodeError):
            return None

    @staticmethod
    def safe_write_text(
        file_path: str | Path, content: str, encoding: str = "utf-8"
    ) -> bool:
        """Safely write text file"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding=encoding)
            return True
        except (PermissionError, UnicodeEncodeError):
            return False

    @staticmethod
    def get_file_size(file_path: str | Path) -> int:
        """Get file size in bytes"""
        try:
            return Path(file_path).stat().st_size
        except (FileNotFoundError, PermissionError):
            return 0

    @staticmethod
    def is_file_recent(file_path: str | Path, hours: int = 24) -> bool:
        """Check if file was modified recently"""
        try:
            mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
            return not DateTimeUtils.is_expired(mtime, hours)
        except (FileNotFoundError, PermissionError):
            return False


class RetryUtils:
    """Retry and error handling utilities"""

    @staticmethod
    def retry_on_exception(
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,),
    ) -> Callable:
        """Decorator for retrying function calls on exceptions"""

        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> T:
                last_exception = None
                last_tb = None

                for attempt in range(max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        # capture exception and its traceback so we can re-raise
                        last_exception = e
                        last_tb = e.__traceback__
                        if attempt < max_attempts - 1:
                            sleep_time = delay * (backoff**attempt)
                            import time

                            time.sleep(sleep_time)
                        continue

                # If all attempts failed, re-raise the last exception preserving traceback
                if last_exception is not None:
                    if last_tb is not None:
                        raise last_exception.with_traceback(last_tb)
                    raise last_exception

                # This shouldn't happen, but just in case
                raise MemoriError("Retry attempts exhausted")

            return wrapper

        return decorator

    @staticmethod
    async def async_retry_on_exception(
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff: float = 2.0,
        exceptions: tuple = (Exception,),
    ) -> Callable:
        """Async decorator for retrying function calls on exceptions"""

        def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> T:
                last_exception = None
                last_tb = None

                for attempt in range(max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        # capture exception and its traceback so we can re-raise
                        last_exception = e
                        last_tb = e.__traceback__
                        if attempt < max_attempts - 1:
                            sleep_time = delay * (backoff**attempt)
                            await asyncio.sleep(sleep_time)
                        continue

                if last_exception is not None:
                    if last_tb is not None:
                        raise last_exception.with_traceback(last_tb)
                    raise last_exception

                raise MemoriError("Async retry attempts exhausted")

            return wrapper

        return decorator


class PerformanceUtils:
    """Performance monitoring utilities"""

    @staticmethod
    def time_function(func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to time function execution"""

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import time

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                execution_time = end_time - start_time

                # Log execution time (you can customize this)
                from .logging import get_logger

                logger = get_logger("performance")
                logger.debug(
                    f"{func.__name__} executed in {execution_time:.4f} seconds"
                )

                return result
            except Exception as e:
                end_time = time.time()
                execution_time = end_time - start_time

                from .logging import get_logger

                logger = get_logger("performance")
                logger.error(
                    f"{func.__name__} failed after {execution_time:.4f} seconds: {e}"
                )

                raise

        return wrapper

    @staticmethod
    def memory_usage() -> dict[str, float]:
        """Get current memory usage"""
        try:
            import psutil

            process = psutil.Process()
            memory_info = process.memory_info()

            return {
                "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size
                "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                "percent": process.memory_percent(),
            }
        except ImportError:
            return {"error": "psutil not available"}
        except Exception as e:
            return {"error": str(e)}


class AsyncUtils:
    """Async utilities"""

    @staticmethod
    async def run_in_executor(func: Callable[..., T], *args, **kwargs) -> T:
        """Run synchronous function in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, functools.partial(func, **kwargs), *args
        )

    @staticmethod
    async def gather_with_concurrency(limit: int, *tasks) -> list[Any]:
        """Run tasks with concurrency limit"""
        semaphore = asyncio.Semaphore(limit)

        async def sem_task(task):
            async with semaphore:
                return await task

        return await asyncio.gather(*[sem_task(task) for task in tasks])

    @staticmethod
    def create_task_with_timeout(coro: Awaitable[T], timeout: float) -> asyncio.Task:
        """Create task with timeout"""
        return asyncio.create_task(asyncio.wait_for(coro, timeout=timeout))
