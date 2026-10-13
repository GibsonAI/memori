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
from collections.abc import Mapping
from typing import Any, TypedDict, TypeGuard, cast

from memori._config import Config
from memori._logging import truncate
from memori._network import Api
from memori.embeddings import embed_texts
from memori.search import search_facts as search_facts_api
from memori.search._types import FactSearchResult

try:
    from sqlalchemy.exc import OperationalError

    _RETRYABLE_DB_ERRORS: tuple[type[Exception], ...] = (OperationalError,)
except ImportError:
    _RETRYABLE_DB_ERRORS = ()

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 0.05

RecallFact = FactSearchResult | Mapping[str, object] | str
CloudRecallSummary = dict[str, object]


class CloudRecallResponse(TypedDict, total=False):
    facts: list[RecallFact]
    messages: list[dict[str, str]]


def _is_str_object_mapping(value: object) -> TypeGuard[Mapping[str, object]]:
    if not isinstance(value, Mapping):
        return False
    return all(isinstance(k, str) for k in value.keys())


def _score_for_recall_threshold(fact: RecallFact) -> float:
    if isinstance(fact, str):
        return 1.0
    if _is_str_object_mapping(fact):
        raw = fact.get("rank_score")
        if raw is None:
            raw = fact.get("similarity", 0.0)
    else:
        raw = fact.rank_score
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    try:
        return float(cast(Any, raw))
    except (TypeError, ValueError):
        return 0.0


def _collect_cloud_summary_items(items: list[object]) -> list[CloudRecallSummary]:
    summaries: list[CloudRecallSummary] = []
    for item in items:
        if _is_str_object_mapping(item):
            summaries.append(dict(item))
    return summaries


def _normalize_cloud_fact(item: object) -> RecallFact | None:
    if isinstance(item, str):
        return item
    if not _is_str_object_mapping(item):
        return None

    fact = dict(item)
    summaries_raw = fact.get("summaries")
    if isinstance(summaries_raw, list):
        fact["summaries"] = _collect_cloud_summary_items(
            cast(list[object], summaries_raw)
        )
    return fact


def _attach_top_level_summaries_to_facts(
    facts: list[RecallFact], summaries: list[CloudRecallSummary]
) -> list[RecallFact]:
    if not summaries:
        return facts

    summaries_by_fact_id: dict[object, list[CloudRecallSummary]] = {}
    for summary in summaries:
        summary_fact_id = summary.get("entity_fact_id")
        if summary_fact_id is None:
            summary_fact_id = summary.get("fact_id")
        if summary_fact_id is None:
            continue
        summaries_by_fact_id.setdefault(summary_fact_id, []).append(summary)

    if not summaries_by_fact_id:
        return facts

    facts_with_summaries: list[RecallFact] = []
    for fact in facts:
        if not _is_str_object_mapping(fact):
            facts_with_summaries.append(fact)
            continue

        fact_id = fact.get("id")
        fact_dict = dict(fact)
        existing_summaries_raw = fact_dict.get("summaries")
        existing_summaries = (
            _collect_cloud_summary_items(cast(list[object], existing_summaries_raw))
            if isinstance(existing_summaries_raw, list)
            else []
        )
        matched_summaries = (
            summaries_by_fact_id.get(fact_id, []) if fact_id is not None else []
        )
        if existing_summaries or matched_summaries:
            fact_dict["summaries"] = [*existing_summaries, *matched_summaries]
        facts_with_summaries.append(fact_dict)

    return facts_with_summaries


