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

from memori._network import Api
from memori.llm._embeddings import embed_texts_async
from memori.memory._struct import Memories
from memori.memory.augmentation._base import AugmentationContext, BaseAugmentation
from memori.memory.augmentation._models import (
    AttributionData,
    AugmentationPayload,
    ConversationData,
    EntityData,
    FrameworkData,
    LlmData,
    MetaData,
    ModelData,
    PlatformData,
    ProcessData,
    SdkData,
    SdkVersionData,
    StorageData,
    hash_id,
)
from memori.memory.augmentation._registry import Registry

logger = logging.getLogger(__name__)


@Registry.register("advanced_augmentation")
class AdvancedAugmentation(BaseAugmentation):
    def __init__(self, config=None, enabled: bool = True):
        super().__init__(config=config, enabled=enabled)

    def _get_conversation_summary(self, driver, conversation_id: str) -> str:
        try:
            conversation = driver.conversation.read(conversation_id)
            if conversation and conversation.get("summary"):
                return conversation["summary"]
        except Exception:
            pass
        return ""

    def _build_api_payload(
        self,
        messages: list,
        summary: str,
        system_prompt: str | None,
        dialect: str,
        entity_id: str | None,
        process_id: str | None,
    ) -> dict:
        """Build API payload using structured dataclasses."""
        conversation = ConversationData(
            messages=messages,
            summary=summary if summary else None,
        )

        meta = MetaData(
            attribution=AttributionData(
                entity=EntityData(id=hash_id(entity_id)),
                process=ProcessData(id=hash_id(process_id)),
            ),
            framework=FrameworkData(provider=self.config.framework.provider),
            llm=LlmData(
                model=ModelData(
                    provider=self.config.llm.provider,
                    sdk=SdkVersionData(version=self.config.llm.provider_sdk_version),
                    version=self.config.llm.version,
                )
            ),
            platform=PlatformData(provider=self.config.platform.provider),
            sdk=SdkData(lang="python", version=self.config.version),
            storage=StorageData(
                cockroachdb=self.config.storage_config.cockroachdb,
                dialect=dialect,
            ),
        )

        payload = AugmentationPayload(conversation=conversation, meta=meta)
        return payload.to_dict()

    async def process(self, ctx: AugmentationContext, driver) -> AugmentationContext:
        if not ctx.payload.entity_id:
            return ctx
        if not self.config:
            return ctx
        if not ctx.payload.conversation_id:
            return ctx

        api = Api(self.config)
        dialect = driver.conversation.conn.get_dialect()
        summary = self._get_conversation_summary(driver, ctx.payload.conversation_id)

        payload = self._build_api_payload(
            ctx.payload.conversation_messages,
            summary,
            ctx.payload.system_prompt,
            dialect,
            ctx.payload.entity_id,
            ctx.payload.process_id,
        )

        logger.debug("AA submitting payload to API")
        try:
            api_response = await api.augmentation_async(payload)
        except Exception as e:
            from memori._exceptions import QuotaExceededError

            if isinstance(e, QuotaExceededError):
                raise
            logger.debug("AA API call failed: %s", type(e).__name__)
            return ctx

        if not api_response:
            logger.debug("AA API returned empty response")
            return ctx

        memories = await self._process_api_response(api_response)

        ctx.data["memories"] = memories

        await self._schedule_entity_writes(ctx, driver, memories)
        self._schedule_process_writes(ctx, driver, memories)
        self._schedule_conversation_writes(ctx, memories)

        return ctx

    async def _process_api_response(self, api_response: dict) -> Memories:
        entity_data = api_response.get("entity", {})
        facts = entity_data.get("facts", [])
        triples = entity_data.get("triples", [])

        if not facts and triples:
            facts = [
                f"{t['subject']['name']} {t['predicate']} {t['object']['name']}"
                for t in triples
                if t.get("subject") and t.get("predicate") and t.get("object")
            ]

        if facts:
            embeddings_config = self.config.embeddings
            fact_embeddings = await embed_texts_async(
                facts,
                model=embeddings_config.model,
                fallback_dimension=embeddings_config.fallback_dimension,
            )
            api_response["entity"]["fact_embeddings"] = fact_embeddings

        return Memories().configure_from_advanced_augmentation(api_response)

    async def _schedule_entity_writes(
        self, ctx: AugmentationContext, driver, memories: Memories
    ):
        if not ctx.payload.entity_id:
            return

        entity_id = driver.entity.create(ctx.payload.entity_id)
        if not entity_id:
            return

        facts_to_write = memories.entity.facts
        embeddings_to_write = memories.entity.fact_embeddings

        if memories.entity.semantic_triples and (
            not facts_to_write or not embeddings_to_write
        ):
            facts_from_triples = [
                f"{triple.subject_name} {triple.predicate} {triple.object_name}"
                for triple in memories.entity.semantic_triples
            ]

            if facts_from_triples:
                embeddings_config = self.config.embeddings
                embeddings_from_triples = await embed_texts_async(
                    facts_from_triples,
                    model=embeddings_config.model,
                    fallback_dimension=embeddings_config.fallback_dimension,
                )
                facts_to_write = (facts_to_write or []) + facts_from_triples
                embeddings_to_write = (
                    embeddings_to_write or []
                ) + embeddings_from_triples

        if facts_to_write and embeddings_to_write:
            ctx.add_write(
                "entity_fact.create",
                entity_id,
                facts_to_write,
                embeddings_to_write,
            )

        if memories.entity.semantic_triples:
            ctx.add_write(
                "knowledge_graph.create",
                entity_id,
                memories.entity.semantic_triples,
            )

    def _schedule_process_writes(
        self, ctx: AugmentationContext, driver, memories: Memories
    ):
        if not ctx.payload.process_id:
            return

        process_id = driver.process.create(ctx.payload.process_id)
        if process_id and memories.process.attributes:
            ctx.add_write(
                "process_attribute.create", process_id, memories.process.attributes
            )

    def _schedule_conversation_writes(
        self, ctx: AugmentationContext, memories: Memories
    ):
        if not ctx.payload.conversation_id:
            return

        if memories.conversation.summary:
            ctx.add_write(
                "conversation.update",
                ctx.payload.conversation_id,
                memories.conversation.summary,
            )
