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
import json
import time

from google.protobuf import json_format

from memori.llm._constants import XAI_LLM_PROVIDER


class XAiWrappers:
    """
    Handles XAI-specific wrapping logic for the two-step API pattern.

    XAI's API works differently than other providers:
    1. create() returns a Chat object (no API call yet)
    2. Chat.sample() or Chat.stream() makes the actual API call

    This class encapsulates all the custom wrapping logic needed to handle
    conversation injection, timing, and payload creation for XAI.
    """

    def __init__(self, config):
        self.config = config

    def inject_conversation_history(self, kwargs):
        """Inject conversation history into messages using XAI message format."""
        from xai_sdk.chat import assistant, user

        if self.config.cache.conversation_id is None:
            return kwargs

        messages = self.config.storage.driver.conversation.messages.read(
            self.config.cache.conversation_id
        )
        if len(messages) == 0:
            return kwargs

        xai_messages = []
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")
            if role == "user":
                xai_messages.append(user(content))
            elif role == "assistant":
                xai_messages.append(assistant(content))

        kwargs["messages"] = xai_messages + kwargs.get("messages", [])

        return kwargs

    def wrap_chat_methods(self, chat_obj, client_version):
        """Wrap the Chat object's sample() and stream() methods."""
        if hasattr(chat_obj, "_memori_installed"):
            return

        chat_obj._sample = chat_obj.sample
        is_async = asyncio.iscoroutinefunction(chat_obj._sample)

        if is_async:
            chat_obj.sample = self._create_async_sample_wrapper(
                chat_obj, client_version
            )
        else:
            chat_obj.sample = self._create_sync_sample_wrapper(chat_obj, client_version)

        if hasattr(chat_obj, "stream"):
            chat_obj._stream = chat_obj.stream
            chat_obj.stream = self._create_stream_wrapper(chat_obj, client_version)

        chat_obj._memori_installed = True

    def _create_sync_sample_wrapper(self, chat_obj, client_version):
        """Create a synchronous wrapper for sample()."""
        from memori.memory._manager import Manager as MemoryManager

        def wrapped_sample(*sample_args, **sample_kwargs):
            start = time.time()
            response = chat_obj._sample(*sample_args, **sample_kwargs)

            query_formatted = {
                "messages": [
                    json.loads(json_format.MessageToJson(msg))
                    for msg in chat_obj.messages
                ]
            }
            response_json = {
                "content": response.content,
                "role": self._normalize_role(response),
            }

            payload = self._build_payload(
                query_formatted, response_json, client_version, start
            )
            MemoryManager(self.config).execute(payload)

            if self.config.augmentation is not None:
                from memori.memory.augmentation.input import AugmentationInput

                messages = payload["conversation"]["query"].get("messages", [])
                messages_for_aug = list(messages) if isinstance(messages, list) else []
                messages_for_aug.append(
                    {"role": "assistant", "content": response.content}
                )

                if self.config.entity_id or self.config.process_id:
                    augmentation_input = AugmentationInput(
                        conversation_id=self.config.cache.conversation_id,
                        entity_id=self.config.entity_id,
                        process_id=self.config.process_id,
                        conversation_messages=messages_for_aug,
                        system_prompt=None,
                    )
                    self.config.augmentation.enqueue(augmentation_input)

            return response

        return wrapped_sample

    def _create_async_sample_wrapper(self, chat_obj, client_version):
        """Create an asynchronous wrapper for sample()."""
        from memori.memory._manager import Manager as MemoryManager

        async def wrapped_sample_async(*sample_args, **sample_kwargs):
            start = time.time()
            response = await chat_obj._sample(*sample_args, **sample_kwargs)

            query_formatted = {
                "messages": [
                    json.loads(json_format.MessageToJson(msg))
                    for msg in chat_obj.messages
                ]
            }
            response_json = {
                "content": response.content,
                "role": self._normalize_role(response),
            }

            payload = self._build_payload(
                query_formatted, response_json, client_version, start
            )
            MemoryManager(self.config).execute(payload)

            if self.config.augmentation is not None:
                from memori.memory.augmentation.input import AugmentationInput

                messages = payload["conversation"]["query"].get("messages", [])
                messages_for_aug = list(messages) if isinstance(messages, list) else []
                messages_for_aug.append(
                    {"role": "assistant", "content": response.content}
                )

                if self.config.entity_id or self.config.process_id:
                    augmentation_input = AugmentationInput(
                        conversation_id=self.config.cache.conversation_id,
                        entity_id=self.config.entity_id,
                        process_id=self.config.process_id,
                        conversation_messages=messages_for_aug,
                        system_prompt=None,
                    )
                    self.config.augmentation.enqueue(augmentation_input)

            return response

        return wrapped_sample_async

    def _create_stream_wrapper(self, chat_obj, client_version):
        """Create an asynchronous wrapper for stream()."""
        from memori.memory._manager import Manager as MemoryManager

        async def wrapped_stream(*stream_args, **stream_kwargs):
            start = time.time()
            full_content = []
            last_response = None

            async for item in chat_obj._stream(*stream_args, **stream_kwargs):
                if isinstance(item, tuple) and len(item) == 2:
                    response, delta = item
                    last_response = response
                    if hasattr(delta, "content") and delta.content:
                        full_content.append(delta.content)
                elif hasattr(item, "content") and item.content:
                    full_content.append(item.content)
                    last_response = item

                yield item

            if full_content and last_response:
                query_formatted = {
                    "messages": [
                        json.loads(json_format.MessageToJson(msg))
                        for msg in chat_obj.messages
                    ]
                }
                response_json = {
                    "content": "".join(full_content),
                    "role": self._normalize_role(last_response)
                    if hasattr(last_response, "role")
                    else "assistant",
                }

                payload = self._build_payload(
                    query_formatted, response_json, client_version, start
                )
                MemoryManager(self.config).execute(payload)

                if self.config.augmentation is not None:
                    from memori.memory.augmentation.input import AugmentationInput

                    messages = payload["conversation"]["query"].get("messages", [])
                    messages_for_aug = (
                        list(messages) if isinstance(messages, list) else []
                    )
                    messages_for_aug.append(
                        {"role": "assistant", "content": "".join(full_content)}
                    )

                    if self.config.entity_id or self.config.process_id:
                        augmentation_input = AugmentationInput(
                            conversation_id=self.config.cache.conversation_id,
                            entity_id=self.config.entity_id,
                            process_id=self.config.process_id,
                            conversation_messages=messages_for_aug,
                            system_prompt=None,
                        )
                        self.config.augmentation.enqueue(augmentation_input)

        return wrapped_stream

    def _build_payload(
        self, query_formatted, response_json, client_version, start_time
    ):
        """Build the payload for memory storage."""
        return {
            "attribution": {
                "entity": {"id": self.config.entity_id},
                "process": {"id": self.config.process_id},
            },
            "conversation": {
                "client": {
                    "provider": self.config.framework.provider,
                    "title": self.config.llm.provider or XAI_LLM_PROVIDER,
                    "version": client_version,
                },
                "query": query_formatted,
                "response": response_json,
            },
            "meta": {
                "api": {"key": self.config.api_key},
                "fnfg": {"exc": None, "status": "succeeded"},
                "sdk": {"client": "python", "version": self.config.version},
            },
            "session": {"uuid": str(self.config.session_id)},
            "time": {"end": time.time(), "start": start_time},
        }

    def _normalize_role(self, response):
        """Normalize protobuf role names to standard format."""
        role_str = (
            response.role.name if hasattr(response.role, "name") else str(response.role)
        )

        role_map = {
            "ROLE_ASSISTANT": "assistant",
            "ROLE_USER": "user",
            "ROLE_SYSTEM": "system",
        }

        return role_map.get(role_str, role_str.lower().replace("role_", ""))
