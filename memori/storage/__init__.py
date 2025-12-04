r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import importlib

from memori.storage._manager import Manager


def _import_optional_module(module_path: str) -> None:
    try:
        importlib.import_module(module_path)
    except ImportError:
        pass


# Import adapters and drivers to trigger their self-registration decorators.
# Order matters: more specific matchers (sqlalchemy, django) before generic ones (mongodb, dbapi)
for adapter in ("sqlalchemy", "django", "mongodb", "dbapi"):
    _import_optional_module(f"memori.storage.adapters.{adapter}")

for driver in ("mongodb", "mysql", "oracle", "postgresql", "sqlite"):
    _import_optional_module(f"memori.storage.drivers.{driver}")

__all__ = ["Manager"]