def _collect_cloud_summaries_from_facts(
    facts: list[RecallFact],
) -> list[CloudRecallSummary]:
    summaries: list[CloudRecallSummary] = []
    seen: set[str] = set()

    def _content_key(summary: CloudRecallSummary) -> str | None:
        content = summary.get("content")
        if not isinstance(content, str) or not content.strip():
            return None
        return content.strip()

    for fact in facts:
        if _is_str_object_mapping(fact):
            summaries_raw = fact.get("summaries")
            if isinstance(summaries_raw, list):
                for summary in _collect_cloud_summary_items(
                    cast(list[object], summaries_raw)
                ):
                    key = _content_key(summary)
                    if key is None or key in seen:
                        continue
                    seen.add(key)
                    summaries.append(summary)
        elif hasattr(fact, "summaries"):
            summaries_raw = fact.summaries
            if isinstance(summaries_raw, list):
                for summary in _collect_cloud_summary_items(
                    cast(list[object], summaries_raw)
                ):
                    key = _content_key(summary)
                    if key is None or key in seen:
                        continue
                    seen.add(key)
                    summaries.append(summary)
    return summaries


class Recall:
    def __init__(self, config: Config) -> None:
        self.config = config

    def _resolve_entity_id(self, entity_id: int | None) -> int | None:
        if entity_id is not None:
            return entity_id

        if self.config.entity_id is None:
            logger.debug("Recall aborted - no entity_id configured")
            return None

        entity_id = self.config.storage.driver.entity.create(self.config.entity_id)
        logger.debug("Entity ID resolved: %s", entity_id)
        if entity_id is None:
            logger.debug("Recall aborted - entity_id is None after resolution")
        return entity_id

    def _resolve_limit(self, limit: int | None) -> int:
        return self.config.recall_facts_limit if limit is None else limit

    def delete_entity_memories(self, entity_external_id: str | None = None) -> None:
        if self.config.storage is None or self.config.storage.driver is None:
            logger.debug("Entity memory deletion aborted - storage not configured")
            return

        resolved_external_id = (
            entity_external_id
            if entity_external_id is not None
            else self.config.entity_id
        )
        if resolved_external_id is None:
            logger.debug("Entity memory deletion aborted - no entity_id configured")
            return

        entity_id = self.config.storage.driver.entity.create(resolved_external_id)
        if entity_id is None:
            logger.debug(
                "Entity memory deletion aborted - entity_id is None after resolution"
            )
            return

        self.config.storage.driver.knowledge_graph.delete_by_entity(entity_id)
        self.config.storage.driver.entity_fact.delete_by_entity(entity_id)

    def _embed_query(self, query: str) -> list[float]:
        logger.debug("Generating query embedding")
        embeddings_config = self.config.embeddings
        return embed_texts(
            query,
            model=embeddings_config.model,
        )[0]

    def _search_with_retries(
        self, *, entity_id: int, query: str, query_embedding: list[float], limit: int
    ) -> list[FactSearchResult]:
        facts: list[FactSearchResult] = []
        for attempt in range(MAX_RETRIES):
            try:
                logger.debug(
                    f"Executing search_facts - entity_id: {entity_id}, limit: {limit}, embeddings_limit: {self.config.recall_embeddings_limit}"
                )
                facts = search_facts_api(
                    self.config.storage.driver.entity_fact,
                    entity_id,
                    query_embedding,
                    limit,
                    self.config.recall_embeddings_limit,
                    query_text=query,
                )
                logger.debug("Recall complete - found %d facts", len(facts))
                break
            except _RETRYABLE_DB_ERRORS as e:
                if "restart transaction" in str(e) and attempt < MAX_RETRIES - 1:
                    logger.debug(
                        "Retry attempt %d due to OperationalError", attempt + 1
                    )
                    time.sleep(RETRY_BACKOFF_BASE * (2**attempt))
                    continue
                raise

        return facts

    def _search_with_retries_cloud(
        self, *, query: str, limit: int
    ) -> CloudRecallResponse:
        data = self._cloud_recall(query, limit=limit)
        return self._parse_cloud_recall_response(data)

    def _filter_cloud_recall_response(
        self, response: CloudRecallResponse
    ) -> CloudRecallResponse:
        relevant_facts = [
            fact
            for fact in response["facts"]
            if _score_for_recall_threshold(fact)
            >= self.config.recall_relevance_threshold
        ]
        filtered_response: CloudRecallResponse = {"facts": relevant_facts}

        if "messages" in response:
            filtered_response["messages"] = response["messages"]

        return filtered_response

    def _cloud_recall(self, query: str, *, limit: int | None = None) -> object:
        if self.config.entity_id is None:
            logger.debug("Cloud recall aborted - no entity_id configured")
            return []

        api = Api(self.config)
        resolved_limit = self._resolve_limit(limit)
        process = None
        if self.config.process_id is not None:
            process = {"id": self.config.process_id}
        payload = {
            "attribution": {
                "entity": {"id": str(self.config.entity_id)},
                "process": process,
            },
            "query": query,
            "session": {"id": str(self.config.session_id)},
            "limit": resolved_limit,
        }
        return api.post("cloud/recall", payload)

    @staticmethod
    def _parse_cloud_recall_response(
        data: object,
    ) -> CloudRecallResponse:
        def _collect_items(items: list[object]) -> list[RecallFact]:
            collected: list[RecallFact] = []
            for item in items:
                fact = _normalize_cloud_fact(item)
                if fact is not None:
                    collected.append(fact)
            return collected

        if isinstance(data, list):
            return {"facts": _collect_items(cast(list[object], data))}

        if not isinstance(data, dict):
            return {"facts": []}

        data_map = cast(Mapping[str, object], data)

        def _extract_list(*keys: str) -> list[object] | None:
            for k in keys:
                v = data_map.get(k)
                if isinstance(v, list):
                    return cast(list[object], v)
            return None

        facts_raw = _extract_list("facts", "results", "memories", "data") or []
        facts = _collect_items(facts_raw)
        summaries_raw = _extract_list("summaries")
        if summaries_raw is not None:
            facts = _attach_top_level_summaries_to_facts(
                facts, _collect_cloud_summary_items(summaries_raw)
            )

        response: CloudRecallResponse = {"facts": facts}

        messages_raw = _extract_list("messages", "conversation_messages", "history")
        if messages_raw is None:
            convo = data_map.get("conversation")
            if _is_str_object_mapping(convo):
                nested = convo.get("messages")
                if isinstance(nested, list):
                    messages_raw = cast(list[object], nested)

        messages: list[dict[str, str]] = []
        if messages_raw is not None:
            for msg in messages_raw:
                if not _is_str_object_mapping(msg):
                    continue
                role = msg.get("role")
                content = msg.get("content")
                if content is None:
                    content = msg.get("text")
                if not isinstance(role, str) or not isinstance(content, str):
                    continue
                messages.append({"role": role, "content": content})
            response["messages"] = messages

        return response

    def search_facts(
        self,
        query: str,
        limit: int | None = None,
        entity_id: int | None = None,
        cloud: bool = False,
    ) -> list[RecallFact] | CloudRecallResponse:
        logger.debug(
            "Recall started - query: %s (%d chars), limit: %s",
            truncate(query, 50),
            len(query),
            limit,
        )

        if self.config.cloud:
            if self.config.entity_id is None:
                logger.debug("Recall aborted - no entity_id configured")
                return {"facts": []}

            logger.debug(
                "Recall started - query: %s (%d chars), limit: %s, cloud: true",
                truncate(query, 50),
                len(query),
                limit,
            )
            resolved_limit = self._resolve_limit(limit)
            response = self._search_with_retries_cloud(
                query=query, limit=resolved_limit
            )
            return self._filter_cloud_recall_response(response)

        if self.config.storage is None or self.config.storage.driver is None:
            logger.debug("Recall aborted - storage not configured")
            return []

        entity_id = self._resolve_entity_id(entity_id)
        if entity_id is None:
            return []

        limit = self._resolve_limit(limit)
        query_embedding = self._embed_query(query)
        return cast(
            list[FactSearchResult | Mapping[str, object] | str],
            self._search_with_retries(
                entity_id=entity_id,
                query=query,
                query_embedding=query_embedding,
                limit=limit,
            ),
        )
