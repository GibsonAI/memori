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
import os

import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from memori._config import Config
from memori._exceptions import QuotaExceededError


class Api:
    def __init__(self, config: Config):
        self.__x_api_key = "c18b1022-7fe2-42af-ab01-b1f9139184f0"
        self.__base = os.environ.get("MEMORI_API_URL_BASE")
        if self.__base is None:
            self.__x_api_key = "96a7ea3e-11c2-428c-b9ae-5a168363dc80"
            self.__base = "https://api.memorilabs.ai"

        self.config = config

    async def augmentation_async(self, payload: dict) -> dict:
        url = self.url("sdk/augmentation")
        headers = self.headers()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as r:
                if r.status == 429:
                    if self._is_anonymous():
                        try:
                            quota_response = await r.json()
                            message = quota_response.get("message")
                        except Exception:
                            message = None

                        if message:
                            raise QuotaExceededError(message)
                        raise QuotaExceededError()
                    else:
                        return {}

                r.raise_for_status()
                return await r.json()

    def delete(self, route):
        r = self.__session().delete(self.url(route), headers=self.headers())

        r.raise_for_status()

        return r.json()

    def get(self, route):
        r = self.__session().get(self.url(route), headers=self.headers())

        r.raise_for_status()

        return r.json()

    async def get_async(self, route):
        return await self.__request_async("GET", route)

    def patch(self, route, json=None):
        r = self.__session().patch(self.url(route), headers=self.headers(), json=json)

        r.raise_for_status()

        return r.json()

    async def patch_async(self, route, json=None):
        return await self.__request_async("PATCH", route, json=json)

    def post(self, route, json=None):
        r = self.__session().post(self.url(route), headers=self.headers(), json=json)

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
                        r.raise_for_status()
                        return await r.json()
            except aiohttp.ClientResponseError as e:
                if e.status < 500 or e.status > 599:
                    raise

                if attempts >= max_retries:
                    raise

                sleep = backoff_factor * (2**attempts)
                await asyncio.sleep(sleep)
                attempts += 1
            except Exception:
                if attempts >= max_retries:
                    raise

                sleep = backoff_factor * (2**attempts)
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
