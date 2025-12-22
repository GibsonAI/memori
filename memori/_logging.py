r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""

import copy
import logging

logger = logging.getLogger(__name__)

# Global setting for truncation (controlled by Config.debug_truncate)
_truncate_enabled = True


def set_truncate_enabled(enabled: bool) -> None:
    """Set whether truncation is enabled for debug logs."""
    global _truncate_enabled
    _truncate_enabled = enabled
    logger.debug("Debug truncation %s", "enabled" if enabled else "disabled")


def truncate(text: str, max_len: int = 200) -> str:
    """Truncate text for debug logging.

    Respects the global _truncate_enabled setting. When disabled,
    returns the full text regardless of length.

    Args:
        text: The text to truncate.
        max_len: Maximum length before truncation (default: 200).

    Returns:
        Original text if truncation disabled or under max_len,
        otherwise truncated with '...'
    """
    if not text:
        return text
    if not _truncate_enabled:
        return text
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def sanitize_payload(payload: dict) -> dict:
    """Sanitize payload for safe logging by masking sensitive data.

    Removes or masks:
    - API keys
    - Authorization tokens

    Args:
        payload: The payload dictionary to sanitize.

    Returns:
        A deep copy of the payload with sensitive data masked.
    """
    sanitized = copy.deepcopy(payload)
    if "meta" in sanitized and "api" in sanitized["meta"]:
        if sanitized["meta"]["api"].get("key"):
            sanitized["meta"]["api"]["key"] = "***REDACTED***"
    return sanitized
