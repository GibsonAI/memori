import pytest
import requests

from memori.provisioning.providers.neon_launchpad import (
    NEON_LAUNCHPAD_HOST,
    NEON_LAUNCHPAD_REFERRER,
    provision_neon_launchpad,
)

_FAKE_DSN = (
    "postgresql://user:secret@ep-cool-darkness-123456.us-east-2.aws.neon.tech/neondb"
)
_FAKE_UUID = "11111111-2222-3333-4444-555555555555"


def _patch_uuid(mocker):
    mocker.patch(
        "memori.provisioning.providers.neon_launchpad.uuid.uuid4",
        return_value=_FAKE_UUID,
    )


def test_provision_neon_launchpad_posts_create_then_gets_connection(mocker):
    post_resp = mocker.Mock()
    get_resp = mocker.Mock()
    get_resp.json.return_value = {"connection_string": _FAKE_DSN}

    post = mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.post",
        return_value=post_resp,
    )
    get = mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.get",
        return_value=get_resp,
    )
    _patch_uuid(mocker)

    result = provision_neon_launchpad(timeout=10)

    post.assert_called_once_with(
        f"{NEON_LAUNCHPAD_HOST}/api/v1/database/{_FAKE_UUID}?referrer={NEON_LAUNCHPAD_REFERRER}",
        headers={"Content-Type": "application/json"},
        json={"enable_logical_replication": False},
        timeout=10,
    )
    get.assert_called_once_with(
        f"{NEON_LAUNCHPAD_HOST}/api/v1/database/{_FAKE_UUID}",
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    post_resp.raise_for_status.assert_called_once()
    get_resp.raise_for_status.assert_called_once()
    assert result.dsn == _FAKE_DSN
    assert result.provider == "neon-launchpad"
    assert result.family == "postgresql"
    assert result.claim_url == f"{NEON_LAUNCHPAD_HOST}/database/{_FAKE_UUID}"
    assert result.expires_at is not None
    assert result.metadata["id"] == _FAKE_UUID


def test_provision_neon_launchpad_supports_custom_referrer_and_host(mocker):
    post_resp = mocker.Mock()
    get_resp = mocker.Mock()
    get_resp.json.return_value = {"connection_string": _FAKE_DSN}

    post = mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.post",
        return_value=post_resp,
    )
    get = mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.get",
        return_value=get_resp,
    )
    _patch_uuid(mocker)

    provision_neon_launchpad(
        referrer="my-app",
        timeout=5,
        host="https://custom.neon.example.com",
    )

    post.assert_called_once_with(
        f"https://custom.neon.example.com/api/v1/database/{_FAKE_UUID}?referrer=my-app",
        headers={"Content-Type": "application/json"},
        json={"enable_logical_replication": False},
        timeout=5,
    )
    get.assert_called_once_with(
        f"https://custom.neon.example.com/api/v1/database/{_FAKE_UUID}",
        headers={"Content-Type": "application/json"},
        timeout=5,
    )


def test_provision_neon_launchpad_encodes_referrer_with_special_chars(mocker):
    post_resp = mocker.Mock()
    get_resp = mocker.Mock()
    get_resp.json.return_value = {"connection_string": _FAKE_DSN}

    post = mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.post",
        return_value=post_resp,
    )
    mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.get",
        return_value=get_resp,
    )
    _patch_uuid(mocker)

    provision_neon_launchpad(referrer="my app/v2", timeout=5)

    called_url = post.call_args[0][0]
    assert "my%20app%2Fv2" in called_url


def test_provision_neon_launchpad_propagates_create_http_errors(mocker):
    post_resp = mocker.Mock()
    post_resp.raise_for_status.side_effect = requests.HTTPError("503")
    mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.post",
        return_value=post_resp,
    )
    _patch_uuid(mocker)

    with pytest.raises(requests.HTTPError):
        provision_neon_launchpad()


def test_provision_neon_launchpad_propagates_get_http_errors(mocker):
    post_resp = mocker.Mock()
    get_resp = mocker.Mock()
    get_resp.raise_for_status.side_effect = requests.HTTPError("404")

    mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.post",
        return_value=post_resp,
    )
    mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.get",
        return_value=get_resp,
    )
    _patch_uuid(mocker)

    with pytest.raises(requests.HTTPError):
        provision_neon_launchpad()


def test_provision_neon_launchpad_raises_if_connection_string_missing(mocker):
    post_resp = mocker.Mock()
    get_resp = mocker.Mock()
    get_resp.json.return_value = {}

    mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.post",
        return_value=post_resp,
    )
    mocker.patch(
        "memori.provisioning.providers.neon_launchpad.requests.get",
        return_value=get_resp,
    )
    _patch_uuid(mocker)

    with pytest.raises(ValueError, match="connection_string"):
        provision_neon_launchpad()
