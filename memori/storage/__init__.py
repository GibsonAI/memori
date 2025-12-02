r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from memori.storage._manager import Manager

# Import adapters and drivers to trigger their self-registration decorators.
# Order matters: more specific matchers (sqlalchemy, django) before generic ones (mongodb, dbapi)
from memori.storage.adapters import sqlalchemy, django, mongodb, dbapi  # noqa: F401
from memori.storage.drivers import (
    mongodb as mongodb_driver,  # noqa: F401
)
from memori.storage.drivers import (
    mysql,  # noqa: F401
    oracle,  # noqa: F401
    postgresql,  # noqa: F401
    sqlite,  # noqa: F401
)

__all__ = ["Manager"]
