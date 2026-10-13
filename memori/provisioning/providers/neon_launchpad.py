from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import requests

from memori.provisioning._models import ProvisionResult
from memori.provisioning._registry import Registry

NEON_LAUNCHPAD_HOST = "https://neon.new"
NEON_LAUNCHPAD_REFERRER = "memori"
_NEON_LAUNCHPAD_TTL_DAYS = 3


@Registry.register_provider("neon-launchpad")
def provision_neon_launchpad(
    *,
    referrer: str = NEON_LAUNCHPAD_REFERRER,
    timeout: int = 30,
    host: str | None = None,
    **_kwargs: Any,
) -> ProvisionResult:
    resolved_host = host or NEON_LAUNCHPAD_HOST
    db_id = str(uuid.uuid4())

    create_url = (
        f"{resolved_host}/api/v1/database/{db_id}?referrer={quote(referrer, safe='')}"
    )
    create_response = requests.post(
        create_url,
        headers={"Content-Type": "application/json"},
        json={"enable_logical_replication": False},
        timeout=timeout,
    )
    create_response.raise_for_status()

    get_url = f"{resolved_host}/api/v1/database/{db_id}"
    data_response = requests.get(
        get_url,
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    data_response.raise_for_status()
    return parse_neon_launchpad_response(data_response.json(), db_id, resolved_host)


def parse_neon_launchpad_response(
    data: dict[str, Any],
    db_id: str,
    host: str = NEON_LAUNCHPAD_HOST,
) -> ProvisionResult:
    dsn = data.get("connection_string")
    if not isinstance(dsn, str) or not dsn:
        raise ValueError("Neon Launchpad response did not include a connection_string")

    claim_url = f"{host}/database/{db_id}"
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=_NEON_LAUNCHPAD_TTL_DAYS)
    ).isoformat()

    return ProvisionResult(
        provider="neon-launchpad",
        family="postgresql",
        dsn=dsn,
        claim_url=claim_url,
        expires_at=expires_at,
        metadata={"id": db_id},
    )
