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
