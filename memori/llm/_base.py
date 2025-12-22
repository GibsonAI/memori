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
import copy
import json
import logging
from typing import TYPE_CHECKING

from google.protobuf import json_format

from memori._config import Config
from memori._logging import truncate
from memori._utils import merge_chunk

if TYPE_CHECKING:
    pass
from memori.llm._utils import (
    agno_is_anthropic,
    agno_is_google,
    agno_is_openai,
    agno_is_xai,
    llm_is_anthropic,
    llm_is_bedrock,
    llm_is_google,
    llm_is_openai,
    llm_is_xai,
    provider_is_langchain,
)

logger = logging.getLogger(__name__)


class BaseClient:
    def __init__(self, config: Config):
        self.config = config
        self.stream = False

    def register(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement register()")

    def _wrap_method(
        self,
        obj,
        method_name,
        backup_obj,
        backup_attr,
        provider,
        llm_provider,
        version,
        stream=False,
    ):
        """Helper to wrap a method with the appropriate Invoke wrapper.

        Automatically detects async context and chooses the correct wrapper class.

        Args:
            obj: The object containing the method to wrap (e.g., client.chat.completions)
            method_name: Name of the method to wrap (e.g., 'create')
            backup_obj: The object where backup is stored (e.g., client.chat)
            backup_attr: Name of backup attribute where original is stored (e.g., '_completions_create')
            provider: Framework provider name
            llm_provider: LLM provider name
            version: Provider SDK version
            stream: Whether to use streaming wrappers
        """
        from memori.llm._invoke import (
            Invoke,
            InvokeAsync,
            InvokeAsyncStream,
            InvokeStream,
        )

        original = getattr(backup_obj, backup_attr)

        try:
            asyncio.get_running_loop()
            wrapper_class = InvokeAsyncStream if stream else InvokeAsync
        except RuntimeError:
            wrapper_class = InvokeStream if stream else Invoke

        setattr(
            obj,
            method_name,
            wrapper_class(self.config, original)
            .set_client(provider, llm_provider, version)
            .invoke,
        )


class BaseInvoke:
    def __init__(self, config: Config, method):
        self.config = config
        self._method = method
        self._uses_protobuf = False
        self._injected_message_count = 0

    def configure_for_streaming_usage(self, kwargs: dict) -> dict:
        if (
            llm_is_openai(self.config.framework.provider, self.config.llm.provider)
            or llm_is_xai(self.config.framework.provider, self.config.llm.provider)
            or agno_is_openai(self.config.framework.provider, self.config.llm.provider)
        ):
            if kwargs.get("stream", None):
                stream_options = kwargs.get("stream_options", None)
                if stream_options is None or not isinstance(stream_options, dict):
                    kwargs["stream_options"] = {}

                kwargs["stream_options"]["include_usage"] = True

        return kwargs

    def _convert_to_json(self, obj):
        """Recursively convert objects to JSON-serializable format."""
        if isinstance(obj, list):
            return [self._convert_to_json(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._convert_to_json(value) for key, value in obj.items()}
        elif hasattr(obj, "__dict__"):
            return self._convert_to_json(obj.__dict__)
        else:
            return obj

    def dict_to_json(self, dict_: dict) -> dict:
        return self._convert_to_json(dict_)

    def _format_kwargs(self, kwargs):
        if self._uses_protobuf:
            if "request" in kwargs:
                formatted_kwargs = json.loads(
                    json_format.MessageToJson(kwargs["request"].__dict__["_pb"])
                )
            else:
                formatted_kwargs = copy.deepcopy(kwargs)
                formatted_kwargs = self.dict_to_json(formatted_kwargs)
        else:
            formatted_kwargs = copy.deepcopy(kwargs)
            if provider_is_langchain(self.config.framework.provider):
                if "response_format" in formatted_kwargs and isinstance(
                    formatted_kwargs["response_format"], object
                ):
                    """
                    We are likely processing the result of LangChain's structured
                    output runnable. The object defined in "response_format" is
                    recursive (it refers to itself) so formatting it into a dictionary
                    will result in an RecursionError. We also do not need the data in
                    this object so we are going to discard it here.
                    """

                    del formatted_kwargs["response_format"]

            formatted_kwargs = self.dict_to_json(formatted_kwargs)

        if self._injected_message_count > 0:
            formatted_kwargs["_memori_injected_count"] = self._injected_message_count

        return formatted_kwargs

    def _format_payload(
        self,
        client_provider,
        client_title,
        client_version,
        start_time,
        end_time,
        query,
        response,
    ):
        response_json = self.response_to_json(response)

        payload = {
            "attribution": {
                "entity": {"id": self.config.entity_id},
                "process": {"id": self.config.process_id},
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
                "api": {"key": self.config.api_key},
                "fnfg": {
                    "exc": None,
                    "status": "succeeded",
                },
                "sdk": {"client": "python", "version": self.config.version},
            },
            "session": {"uuid": str(self.config.session_id)},
            "time": {"end": end_time, "start": start_time},
        }

        return payload

    def _format_response(self, raw_response):
        formatted_response = copy.deepcopy(raw_response)
        if self._uses_protobuf:
            if not isinstance(formatted_response, list):
                if (
                    hasattr(formatted_response, "__dict__")
                    and "_pb" in formatted_response.__dict__
                ):
                    formatted_response = json.loads(
                        json_format.MessageToJson(formatted_response.__dict__["_pb"])
                    )
                else:
                    formatted_response = {}

        return formatted_response

    def get_response_content(self, raw_response):
        if (
            raw_response.__class__.__name__ == "LegacyAPIResponse"
            and raw_response.__class__.__module__ == "openai._legacy_response"
        ):
            """
            Library: langchain-openai
            Version: > 0.3.31

            Calling the chat / invoke method of the client no longer returns the JSON
            response but instead an object that looks like an API response. This
            object does not inherit from a base class we can reliably identify and
            we do not want to force the OpenAI library as a dependency.
            """

            return json.loads(raw_response.text)

        return raw_response

    def _extract_text_from_parts(self, parts: list) -> str:
        """Extract text from a list of parts (Google format)."""
        text_parts = []
        for part in parts:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif hasattr(part, "text") and part.text:
                text_parts.append(part.text)
        return " ".join(text_parts) if text_parts else ""

    def _extract_from_contents(self, contents) -> str:
        """Extract user query from Google's contents format."""
        if isinstance(contents, str):
            return contents

        if isinstance(contents, list):
            for content in reversed(contents):
                if isinstance(content, str):
                    return content
                elif isinstance(content, dict) and content.get("role") == "user":
                    text = self._extract_text_from_parts(content.get("parts", []))
                    if text:
                        return text
        return ""

    def _extract_user_query(self, kwargs: dict) -> str:
        """Extract the most recent user message from kwargs."""
        if "messages" in kwargs and kwargs["messages"]:
            for msg in reversed(kwargs["messages"]):
                if msg.get("role") == "user":
                    return msg.get("content", "")

        if "contents" in kwargs:
            result = self._extract_from_contents(kwargs["contents"])
            if result:
                return result

        if "request" in kwargs:
            try:
                formatted_kwargs = json.loads(
                    json_format.MessageToJson(kwargs["request"].__dict__["_pb"])
                )
                if "contents" in formatted_kwargs:
                    return self._extract_from_contents(formatted_kwargs["contents"])
            except Exception:
                pass

        return ""

    def _append_to_google_system_instruction_dict(self, config: dict, context: str):
        """Append context to system_instruction in a dict config."""
        if "system_instruction" not in config or not config["system_instruction"]:
            config["system_instruction"] = context.lstrip("\n")
            return

        existing = config["system_instruction"]

        if isinstance(existing, str):
            config["system_instruction"] = existing + context
        elif isinstance(existing, list):
            self._append_to_list(existing, context, config, "system_instruction")
        elif isinstance(existing, dict):
            self._append_to_content_dict(
                existing, context, config, "system_instruction"
            )
        else:
            config["system_instruction"] = context.lstrip("\n")

    def _append_to_google_system_instruction_obj(self, config, context: str):
        """Append context to system_instruction in a config object."""
        if not hasattr(config, "system_instruction"):
            return

        if config.system_instruction is None:
            config.system_instruction = context.lstrip("\n")
        elif isinstance(config.system_instruction, str):
            config.system_instruction = config.system_instruction + context
        elif isinstance(config.system_instruction, list):
            self._append_to_list_obj(config, context)
        elif hasattr(config.system_instruction, "text"):
            self._append_to_part_obj(config.system_instruction, context)
        elif hasattr(config.system_instruction, "parts"):
            self._append_to_content_obj(config.system_instruction, context)
        else:
            config.system_instruction = context.lstrip("\n")

    def _append_to_list(self, lst: list, context: str, parent: dict, key: str):
        """Append context to a list (handles list[str], list[dict], empty list)."""
        if not lst:
            parent[key] = [{"text": context.lstrip("\n")}]
        elif isinstance(lst[0], dict) and "text" in lst[0]:
            lst[0]["text"] += context
        elif isinstance(lst[0], str):
            lst[0] += context
        else:
            lst.insert(0, {"text": context.lstrip("\n")})

    def _append_to_list_obj(self, config, context: str):
        """Append context to a list in config object."""
        lst = config.system_instruction
        if not lst:
            config.system_instruction = context.lstrip("\n")
        elif hasattr(lst[0], "text"):
            lst[0].text += context
        elif isinstance(lst[0], str):
            lst[0] += context
        else:
            config.system_instruction = context.lstrip("\n")

    def _append_to_content_dict(
        self, content: dict, context: str, parent: dict, key: str
    ):
        """Append context to a Content dict (has 'parts') or Part dict (has 'text')."""
        if "parts" in content:
            parts = content.get("parts", [])
            if parts and isinstance(parts[0], dict) and "text" in parts[0]:
                parts[0]["text"] += context
            else:
                if not content.get("parts"):
                    content["parts"] = []
                content["parts"].insert(0, {"text": context.lstrip("\n")})
        elif "text" in content:
            content["text"] += context
        else:
            parent[key] = context.lstrip("\n")

    def _append_to_part_obj(self, part, context: str):
        """Append context to a Part object."""
        if part.text:
            part.text += context
        else:
            part.text = context.lstrip("\n")

    def _append_to_content_obj(self, content, context: str):
        """Append context to a Content object."""
        if (
            content.parts
            and len(content.parts) > 0
            and hasattr(content.parts[0], "text")
        ):
            if content.parts[0].text:
                content.parts[0].text += context
            else:
                content.parts[0].text = context.lstrip("\n")

    def _inject_google_system_instruction(self, kwargs: dict, context: str):
        """Inject recall context into Google/Gemini system_instruction."""
        if "request" in kwargs:
            formatted_kwargs = json.loads(
                json_format.MessageToJson(kwargs["request"].__dict__["_pb"])
            )
            system_instruction = formatted_kwargs.get("systemInstruction", {})
            parts = system_instruction.get("parts", [])
            if parts and isinstance(parts[0], dict) and "text" in parts[0]:
                parts[0]["text"] += context
            else:
                system_instruction["parts"] = [{"text": context.lstrip("\n")}]
            formatted_kwargs["systemInstruction"] = system_instruction
            json_format.ParseDict(formatted_kwargs, kwargs["request"].__dict__["_pb"])
        else:
            config = kwargs.get("config", None)
            if config is None:
                kwargs["config"] = {"system_instruction": context.lstrip("\n")}
            elif isinstance(config, dict):
                self._append_to_google_system_instruction_dict(config, context)
            else:
                self._append_to_google_system_instruction_obj(config, context)

    def inject_recalled_facts(self, kwargs: dict) -> dict:
        if self.config.storage is None or self.config.storage.driver is None:
            return kwargs

        if self.config.entity_id is None:
            return kwargs

        entity_id = self.config.storage.driver.entity.create(self.config.entity_id)
        if entity_id is None:
            return kwargs

        user_query = self._extract_user_query(kwargs)
        if not user_query:
            return kwargs

        logger.debug("User query: %s", truncate(user_query))

        from memori.memory.recall import Recall

        facts = Recall(self.config).search_facts(user_query, entity_id=entity_id)

        if not facts:
            logger.debug("No facts found to inject into prompt")
            return kwargs

        relevant_facts = [
            f
            for f in facts
            if f.get("similarity", 0) >= self.config.recall_relevance_threshold
        ]

        if not relevant_facts:
            logger.debug(
                "No facts above relevance threshold (%.2f)",
                self.config.recall_relevance_threshold,
            )
            return kwargs

        logger.debug("Injecting %d recalled facts into prompt", len(relevant_facts))
        fact_lines = [f"- {fact['content']}" for fact in relevant_facts]
        recall_context = (
            "\n\n<memori_context>\n"
            "Only use the relevant context if it is relevant to the user's query. "
            "Relevant context about the user:\n"
            + "\n".join(fact_lines)
            + "\n</memori_context>"
        )

        if llm_is_anthropic(
            self.config.framework.provider, self.config.llm.provider
        ) or llm_is_bedrock(self.config.framework.provider, self.config.llm.provider):
            existing_system = kwargs.get("system", "")
            kwargs["system"] = existing_system + recall_context
        elif llm_is_google(
            self.config.framework.provider, self.config.llm.provider
        ) or agno_is_google(self.config.framework.provider, self.config.llm.provider):
            self._inject_google_system_instruction(kwargs, recall_context)
        else:
            messages = kwargs.get("messages", [])
            if messages and messages[0].get("role") == "system":
                messages[0]["content"] = messages[0]["content"] + recall_context
            else:
                context_message = {
                    "role": "system",
                    "content": recall_context.lstrip("\n"),
                }
                messages.insert(0, context_message)

        return kwargs

    def inject_conversation_messages(self, kwargs: dict) -> dict:
        if self.config.cache.conversation_id is None:
            return kwargs

        if self.config.storage is None or self.config.storage.driver is None:
            return kwargs

        messages = self.config.storage.driver.conversation.messages.read(
            self.config.cache.conversation_id
        )
        if not messages:
            return kwargs

        self._injected_message_count = len(messages)
        logger.debug("Injecting %d conversation messages from history", len(messages))

        if (
            llm_is_openai(self.config.framework.provider, self.config.llm.provider)
            or agno_is_openai(self.config.framework.provider, self.config.llm.provider)
            or agno_is_xai(self.config.framework.provider, self.config.llm.provider)
        ):
            kwargs["messages"] = messages + kwargs["messages"]
        elif (
            llm_is_anthropic(self.config.framework.provider, self.config.llm.provider)
            or llm_is_bedrock(self.config.framework.provider, self.config.llm.provider)
            or agno_is_anthropic(
                self.config.framework.provider, self.config.llm.provider
            )
        ):
            filtered_messages = [m for m in messages if m.get("role") != "system"]
            kwargs["messages"] = filtered_messages + kwargs["messages"]
        elif llm_is_xai(self.config.framework.provider, self.config.llm.provider):
            from xai_sdk.chat import assistant, user

            xai_messages = []
            for message in messages:
                role = message.get("role", "")
                content = message.get("content", "")
                if role == "user":
                    xai_messages.append(user(content))
                elif role == "assistant":
                    xai_messages.append(assistant(content))

            kwargs["messages"] = xai_messages + kwargs["messages"]
        elif llm_is_google(
            self.config.framework.provider, self.config.llm.provider
        ) or agno_is_google(self.config.framework.provider, self.config.llm.provider):
            contents = []
            for message in messages:
                role = message["role"]
                if role == "assistant":
                    role = "model"
                contents.append({"parts": [{"text": message["content"]}], "role": role})

            if "request" in kwargs:
                formatted_kwargs = json.loads(
                    json_format.MessageToJson(kwargs["request"].__dict__["_pb"])
                )
                formatted_kwargs["contents"] = contents + formatted_kwargs["contents"]
                json_format.ParseDict(
                    formatted_kwargs, kwargs["request"].__dict__["_pb"]
                )
            else:
                existing_contents = kwargs.get("contents", [])
                if isinstance(existing_contents, str):
                    existing_contents = [
                        {"parts": [{"text": existing_contents}], "role": "user"}
                    ]
                elif isinstance(existing_contents, list):
                    normalized = []
                    for item in existing_contents:
                        if isinstance(item, str):
                            normalized.append(
                                {"parts": [{"text": item}], "role": "user"}
                            )
                        else:
                            normalized.append(item)
                    existing_contents = normalized
                kwargs["contents"] = contents + existing_contents
        else:
            raise NotImplementedError

        return kwargs

    def list_to_json(self, list_: list) -> list:
        return self._convert_to_json(list_)

    def response_to_json(self, response) -> dict | list:
        return self._convert_to_json(response)

    def set_client(self, framework_provider, llm_provider, provider_sdk_version):
        self.config.framework.provider = framework_provider
        self.config.llm.provider = llm_provider
        self.config.llm.provider_sdk_version = provider_sdk_version
        return self

    def uses_protobuf(self):
        self._uses_protobuf = True
        return self

    def _extract_system_prompt(self, messages: list | None) -> str | None:
        if not messages or not isinstance(messages, list):
            return None

        first_message = messages[0]
        if not isinstance(first_message, dict) or first_message.get("role") != "system":
            return None

        content = first_message.get("content", "")
        if not content:
            return None

        if "<memori_context>" in content:
            parts = content.split("<memori_context>")
            system_prompt = parts[0].strip()
            return system_prompt if system_prompt else None

        return content

    def _strip_memori_context_from_messages(self, messages: list) -> list:
        if not messages:
            return messages

        cleaned_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                cleaned_messages.append(msg)
                continue

            if msg.get("role") == "system" and "<memori_context>" in msg.get(
                "content", ""
            ):
                content = msg["content"]
                parts = content.split("<memori_context>")
                cleaned_content = parts[0].strip()

                if cleaned_content:
                    cleaned_msg = msg.copy()
                    cleaned_msg["content"] = cleaned_content
                    cleaned_messages.append(cleaned_msg)
            else:
                cleaned_messages.append(msg)

        return cleaned_messages

    def handle_post_response(self, kwargs, start_time, raw_response):
        from memori.memory._manager import Manager as MemoryManager

        if "model" in kwargs:
            self.config.llm.version = kwargs["model"]

        payload = self._format_payload(
            self.config.framework.provider,
            self.config.llm.provider,
            self.config.llm.version,
            start_time,
            __import__("time").time(),
            self._format_kwargs(kwargs),
            self._format_response(self.get_response_content(raw_response)),
        )

        MemoryManager(self.config).execute(payload)

        if self.config.augmentation is not None:
            from memori.llm._registry import Registry as LlmRegistry
            from memori.memory.augmentation.input import AugmentationInput

            llm_adapter = LlmRegistry().adapter(
                self.config.framework.provider,
                self.config.llm.provider,
            )
            messages_for_aug = llm_adapter.get_formatted_query(payload)

            if isinstance(raw_response, dict):
                choices = raw_response.get("choices", [])
                if choices:
                    choice = choices[0]
                    if isinstance(choice, dict):
                        content = choice.get("message", {}).get("content", "")
                    elif hasattr(choice, "message"):
                        content = getattr(choice.message, "content", "")
                    else:
                        content = ""
                else:
                    content = ""
            elif hasattr(raw_response, "choices"):
                content = raw_response.choices[0].message.content
            elif hasattr(raw_response, "text"):
                content = raw_response.text
            else:
                content = ""

            if content:
                logger.debug("Response content: %s", truncate(str(content)))

            messages_for_aug.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )

            system_prompt = self._extract_system_prompt(messages_for_aug)
            messages_for_aug = self._strip_memori_context_from_messages(
                messages_for_aug
            )

            if not self.config.entity_id and not self.config.process_id:
                return

            augmentation_input = AugmentationInput(
                conversation_id=self.config.cache.conversation_id,
                entity_id=self.config.entity_id,
                process_id=self.config.process_id,
                conversation_messages=messages_for_aug,
                system_prompt=system_prompt,
            )
            logger.debug("Kicking off AA - enqueueing augmentation")
            self.config.augmentation.enqueue(augmentation_input)


class BaseIterator:
    def __init__(self, config: Config, source_iterator):
        self.config = config
        self.source_iterator = source_iterator
        self.iterator = None
        self.raw_response: dict | list | None = None

    def configure_invoke(self, invoke: BaseInvoke):
        self.invoke = invoke
        return self

    def configure_request(self, kwargs, time_start):
        self._kwargs = kwargs
        self._time_start = time_start
        return self

    def process_chunk(self, chunk):
        if self.invoke._uses_protobuf is True:
            formatted_chunk = copy.deepcopy(chunk)
            if isinstance(self.raw_response, list):
                if "_pb" in formatted_chunk.__dict__:
                    self.raw_response.append(
                        json.loads(
                            json_format.MessageToJson(formatted_chunk.__dict__["_pb"])
                        )
                    )
        else:
            if isinstance(self.raw_response, dict):
                self.raw_response = merge_chunk(self.raw_response, chunk.__dict__)

        return self

    def set_raw_response(self):
        if self.raw_response is not None:
            return self

        self.raw_response = {}
        if self.invoke._uses_protobuf:
            self.raw_response = []

        return self


class BaseLlmAdaptor:
    def _exclude_injected_messages(self, messages, payload):
        injected_count = (
            payload.get("conversation", {})
            .get("query", {})
            .get("_memori_injected_count", 0)
        )
        return messages[injected_count:]

    def get_formatted_query(self, payload):
        raise NotImplementedError

    def get_formatted_response(self, payload):
        raise NotImplementedError


class BaseProvider:
    def __init__(self, entity):
        self.client = None
        self.entity = entity
        self.config = entity.config
