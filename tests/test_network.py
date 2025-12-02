import os
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
import requests
from requests.adapters import HTTPAdapter

from memori._config import Config
from memori._exceptions import QuotaExceededError
from memori._network import Api, _ApiRetryRecoverable


@pytest.fixture
def api():
    os.environ["MEMORI_API_URL_BASE"] = "https://test.api.com"
    return Api(Config())


@pytest.fixture
def config():
    return Config()


class TestApiRetryRecoverable:
    def test_is_retry_returns_true_for_5xx_errors(self):
        retry = _ApiRetryRecoverable()
        assert retry.is_retry("GET", 500) is True
        assert retry.is_retry("GET", 503) is True
        assert retry.is_retry("GET", 599) is True

    def test_is_retry_returns_false_for_non_5xx_errors(self):
        retry = _ApiRetryRecoverable()
        assert retry.is_retry("GET", 200) is False
        assert retry.is_retry("GET", 404) is False
        assert retry.is_retry("GET", 400) is False


class TestApiInitialization:
    def test_init_uses_default_api_key_and_base_url(self):
        if "MEMORI_API_URL_BASE" in os.environ:
            del os.environ["MEMORI_API_URL_BASE"]

        api = Api(Config())
        assert api._Api__x_api_key == "96a7ea3e-11c2-428c-b9ae-5a168363dc80"  # type: ignore[attr-defined]
        assert api._Api__base == "https://api.memorilabs.ai"  # type: ignore[attr-defined]

    def test_init_uses_custom_base_url(self):
        os.environ["MEMORI_API_URL_BASE"] = "https://custom.api.com"
        api = Api(Config())
        assert api._Api__x_api_key == "c18b1022-7fe2-42af-ab01-b1f9139184f0"  # type: ignore[attr-defined]
        assert api._Api__base == "https://custom.api.com"  # type: ignore[attr-defined]


class TestApiUrl:
    def test_url_construction(self, api):
        assert api.url("test/route") == "https://test.api.com/v1/test/route"

    def test_url_with_empty_route(self, api):
        assert api.url("") == "https://test.api.com/v1/"


class TestApiHeaders:
    def test_headers_without_api_key(self, api):
        if "MEMORI_API_KEY" in os.environ:
            del os.environ["MEMORI_API_KEY"]

        headers = api.headers()
        assert "X-Memori-API-Key" in headers
        assert "Authorization" not in headers

    def test_headers_with_api_key(self, api):
        os.environ["MEMORI_API_KEY"] = "test-api-key-123"
        headers = api.headers()
        assert headers["Authorization"] == "Bearer test-api-key-123"
        assert "X-Memori-API-Key" in headers


class TestApiPost:
    def test_post_success(self, api, mocker):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mocker.patch.object(api, "_Api__session", return_value=mock_session)

        result = api.post("test/endpoint", json={"data": "test"})

        assert result == {"result": "success"}
        mock_session.post.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    def test_post_raises_http_error(self, api, mocker):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mocker.patch.object(api, "_Api__session", return_value=mock_session)

        with pytest.raises(requests.HTTPError):
            api.post("test/endpoint")


class TestApiPostAsync:
    @pytest.mark.asyncio
    async def test_post_async_success(self, api, mocker):
        mock_response = {"result": "async success"}
        mock_request_async = AsyncMock(return_value=mock_response)
        mocker.patch.object(api, "_Api__request_async", mock_request_async)

        result = await api.post_async("test/endpoint", json={"data": "test"})
        assert result == {"result": "async success"}

    @pytest.mark.asyncio
    async def test_post_async_with_retry_on_5xx_error(self, api, mocker):
        error = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=503
        )
        success_response = {"result": "success after retry"}

        mock_response_ctx_fail = MagicMock()
        mock_response_ctx_fail.__aenter__.return_value = MagicMock()
        mock_response_ctx_fail.__aenter__.return_value.raise_for_status.side_effect = (
            error
        )
        mock_response_ctx_fail.__aexit__.return_value = None

        mock_response_ctx_success = MagicMock()
        mock_response_success = MagicMock()
        mock_response_success.raise_for_status = MagicMock()
        mock_response_success.json = AsyncMock(return_value=success_response)
        mock_response_ctx_success.__aenter__.return_value = mock_response_success
        mock_response_ctx_success.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.request.side_effect = [
            mock_response_ctx_fail,
            mock_response_ctx_success,
        ]
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await api.post_async("test/endpoint")
                assert result == success_response
                assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_post_async_raises_on_4xx_error(self, api):
        error = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=404
        )

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = error

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(aiohttp.ClientResponseError):
                await api.post_async("test/endpoint")

    @pytest.mark.asyncio
    async def test_post_async_raises_after_max_retries(self, api):
        error = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=503
        )

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = error

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(aiohttp.ClientResponseError):
                    await api.post_async("test/endpoint")


