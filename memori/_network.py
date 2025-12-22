r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import asyncio
import logging
import os
import ssl

import aiohttp
import certifi
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from memori._config import Config
from memori._exceptions import (
    MemoriApiClientError,
    MemoriApiError,
    MemoriApiRequestRejectedError,
    MemoriApiValidationError,
    QuotaExceededError,
)

logger = logging.getLogger(__name__)


class Api:
    def __init__(self, config: Config):
        test_mode = os.environ.get("MEMORI_TEST_MODE") == "1"

        self.__base = os.environ.get("MEMORI_API_URL_BASE")

        if self.__base is None:
            if test_mode:
                # Use staging for test mode
                self.__x_api_key = "c18b1022-7fe2-42af-ab01-b1f9139184f0"
                self.__base = "https://staging-api.memorilabs.ai"
            else:
                # Use production
                self.__x_api_key = "96a7ea3e-11c2-428c-b9ae-5a168363dc80"
                self.__base = "https://api.memorilabs.ai"
        else:
            # Custom URL provided, use staging key as default
            self.__x_api_key = "c18b1022-7fe2-42af-ab01-b1f9139184f0"

        self.config = config

    async def augmentation_async(self, payload: dict) -> dict:
        url = self.url("sdk/augmentation")
        headers = self.headers()
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        logger.debug("Sending augmentation request to %s", url)

        def _default_client_error_message(status_code: int) -> str:
            if status_code == 422:
                return (
                    "Memori API rejected the request (422 validation error). "
                    "Check your augmentation payload structure."
                )
            if status_code == 433:
                return (
                    "The request was rejected (433). "
                    "This can sometimes be caused by certificate/SSL inspection or proxy issues. "
                    "If this persists, contact Memori Labs support via email at support@memorilabs.ai."
                )
            return f"Memori API request failed with status {status_code}."

        async def _read_error_payload(response: aiohttp.ClientResponse):
            try:
                data = await response.json()
            except Exception:
                return None, None

            if isinstance(data, dict):
                return data.get("message") or data.get("detail"), data
            return None, data

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=ssl_context)
        ) as session:
            try:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as r:
                    logger.debug("Augmentation response - status: %d", r.status)

                    if r.status == 429:
                        logger.warning("Rate limit exceeded (429)")
                        if self._is_anonymous():
                            message, _data = await _read_error_payload(r)

                            if message:
                                raise QuotaExceededError(message)
                            raise QuotaExceededError()
                        else:
                            return {}

                    if r.status == 422:
                        message, data = await _read_error_payload(r)
                        logger.error("Validation error (422): %s", message)
                        raise MemoriApiValidationError(
                            status_code=422,
                            message=message or _default_client_error_message(422),
                            details=data,
                        )

                    if r.status == 433:
                        message, data = await _read_error_payload(r)
                        logger.error("Request rejected (433): %s", message)
                        raise MemoriApiRequestRejectedError(
                            status_code=433,
                            message=message or _default_client_error_message(433),
                            details=data,
                        )

                    if 400 <= r.status <= 499:
                        message, data = await _read_error_payload(r)
                        logger.error("Client error (%d): %s", r.status, message)
                        raise MemoriApiClientError(
                            status_code=r.status,
                            message=message or _default_client_error_message(r.status),
                            details=data,
                        )

                    r.raise_for_status()
                    logger.debug("Augmentation request successful")
                    return await r.json()
            except aiohttp.ClientResponseError:
                raise
            except (ssl.SSLError, aiohttp.ClientSSLError) as e:
                logger.error("SSL/TLS error during augmentation request: %s", e)
                raise MemoriApiError(
                    "Memori API request failed due to an SSL/TLS certificate error. "
                    "This is often caused by corporate proxies/SSL inspection. "
                    "Try updating your CA certificates and try again."
                ) from e
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error("Network/timeout error during augmentation request: %s", e)
                raise MemoriApiError(
                    "Memori API request failed (network/timeout). "
                    "Check your connection and try again."
                ) from e

    def delete(self, route):
        logger.debug("DELETE request to %s", route)
        r = self.__session().delete(self.url(route), headers=self.headers())
        logger.debug("DELETE response - status: %d", r.status_code)

        r.raise_for_status()

        return r.json()

    def get(self, route):
        logger.debug("GET request to %s", route)
        r = self.__session().get(self.url(route), headers=self.headers())
        logger.debug("GET response - status: %d", r.status_code)

        r.raise_for_status()

        return r.json()

    async def get_async(self, route):
        return await self.__request_async("GET", route)

    def patch(self, route, json=None):
        logger.debug("PATCH request to %s", route)
        r = self.__session().patch(self.url(route), headers=self.headers(), json=json)
        logger.debug("PATCH response - status: %d", r.status_code)

        r.raise_for_status()

        return r.json()

    async def patch_async(self, route, json=None):
        return await self.__request_async("PATCH", route, json=json)

    def post(self, route, json=None):
        logger.debug("POST request to %s", route)
        r = self.__session().post(self.url(route), headers=self.headers(), json=json)
        logger.debug("POST response - status: %d", r.status_code)

        r.raise_for_status()

        return r.json()

    async def post_async(self, route, json=None):
        return await self.__request_async("POST", route, json=json)

    def headers(self):
        headers = {"X-Memori-API-Key": self.__x_api_key}

        api_key = os.environ.get("MEMORI_API_KEY")
        if api_key is not None:
            headers["Authorization"] = f"Bearer {api_key}"

        return headers

    def _is_anonymous(self):
        return os.environ.get("MEMORI_API_KEY") is None

    async def __request_async(self, method: str, route: str, json=None):
        url = self.url(route)
        headers = self.headers()
        attempts = 0
        max_retries = 5
        backoff_factor = 1
        print(url)

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method.upper(),
                        url,
                        headers=headers,
                        json=json,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as r:
                        logger.debug(
                            "Async %s response - status: %d, attempt: %d",
                            method.upper(),
                            r.status,
                            attempts + 1,
                        )
                        r.raise_for_status()
                        return await r.json()
            except aiohttp.ClientResponseError as e:
                if e.status < 500 or e.status > 599:
                    logger.error(
                        "Non-retryable error %d for %s %s",
                        e.status,
                        method.upper(),
                        url,
                    )
                    raise

                if attempts >= max_retries:
                    logger.error(
                        "Max retries (%d) exceeded for %s %s",
                        max_retries,
                        method.upper(),
                        url,
                    )
                    raise

                sleep = backoff_factor * (2**attempts)
                logger.debug(
                    "Retrying %s %s in %.1fs (attempt %d/%d) after status %d",
                    method.upper(),
                    url,
                    sleep,
                    attempts + 2,
                    max_retries,
                    e.status,
                )
                await asyncio.sleep(sleep)
                attempts += 1
            except Exception as e:
                if attempts >= max_retries:
                    logger.error(
                        "Max retries (%d) exceeded for %s %s: %s",
                        max_retries,
                        method.upper(),
                        url,
                        e,
                    )
                    raise

                sleep = backoff_factor * (2**attempts)
                logger.debug(
                    "Retrying %s %s in %.1fs (attempt %d/%d) after error: %s",
                    method.upper(),
                    url,
                    sleep,
                    attempts + 2,
                    max_retries,
                    e,
                )
                await asyncio.sleep(sleep)
                attempts += 1

    def __session(self):
        adapter = HTTPAdapter(
            max_retries=_ApiRetryRecoverable(
                allowed_methods=["GET", "PATCH", "POST", "PUT", "DELETE"],
                backoff_factor=1,
                raise_on_status=False,
                status=None,
                total=5,
            )
        )

        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def url(self, route):
        return f"{self.__base}/v1/{route}"


class _ApiRetryRecoverable(Retry):
    def is_retry(self, method, status_code, has_retry_after=False):
        return 500 <= status_code <= 599
