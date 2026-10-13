from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from memori._exceptions import UnsupportedProvisionedDatabaseFamilyError
from memori.provisioning._cache import ProvisionCache, cache_key
from memori.provisioning._models import ProvisionResult
from memori.provisioning._registry import provision
from memori.provisioning._utils import (
    mysql_connection_factory,
    postgresql_connection_factory,
    redact_dsn,
    require_mysql_driver,
    require_psycopg_driver,
)

# Import providers to trigger registration decorators.
importlib.import_module("memori.provisioning.providers")

if TYPE_CHECKING:
    from memori import Memori

SUPPORTED_FAMILIES = {"mysql", "postgresql"}
MYSQL_PROVIDERS = {"tidb-zero"}
POSTGRESQL_PROVIDERS = {"neon-launchpad"}


def get_provision_result(
    *,
    provider: str,
    cache: bool = True,
    tag: str = "memori",
    cache_key_override: str | None = None,
    **kwargs: Any,
) -> ProvisionResult:
    if cache:
        resolved_cache_key = cache_key(provider, tag, cache_key_override)
        provision_cache = ProvisionCache()
        cached = provision_cache.get(resolved_cache_key)
        if cached is not None:
            return cached

    result = provision(provider, tag=tag, **kwargs)
    _validate_family(result)
    if cache:
        provision_cache.set(resolved_cache_key, result)
    return result


def provision_memori(
    *,
    provider: str,
    build: bool = True,
    cache: bool = True,
    tag: str = "memori",
    cache_key: str | None = None,
    **kwargs: Any,
) -> Memori:
    from memori import Memori

    if provider in MYSQL_PROVIDERS:
        require_mysql_driver("TiDB Zero")
    if provider in POSTGRESQL_PROVIDERS:
        require_psycopg_driver(provider.replace("-", " ").title())

    result = get_provision_result(
        provider=provider,
        cache=cache,
        tag=tag,
        cache_key_override=cache_key,
        **kwargs,
    )
    _validate_family(result)

    if result.family == "postgresql":
        conn = postgresql_connection_factory(result.dsn)
    else:
        conn = mysql_connection_factory(result.dsn, result.connect_args)

    mem = Memori(conn=conn)
    mem.config.provision_result = result
    if build:
        mem.config.storage.build()
    return mem


def _validate_family(result: ProvisionResult) -> None:
    if result.family not in SUPPORTED_FAMILIES:
        raise UnsupportedProvisionedDatabaseFamilyError(result.family)


__all__ = [
    "ProvisionResult",
    "get_provision_result",
    "provision_memori",
    "redact_dsn",
]