class TestApiAugmentation:
    @pytest.mark.asyncio
    async def test_augmentation_async_success(self, api, mocker):
        mock_response_data = {
            "conversation": {"summary": "Test summary"},
            "entity": {"facts": ["fact1", "fact2"]},
            "process": {"attributes": []},
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        payload = {
            "conversation": {
                "messages": [{"role": "user", "content": "test"}],
                "summary": "Test summary",
            },
            "meta": {},
        }

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await api.augmentation_async(payload)

        assert result is not None
        assert result == mock_response_data

    @pytest.mark.asyncio
    async def test_augmentation_async_includes_storage_in_payload(self, api, mocker):
        mock_response_data = {
            "conversation": {"summary": "Test summary"},
            "entity": {"facts": []},
            "process": {"attributes": []},
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        payload = {
            "conversation": {
                "messages": [{"role": "user", "content": "test"}],
                "summary": "Test summary",
            },
            "meta": {
                "storage": {"cockroachdb": True, "dialect": "cockroachdb"},
            },
        }

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await api.augmentation_async(payload)

        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        sent_payload = call_args[1]["json"]

        assert "meta" in sent_payload
        assert "storage" in sent_payload["meta"]
        assert sent_payload["meta"]["storage"]["cockroachdb"] is True
        assert sent_payload["meta"]["storage"]["dialect"] == "cockroachdb"

    @pytest.mark.asyncio
    async def test_augmentation_async_mysql_dialect(self, api, mocker):
        mock_response_data = {
            "conversation": {"summary": "Test summary"},
            "entity": {"facts": []},
            "process": {"attributes": []},
        }

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        payload = {
            "conversation": {
                "messages": [{"role": "user", "content": "test"}],
                "summary": "Test summary",
            },
            "meta": {
                "storage": {"cockroachdb": False, "dialect": "mysql"},
            },
        }

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await api.augmentation_async(payload)

        call_args = mock_session.post.call_args
        sent_payload = call_args[1]["json"]

        assert sent_payload["meta"]["storage"]["cockroachdb"] is False
        assert sent_payload["meta"]["storage"]["dialect"] == "mysql"


class TestApiPostAsyncGenericException:
    @pytest.mark.asyncio
    async def test_post_async_retries_on_generic_exception(self, api):
        """Test that generic exceptions (not ClientResponseError) also trigger retry logic."""
        generic_error = RuntimeError("Network timeout")
        success_response = {"result": "success after retry"}

        mock_response_ctx_fail = MagicMock()
        mock_response_ctx_fail.__aenter__.side_effect = generic_error
        mock_response_ctx_fail.__aexit__.return_value = None

        mock_response_ctx_success = MagicMock()
        mock_response_success = MagicMock()
        mock_response_success.raise_for_status = MagicMock()
        mock_response_success.json = AsyncMock(return_value=success_response)
        mock_response_ctx_success.__aenter__.return_value = mock_response_success
        mock_response_ctx_success.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.request.side_effect = [
            mock_response_ctx_fail,
            mock_response_ctx_success,
        ]
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                result = await api.post_async("test/endpoint")
                assert result == success_response
                assert mock_sleep.call_count == 1

    @pytest.mark.asyncio
    async def test_post_async_raises_generic_exception_after_max_retries(self, api):
        """Test that generic exceptions raise after max retries."""
        generic_error = RuntimeError("Persistent network error")

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.side_effect = generic_error
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.request.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RuntimeError, match="Persistent network error"):
                    await api.post_async("test/endpoint")


class TestApiSession:
    def test_session_creates_session_with_retry_adapter(self, api):
        """Test that __session creates a properly configured requests Session."""
        session = api._Api__session()

        assert isinstance(session, requests.Session)

        # Check that adapters are mounted
        https_adapter = session.get_adapter("https://example.com")
        http_adapter = session.get_adapter("http://example.com")

        assert https_adapter is not None
        assert http_adapter is not None
        assert isinstance(https_adapter, HTTPAdapter)
        assert isinstance(http_adapter, HTTPAdapter)


class TestApiQuotaEnforcement:
    @pytest.mark.asyncio
    async def test_augmentation_async_raises_quota_exceeded_with_api_message(self, api):
        if "MEMORI_API_KEY" in os.environ:
            del os.environ["MEMORI_API_KEY"]

        api_error_message = "You have exceeded your quota. Please upgrade your plan."

        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={"message": api_error_message})
        mock_response.raise_for_status = MagicMock()

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(QuotaExceededError) as exc_info:
                await api.augmentation_async({"test": "payload"})
            assert str(exc_info.value) == api_error_message

    @pytest.mark.asyncio
    async def test_augmentation_async_raises_quota_exceeded_with_default_message(
        self, api
    ):
        if "MEMORI_API_KEY" in os.environ:
            del os.environ["MEMORI_API_KEY"]

        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={})
        mock_response.raise_for_status = MagicMock()

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(QuotaExceededError) as exc_info:
                await api.augmentation_async({"test": "payload"})
            assert (
                "your IP address is over quota; register for an API key now: "
                + "https://app.memorilabs.ai/signup"
                in str(exc_info.value)
            )

    @pytest.mark.asyncio
    async def test_augmentation_async_raises_quota_exceeded_when_json_fails(self, api):
        if "MEMORI_API_KEY" in os.environ:
            del os.environ["MEMORI_API_KEY"]

        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(side_effect=Exception("JSON parse error"))
        mock_response.raise_for_status = MagicMock()

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(QuotaExceededError) as exc_info:
                await api.augmentation_async({"test": "payload"})
            assert (
                "your IP address is over quota; register for an API key now: "
                + "https://app.memorilabs.ai/signup"
                in str(exc_info.value)
            )

    @pytest.mark.asyncio
    async def test_augmentation_async_returns_empty_dict_for_authenticated_429(
        self, api
    ):
        os.environ["MEMORI_API_KEY"] = "test-key"

        mock_response = MagicMock()
        mock_response.status = 429
        mock_response.raise_for_status = MagicMock()

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await api.augmentation_async({"test": "payload"})
            assert result == {}

    @pytest.mark.asyncio
    async def test_augmentation_async_raises_other_errors_for_anonymous(self, api):
        if "MEMORI_API_KEY" in os.environ:
            del os.environ["MEMORI_API_KEY"]

        error = aiohttp.ClientResponseError(
            request_info=MagicMock(), history=(), status=500
        )

        mock_response = MagicMock()
        mock_response.status = 500
        mock_response.raise_for_status = MagicMock(side_effect=error)

        mock_response_ctx = MagicMock()
        mock_response_ctx.__aenter__.return_value = mock_response
        mock_response_ctx.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.post.return_value = mock_response_ctx
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await api.augmentation_async({"test": "payload"})
            assert exc_info.value.status == 500

    def test_is_anonymous_returns_true_without_api_key(self, api):
        if "MEMORI_API_KEY" in os.environ:
            del os.environ["MEMORI_API_KEY"]
        assert api._is_anonymous() is True

    def test_is_anonymous_returns_false_with_api_key(self, api):
        os.environ["MEMORI_API_KEY"] = "test-key"
        assert api._is_anonymous() is False
