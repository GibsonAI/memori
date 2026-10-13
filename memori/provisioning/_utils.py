from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse, urlunparse

import certifi

from memori._exceptions import MissingPsycopgError, MissingPyMySQLError

DEFAULT_MYSQL_DATABASE = "memori"
DEFAULT_POSTGRESQL_DATABASE = "memori"


def mysql_tls_connect_args() -> dict[str, Any]:
    return {
        "ssl": {
            "ca": certifi.where(),
            "check_hostname": True,
            "verify_mode": "required",
        }
    }


def require_mysql_driver(database: str = "TiDB Zero") -> Any:
    try:
        import pymysql
    except ImportError as e:
        raise MissingPyMySQLError(database) from e
    return pymysql


def redact_dsn(dsn: str) -> str:
    parsed = urlparse(dsn)
    if not parsed.scheme or not parsed.netloc:
        return dsn

    username = parsed.username
    password = parsed.password
    if username is None and password is None:
        return dsn

    host = parsed.hostname or ""
    userinfo = quote(username or "", safe="")
    if password is not None:
        userinfo += ":****"

    if ":" in host and not host.startswith("["):
        host = f"[{host}]"

    netloc = f"{userinfo}@{host}" if userinfo else host
    if parsed.port is not None:
        netloc = f"{netloc}:{parsed.port}"

    return urlunparse(parsed._replace(netloc=netloc))


def mysql_connection_factory(
    dsn: str,
    connect_args: dict[str, Any] | None = None,
) -> Callable[[], Any]:
    pymysql = require_mysql_driver("TiDB Zero")

    kwargs = _mysql_kwargs_from_dsn(dsn)
    kwargs.update(connect_args or {})
    if kwargs.get("ssl") == {}:
        kwargs.update(mysql_tls_connect_args())
    bootstrap_database = None
    if not kwargs.get("database"):
        kwargs.pop("database", None)
        bootstrap_database = DEFAULT_MYSQL_DATABASE

    return lambda: _connect_mysql(pymysql, kwargs, bootstrap_database)


def _connect_mysql(pymysql: Any, kwargs: dict[str, Any], database: str | None) -> Any:
    conn = pymysql.connect(**kwargs)
    if database is not None:
        _ensure_database(conn, database)
    return conn


def _mysql_kwargs_from_dsn(dsn: str) -> dict[str, Any]:
    parsed = urlparse(dsn)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise ValueError(f"Unsupported TiDB Zero DSN scheme: {parsed.scheme}")

    if parsed.hostname is None:
        raise ValueError("TiDB Zero DSN must include a hostname")

    kwargs: dict[str, Any] = {
        "host": parsed.hostname,
        "port": parsed.port or 4000,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": unquote(parsed.path.lstrip("/")),
    }

    query = parse_qs(parsed.query, keep_blank_values=True)
    ssl_mode = _first(query, "ssl-mode") or _first(query, "sslmode")
    if ssl_mode is not None and ssl_mode.lower() not in {"disable", "disabled"}:
        kwargs.update(mysql_tls_connect_args())

    charset = _first(query, "charset")
    if charset:
        kwargs["charset"] = charset

    return kwargs


def _ensure_database(conn: Any, database: str) -> None:
    escaped = database.replace("`", "``")
    cursor = conn.cursor()
    try:
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{escaped}`")
        cursor.execute(f"USE `{escaped}`")
        conn.commit()
    finally:
        cursor.close()


def _first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    return values[0]


def require_psycopg_driver(database: str = "PostgreSQL") -> Any:
    try:
        import psycopg
    except ImportError as e:
        raise MissingPsycopgError(database) from e
    return psycopg


def postgresql_connection_factory(dsn: str) -> Callable[[], Any]:
    psycopg = require_psycopg_driver("Neon Launchpad")
    return lambda: psycopg.connect(dsn)
