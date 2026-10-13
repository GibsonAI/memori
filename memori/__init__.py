r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

import os
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from memori._config import Config
from memori._exceptions import (
    MissingMemoriApiKeyError,
    MissingPsycopgError,
    QuotaExceededError,
    UnsupportedLLMProviderError,
    warn_if_legacy_memorisdk_installed,
)
from memori.agent import Agent as AgentClient
from memori.llm._providers import Agno as LlmProviderAgno
from memori.llm._providers import Anthropic as LlmProviderAnthropic
from memori.llm._providers import Google as LlmProviderGoogle
from memori.llm._providers import LangChain as LlmProviderLangChain
from memori.llm._providers import OpenAi as LlmProviderOpenAi
from memori.llm._providers import PydanticAi as LlmProviderPydanticAi
from memori.llm._providers import XAi as LlmProviderXAi
from memori.memory.augmentation import Manager as AugmentationManager
from memori.memory.recall import CloudRecallResponse, Recall, RecallFact
from memori.native import RustCoreAdapter
from memori.storage import Manager as StorageManager

__all__ = [
    "Memori",
    "QuotaExceededError",
    "UnsupportedLLMProviderError",
]

warn_if_legacy_memorisdk_installed()


def embed_texts(*args: Any, **kwargs: Any) -> Any:
    from memori.embeddings import embed_texts as embed_texts_impl

    return embed_texts_impl(*args, **kwargs)


class LlmRegistry:
    """Entry point for registering supported LLM clients and framework models."""

    def __init__(self, memori: "Memori") -> None:
        self.memori = memori

    def register(
        self,
        client: Any | None = None,
        openai_chat: Any | None = None,
        claude: Any | None = None,
        gemini: Any | None = None,
        xai: Any | None = None,
        chatbedrock: Any | None = None,
        chatgooglegenai: Any | None = None,
        chatopenai: Any | None = None,
        chatvertexai: Any | None = None,
    ) -> "Memori":
        """Register an LLM client/model and return the parent `Memori` instance.

        This supports direct clients (`client=...`) and framework-specific named
        model arguments (Agno/LangChain), but they cannot be mixed in one call.
        """
        from memori.llm._registry import register_llm

        return register_llm(
            self.memori,
            client=client,
            openai_chat=openai_chat,
            claude=claude,
            gemini=gemini,
            xai=xai,
            chatbedrock=chatbedrock,
            chatgooglegenai=chatgooglegenai,
            chatopenai=chatopenai,
            chatvertexai=chatvertexai,
        )


