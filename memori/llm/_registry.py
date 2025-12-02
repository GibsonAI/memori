r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from collections.abc import Callable
from typing import Any

from memori.llm._base import BaseClient, BaseLlmAdaptor


class Registry:
    _clients: dict[Callable[[Any], bool], type[BaseClient]] = {}
    _adapters: dict[Callable[[str | None, str], bool], type[BaseLlmAdaptor]] = {}

    @classmethod
    def register_client(cls, matcher: Callable[[Any], bool]):
        def decorator(client_class: type[BaseClient]):
            cls._clients[matcher] = client_class
            return client_class

        return decorator

    @classmethod
    def register_adapter(cls, matcher: Callable[[str | None, str], bool]):
        def decorator(adapter_class: type[BaseLlmAdaptor]):
            cls._adapters[matcher] = adapter_class
            return adapter_class

        return decorator

    def client(self, client_obj: Any, config) -> BaseClient:
        for matcher, client_class in self._clients.items():
            if matcher(client_obj):
                return client_class(config)

        raise ValueError(f"No client registered for type: {type(client_obj).__name__}")

    def adapter(self, provider: str | None, title: str) -> BaseLlmAdaptor:
        for matcher, adapter_class in self._adapters.items():
            if matcher(provider, title):
                return adapter_class()

        raise RuntimeError("could not determine LLM for adapter")
