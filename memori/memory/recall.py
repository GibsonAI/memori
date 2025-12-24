r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""

import logging
import time

from sqlalchemy.exc import OperationalError

from memori._config import Config
from memori._logging import truncate
from memori._search import search_entity_facts
from memori.llm._embeddings import embed_texts

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.05


class Recall:
    def __init__(self, config: Config) -> None:
        self.config = config

    def search_facts(
        self, query: str, limit: int | None = None, entity_id: int | None = None
    ) -> list[dict]:
        logger.debug(
            "Recall started - query: %s (%d chars), limit: %s",
            truncate(query, 50),
            len(query),
            limit,
        )

        if self.config.storage is None or self.config.storage.driver is None:
            logger.debug("Recall aborted - storage not configured")
            return []

        if entity_id is None:
            if self.config.entity_id is None:
                logger.debug("Recall aborted - no entity_id configured")
                return []
            entity_id = self.config.storage.driver.entity.create(self.config.entity_id)
            logger.debug("Entity ID resolved: %s", entity_id)

        if entity_id is None:
            logger.debug("Recall aborted - entity_id is None after resolution")
            return []

        if limit is None:
            limit = self.config.recall_facts_limit

        logger.debug("Generating query embedding")
        embeddings_config = self.config.embeddings
        query_embedding = embed_texts(
            query,
            model=embeddings_config.model,
            fallback_dimension=embeddings_config.fallback_dimension,
        )[0]

        facts = []
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(
                    "Executing search_entity_facts - entity_id: %s, limit: %s, embeddings_limit: %s",
                    entity_id,
                    limit,
                    self.config.recall_embeddings_limit,
                )
                facts = search_entity_facts(
                    self.config.storage.driver.entity_fact,
                    entity_id,
                    query_embedding,
                    limit,
                    self.config.recall_embeddings_limit,
                )
                logger.debug("Recall complete - found %d facts", len(facts))
                break
            except OperationalError as e:
                if "restart transaction" in str(e) and attempt < MAX_RETRIES - 1:
                    logger.debug(
                        "Retry attempt %d due to OperationalError", attempt + 1
                    )
                    time.sleep(RETRY_BACKOFF_BASE * (2**attempt))
                    continue
                raise

        return facts
