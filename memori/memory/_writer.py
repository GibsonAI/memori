r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                      memorilabs.ai
"""

import time

from sqlalchemy.exc import OperationalError

from memori._config import Config
from memori.llm._registry import Registry as LlmRegistry

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.1


class Writer:
    def __init__(self, config: Config):
        self.config = config

    def execute(self, payload: dict, max_retries: int = MAX_RETRIES) -> "Writer":
        if self.config.storage is None or self.config.storage.driver is None:
            return self

        for attempt in range(max_retries):
            try:
                self._execute_transaction(payload)
                return self
            except OperationalError as e:
                if "restart transaction" in str(e) and attempt < max_retries - 1:
                    if self.config.storage.adapter:
                        self.config.storage.adapter.rollback()
                    time.sleep(RETRY_BACKOFF_BASE * (2**attempt))
                    continue
                raise
        return self

    def _ensure_cached_id(self, cache_attr: str, create_func, *create_args) -> int:
        """Ensure an ID is cached, creating it if necessary."""
        cached_id = getattr(self.config.cache, cache_attr)
        if cached_id is None:
            cached_id = create_func(*create_args)
            if cached_id is None:
                raise RuntimeError(f"{cache_attr} is unexpectedly None")
            setattr(self.config.cache, cache_attr, cached_id)
        return cached_id

    def _execute_transaction(self, payload: dict) -> None:
        if self.config.entity_id is not None:
            self._ensure_cached_id(
                "entity_id",
                self.config.storage.driver.entity.create,
                self.config.entity_id,
            )

        if self.config.process_id is not None:
            self._ensure_cached_id(
                "process_id",
                self.config.storage.driver.process.create,
                self.config.process_id,
            )

        self._ensure_cached_id(
            "session_id",
            self.config.storage.driver.session.create,
            self.config.session_id,
            self.config.cache.entity_id,
            self.config.cache.process_id,
        )

        self._ensure_cached_id(
            "conversation_id",
            self.config.storage.driver.conversation.create,
            self.config.cache.session_id,
            self.config.session_timeout_minutes,
        )

        llm = LlmRegistry().adapter(
            payload["conversation"]["client"]["provider"],
            payload["conversation"]["client"]["title"],
        )

        messages = llm.get_formatted_query(payload)
        if messages:
            for message in messages:
                if message["role"] != "system":
                    self.config.storage.driver.conversation.message.create(
                        self.config.cache.conversation_id,
                        message["role"],
                        None,
                        message["content"],
                    )

        responses = llm.get_formatted_response(payload)
        if responses:
            for response in responses:
                self.config.storage.driver.conversation.message.create(
                    self.config.cache.conversation_id,
                    response["role"],
                    response["type"],
                    response["text"],
                )

        if self.config.storage is not None and self.config.storage.adapter is not None:
            self.config.storage.adapter.flush()
            self.config.storage.adapter.commit()