class Memori:
    """Primary SDK entry point for memory collection and recall operations."""

    @classmethod
    def provision(
        cls,
        *,
        provider: str,
        build: bool = True,
        cache: bool = True,
        tag: str = "memori",
        cache_key: str | None = None,
        **kwargs: Any,
    ) -> "Memori":
        """Provision a BYODB database and return a ready `Memori` instance."""
        from memori.provisioning import provision_memori

        return provision_memori(
            provider=provider,
            build=build,
            cache=cache,
            tag=tag,
            cache_key=cache_key,
            **kwargs,
        )

    def __init__(
        self,
        conn: Callable[[], Any] | Any | None = None,
        debug_truncate: bool = True,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        use_rust_core: bool | None = None,
    ) -> None:
        """Initialize Memori with cloud mode or a user-provided connection.

        Args:
            conn: Database connection factory or managed connection instance.
            debug_truncate: When True, truncate long content in debug logging.
            api_key: Optional Memori Cloud API key. Defaults to `MEMORI_API_KEY`.
            base_url: Optional Memori Cloud API base URL. Defaults to `MEMORI_API_URL_BASE`.
            use_rust_core: When not None, overrides env for BYODB Rust engine use.
        """
        from memori._logging import set_truncate_enabled

        self.config = Config()
        self.config.api_key = api_key or os.environ.get("MEMORI_API_KEY", None)
        if base_url is not None:
            self.config.api_url_base = base_url
        self.config.session_id = uuid4()
        self.config.debug_truncate = debug_truncate
        set_truncate_enabled(debug_truncate)

        if conn is None:
            conn = self._get_default_connection()
        else:
            self.config.cloud = False
            self.config.byodb = True

        if use_rust_core is not None:
            self.config.use_rust_core = use_rust_core

        self.config.storage = StorageManager(self.config).start(conn)
        self.config.augmentation = AugmentationManager(self.config).start(conn)
        self.config.rust_core = RustCoreAdapter.maybe_create(self.config)

        self.agent = AgentClient(self.config)
        self.augmentation = self.config.augmentation
        self.llm = LlmRegistry(self)
        self.agno = LlmProviderAgno(self)
        self.anthropic = LlmProviderAnthropic(self)
        self.google = LlmProviderGoogle(self)
        self.langchain = LlmProviderLangChain(self)
        self.openai = LlmProviderOpenAi(self)
        self.pydantic_ai = LlmProviderPydanticAi(self)
        self.xai = LlmProviderXAi(self)

    def _get_default_connection(self) -> Callable[[], Any] | None:
        connection_string = os.environ.get("MEMORI_COCKROACHDB_CONNECTION_STRING", None)
        if connection_string:
            try:
                import psycopg
            except ImportError as e:
                raise MissingPsycopgError("CockroachDB") from e

            self.config.cloud = False
            self.config.byodb = False
            return lambda: psycopg.connect(connection_string)

        self.config.cloud = True
        self.config.byodb = False
        api_key = self.config.api_key
        if api_key is None or api_key == "":
            raise MissingMemoriApiKeyError()
        return None

    def attribution(
        self,
        entity_id: str,
        process_id: str | None = None,
    ) -> "Memori":
        """Set attribution identifiers used when persisting and recalling memory."""
        if not isinstance(entity_id, str):
            raise TypeError("entity_id must be a string")

        if not entity_id:
            raise ValueError("entity_id cannot be empty")

        if len(entity_id) > 100:
            raise RuntimeError("entity_id cannot be greater than 100 characters")

        if process_id is not None and not isinstance(process_id, str):
            raise TypeError("process_id must be a string or None")

        if process_id is not None and not process_id:
            raise ValueError("process_id cannot be empty")

        if process_id is not None and len(process_id) > 100:
            raise RuntimeError("process_id cannot be greater than 100 characters")

        self.config.entity_id = entity_id
        self.config.process_id = process_id

        return self

    def new_session(self) -> "Memori":
        """Start a new session and clear in-memory caches for this instance."""
        self.config.session_id = uuid4()
        self.config.reset_cache()
        return self

    def set_session(self, session_id: Any) -> "Memori":
        """Set an explicit session identifier on the current instance."""
        self.config.session_id = session_id
        return self

    def recall(
        self, query: str, limit: int | None = None
    ) -> list[RecallFact] | CloudRecallResponse:
        """Return relevant memories for a query."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not query.strip():
            raise ValueError("query cannot be empty")
        if limit is not None:
            if not isinstance(limit, int):
                raise TypeError("limit must be an integer or None")
            if limit <= 0:
                raise ValueError("limit must be greater than 0")

        if self.config.cloud is False and self.config.rust_core is not None:
            resolved_limit = self.config.recall_facts_limit if limit is None else limit
            if not self.config.entity_id:
                return []
            return self.config.rust_core.retrieve_facts(
                query=query,
                entity_id=str(self.config.entity_id),
                limit=resolved_limit,
                dense_limit=self.config.recall_embeddings_limit,
            )
        return Recall(self.config).search_facts(query, limit)

    def delete_entity_memories(self, entity_id: str | None = None) -> None:
        """Delete memory records for an entity while preserving conversations."""
        if not self.config.byodb:
            raise RuntimeError("delete_entity_memories is only available in BYODB mode")

        if entity_id is not None and not isinstance(entity_id, str):
            raise TypeError("entity_id must be a string or None")
        if entity_id is not None and not entity_id:
            raise ValueError("entity_id cannot be empty")
        if entity_id is not None and len(entity_id) > 100:
            raise RuntimeError("entity_id cannot be greater than 100 characters")

        Recall(self.config).delete_entity_memories(entity_id)

    def agent_recall(
        self,
        *,
        query: str | None = None,
        date_start: str | None = None,
        date_end: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
        signal: str | None = None,
        source: str | None = None,
    ) -> dict[str, Any]:
        """Fetch memories from the Memori Cloud agent recall endpoint."""
        return self.agent.recall(
            query=query,
            date_start=date_start,
            date_end=date_end,
            project_id=project_id,
            session_id=session_id,
            signal=signal,
            source=source,
        )

    def agent_recall_summary(
        self,
        *,
        date_start: str | None = None,
        date_end: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch summaries from the Memori Cloud agent recall summary endpoint."""
        return self.agent.recall_summary(
            date_start=date_start,
            date_end=date_end,
            project_id=project_id,
            session_id=session_id,
        )

    def agent_compaction(
        self,
        *,
        project_id: str | None = None,
        session_id: str | None = None,
        num_messages: int | None = None,
    ) -> dict[str, Any]:
        """Fetch a structured compaction from the Memori Cloud agent endpoint."""
        return self.agent.compaction(
            project_id=project_id,
            session_id=session_id,
            num_messages=num_messages,
        )

    def capture_agent_turn(
        self,
        *,
        user_content: str,
        assistant_content: str,
        project_id: str,
        session_id: str | None = None,
        platform: str = "python",
        trace: dict[str, Any] | None = None,
        summary: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        provider_sdk_version: str | None = None,
    ) -> None:
        """Capture an agent conversation turn for persistence and augmentation."""
        self.agent.capture_turn(
            user_content=user_content,
            assistant_content=assistant_content,
            project_id=project_id,
            session_id=session_id,
            platform=platform,
            trace=trace,
            summary=summary,
            provider=provider,
            model=model,
            provider_sdk_version=provider_sdk_version,
        )

    def agent_feedback(self, content: str) -> None:
        """Send agent integration feedback to Memori Cloud."""
        self.agent.feedback(content)

    def close(self) -> None:
        """Close the underlying storage connection/session, if any.

        This is especially important for long-running processes (e.g. web servers)
        where you want to explicitly release database connections.
        """
        storage = getattr(self.config, "storage", None)
        adapter = getattr(storage, "adapter", None) if storage is not None else None
        if adapter is None:
            return
        try:
            adapter.close()
        except Exception:  # nosec B110
            pass

    def __enter__(self) -> "Memori":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def embed_texts(self, texts: str | list[str], *, async_: bool = False) -> Any:
        """Generate embedding vectors for one or many input strings."""
        embeddings_cfg = self.config.embeddings
        return embed_texts(
            texts,
            model=embeddings_cfg.model,
            async_=async_,
        )
