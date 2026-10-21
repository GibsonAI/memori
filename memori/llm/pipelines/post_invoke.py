import logging
import time
from typing import Any

from memori._logging import truncate
from memori.llm.helpers.serialization import (
    convert_to_json,
    format_kwargs,
    format_response,
    get_response_content,
)
from memori.memory.augmentation.augmentations.memori.models import (
    AttributionData,
    AugmentationInputData,
    ConversationMessage,
    EntityData,
    ProcessData,
    SessionData,
)

logger = logging.getLogger(__name__)


def format_payload(
    invoke,
    client_provider,
    client_title,
    client_version,
    start_time,
    end_time,
    query,
    response,
):
    response_json = convert_to_json(response)

    from memori.memory._conversation_messages import parse_payload_conversation_messages

    payload: dict[str, Any] = {
        "attribution": {
            "entity": {"id": invoke.config.entity_id},
            "process": {"id": invoke.config.process_id},
        },
        "conversation": {
            "client": {
                "provider": client_provider,
                "title": client_title,
                "version": client_version,
            },
            "query": query,
            "response": response_json,
        },
        "meta": {
            "api": {"key": invoke.config.api_key},
            "fnfg": {
                "exc": None,
                "status": "succeeded",
            },
            "sdk": {"client": "python", "version": invoke.config.version},
        },
        "session": {"uuid": str(invoke.config.session_id)},
        "time": {"end": end_time, "start": start_time},
    }

    messages = list(parse_payload_conversation_messages(payload))
    payload["messages"] = messages

    if invoke.config.cloud is True:
        return {
            "attribution": {
                "entity": {"id": invoke.config.entity_id},
                "process": {"id": invoke.config.process_id},
            },
            "messages": messages,
            "session": {"id": str(invoke.config.session_id)},
        }

    return payload


def format_augmentation_input(invoke, payload: dict) -> AugmentationInputData:
    return AugmentationInputData(
        attribution=AttributionData(
            entity=EntityData(id=invoke.config.entity_id),
            process=ProcessData(id=invoke.config.process_id),
        ),
        messages=[
            ConversationMessage(role=message.get("role"), content=message.get("text"))
            for message in payload.get("messages", [])
        ],
        session=SessionData(id=str(invoke.config.session_id)),
    )


def run_post_invoke(invoke, kwargs, payload):
    """Persist the completed turn and, when configured, run memory augmentation."""
    from memori.memory._manager import Manager as MemoryManager

    MemoryManager(invoke.config).execute(payload)
    if invoke.config.augmentation is not None:
        from memori.memory.augmentation._handler import handle_augmentation

        aug_input = format_augmentation_input(invoke, payload)

        handle_augmentation(
            config=invoke.config,
            payload=aug_input,
            kwargs=kwargs,
            augmentation_manager=invoke.config.augmentation,
            log_content=lambda c: logger.debug(
                "Response content: %s", truncate(str(c))
            ),
        )


def handle_post_response(invoke, kwargs, start_time, raw_response):
    if "model" in kwargs:
        invoke.config.llm.version = kwargs["model"]

    payload = format_payload(
        invoke,
        invoke.config.framework.provider,
        invoke.config.llm.provider,
        invoke.config.llm.version,
        start_time,
        time.time(),
        format_kwargs(
            kwargs,
            uses_protobuf=invoke._uses_protobuf,
            framework_provider=invoke.config.framework.provider,
            injected_count=invoke._injected_message_count,
        ),
        format_response(
            get_response_content(raw_response), uses_protobuf=invoke._uses_protobuf
        ),
    )

    conv_id = invoke.config.cache.conversation_id
    msg_count = len(
        payload.get("conversation", {}).get("query", {}).get("messages", [])
    )
    resp_count = len(
        payload.get("conversation", {}).get("response", {}).get("choices", [])
    )
    logger.debug(
        f"Ingesting conversation turn: conversation_id={conv_id}, "
        f"messages_count={msg_count}, responses_count={resp_count}"
    )

    run_post_invoke(invoke, kwargs, payload)
