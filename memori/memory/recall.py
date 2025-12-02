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
from memori._search import search_entity_facts
from memori.llm._embeddings import embed_texts

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.05


class Recall:
    def __init__(self, config: Config) -> None:
        self.config = config

    def search_facts(
        self, query: str, limit: int | None = None, entity_id: int | None = None
    ) -> list[dict]:
        if self.config.storage is None or self.config.storage.driver is None:
            return []

        if entity_id is None:
            if self.config.entity_id is None:
                return []
            entity_id = self.config.storage.driver.entity.create(self.config.entity_id)

        if entity_id is None:
            return []

        if limit is None:
            limit = self.config.recall_facts_limit

        query_embedding = embed_texts(query)[0]

        facts = []
        for attempt in range(MAX_RETRIES):
            try:
                facts = search_entity_facts(
                    self.config.storage.driver.entity_fact,
                    entity_id,
                    query_embedding,
                    limit,
                    self.config.recall_embeddings_limit,
                )
                break
            except OperationalError as e:
                if "restart transaction" in str(e) and attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF_BASE * (2**attempt))
                    continue
                raise

        return facts
