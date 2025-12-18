r"""
 _  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""

import warnings
from importlib.metadata import PackageNotFoundError, distribution


class QuotaExceededError(Exception):
    def __init__(
        self,
        message=(
            "your IP address is over quota; register for an API key now: "
            + "https://app.memorilabs.ai/signup"
        ),
    ):
        self.message = message
        super().__init__(self.message)


class MemoriApiError(Exception):
    pass


class MemoriApiClientError(MemoriApiError):
    def __init__(
        self,
        status_code: int,
        message: str | None = None,
        details: object | None = None,
    ):
        self.status_code = status_code
        self.details = details
        super().__init__(
            message or f"Memori API request failed with status {status_code}"
        )


class MemoriApiValidationError(MemoriApiClientError):
    pass


class MemoriApiRequestRejectedError(MemoriApiClientError):
    pass


class MemoriLegacyPackageWarning(UserWarning):
    """Warning emitted when the legacy `memorisdk` package is installed."""


def warn_if_legacy_memorisdk_installed() -> None:
    try:
        distribution("memorisdk")
    except PackageNotFoundError:
        return

    warnings.warn(
        "You have Memori installed under the legacy package name 'memorisdk'. "
        "That name is deprecated and will stop receiving updates. "
        "Please switch to 'memori':\n\n"
        "    pip uninstall memorisdk\n"
        "    pip install memori\n",
        MemoriLegacyPackageWarning,
        stacklevel=3,
    )
