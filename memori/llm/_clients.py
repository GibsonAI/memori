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

from memori.llm._base import BaseClient
from memori.llm._constants import (
    ATHROPIC_LLM_PROVIDER,
    GOOGLE_LLM_PROVIDER,
    LANGCHAIN_CHATBEDROCK_LLM_PROVIDER,
    LANGCHAIN_CHATGOOGLEGENAI_LLM_PROVIDER,
    LANGCHAIN_CHATVERTEXAI_LLM_PROVIDER,
    LANGCHAIN_FRAMEWORK_PROVIDER,
    LANGCHAIN_OPENAI_LLM_PROVIDER,
    OPENAI_LLM_PROVIDER,
    PYDANTIC_AI_FRAMEWORK_PROVIDER,
    PYDANTIC_AI_OPENAI_LLM_PROVIDER,
)
from memori.llm._invoke import (
    Invoke,
    InvokeAsync,
    InvokeAsyncIterator,
    InvokeAsyncStream,
    InvokeStream,
)
from memori.llm._registry import Registry


@Registry.register_client(lambda client: hasattr(client, "messages"))
class Anthropic(BaseClient):
    def register(self, client):
        if not hasattr(client, "messages"):
            raise RuntimeError("client provided is not instance of Anthropic")

        if not hasattr(client, "_memori_installed"):
            client.beta._messages_create = client.beta.messages.create
            client._messages_create = client.messages.create

            try:
                asyncio.get_running_loop()

                client.beta.messages.create = (
                    InvokeAsync(self.config, client.beta._messages_create)
                    .set_client(None, ATHROPIC_LLM_PROVIDER, client._version)
                    .invoke
                )
                client.messages.create = (
                    InvokeAsync(self.config, client._messages_create)
                    .set_client(None, ATHROPIC_LLM_PROVIDER, client._version)
                    .invoke
                )
            except RuntimeError:
                client.beta.messages.create = (
                    Invoke(self.config, client.beta._messages_create)
                    .set_client(None, ATHROPIC_LLM_PROVIDER, client._version)
                    .invoke
                )
                client.messages.create = (
                    Invoke(self.config, client._messages_create)
                    .set_client(None, ATHROPIC_LLM_PROVIDER, client._version)
                    .invoke
                )

            client._memori_installed = True

        return self


@Registry.register_client(lambda client: hasattr(client, "models"))
class Google(BaseClient):
    def register(self, client):
        if not hasattr(client, "models"):
            raise RuntimeError("client provided is not instance of genai.Client")

        if not hasattr(client, "_memori_installed"):
            client.models.actual_generate_content = client.models.generate_content
            client_version = getattr(client, "_version", None)
            client.models.generate_content = (
                Invoke(self.config, client.models.actual_generate_content)
                .set_client(None, GOOGLE_LLM_PROVIDER, client_version)
                .uses_protobuf()
                .invoke
            )

            # Register async client if available
            if hasattr(client, "aio") and hasattr(client.aio, "models"):
                client.aio.models.actual_generate_content = (
                    client.aio.models.generate_content
                )
                client.aio.models.generate_content = (
                    InvokeAsync(self.config, client.aio.models.actual_generate_content)
                    .set_client(None, GOOGLE_LLM_PROVIDER, client_version)
                    .uses_protobuf()
                    .invoke
                )

                # Register streaming if available
                if hasattr(client.aio.models, "generate_content_stream"):
                    client.aio.models.actual_generate_content_stream = (
                        client.aio.models.generate_content_stream
                    )
                    client.aio.models.generate_content_stream = (
                        InvokeAsyncIterator(
                            self.config,
                            client.aio.models.actual_generate_content_stream,
                        )
                        .set_client(None, GOOGLE_LLM_PROVIDER, client_version)
                        .uses_protobuf()
                        .invoke
                    )

            client._memori_installed = True

        return self


class LangChain(BaseClient):
    def register(
        self, chatbedrock=None, chatgooglegenai=None, chatopenai=None, chatvertexai=None
    ):
        if (
            chatbedrock is None
            and chatgooglegenai is None
            and chatopenai is None
            and chatvertexai is None
        ):
            raise RuntimeError("LangChain::register called without client")

        if chatbedrock is not None:
            if not hasattr(chatbedrock, "client"):
                raise RuntimeError("client provided is not instance of ChatBedrock")

            if not hasattr(chatbedrock.client, "_memori_installed"):
                chatbedrock.client._invoke_model = chatbedrock.client.invoke_model
                chatbedrock.client.invoke_model = (
                    Invoke(self.config, chatbedrock.client._invoke_model)
                    .set_client(
                        LANGCHAIN_FRAMEWORK_PROVIDER,
                        LANGCHAIN_CHATBEDROCK_LLM_PROVIDER,
                        None,
                    )
                    .invoke
                )

                chatbedrock.client._invoke_model_with_response_stream = (
                    chatbedrock.client.invoke_model_with_response_stream
                )
                chatbedrock.client.invoke_model_with_response_stream = (
                    Invoke(
                        self.config,
                        chatbedrock.client._invoke_model_with_response_stream,
                    )
                    .set_client(
                        LANGCHAIN_FRAMEWORK_PROVIDER,
                        LANGCHAIN_CHATBEDROCK_LLM_PROVIDER,
                        None,
                    )
                    .invoke
                )

                chatbedrock.client._memori_installed = True

        if chatgooglegenai is not None:
            if not hasattr(chatgooglegenai, "client"):
                raise RuntimeError(
                    "client provided is not instance of ChatGoogleGenerativeAI"
                )

            if not hasattr(chatgooglegenai.client, "_memori_installed"):
                chatgooglegenai.client._generate_content = (
                    chatgooglegenai.client.generate_content
                )
                chatgooglegenai.client.generate_content = (
                    Invoke(self.config, chatgooglegenai.client._generate_content)
                    .set_client(
                        LANGCHAIN_FRAMEWORK_PROVIDER,
                        LANGCHAIN_CHATGOOGLEGENAI_LLM_PROVIDER,
                        None,
                    )
                    .uses_protobuf()
                    .invoke
                )

                if chatgooglegenai.async_client is not None:
                    chatgooglegenai.async_client._stream_generate_content = (
                        chatgooglegenai.async_client.stream_generate_content
                    )
                    chatgooglegenai.async_client.stream_generate_content = (
                        InvokeAsyncIterator(
                            self.config,
                            chatgooglegenai.async_client._stream_generate_content,
                        )
                        .set_client(
                            LANGCHAIN_FRAMEWORK_PROVIDER,
                            LANGCHAIN_CHATGOOGLEGENAI_LLM_PROVIDER,
                            None,
                        )
                        .uses_protobuf()
                        .invoke
                    )

                chatgooglegenai.client._memori_installed = True

        if chatopenai is not None:
            if not hasattr(chatopenai, "client") or not hasattr(
                chatopenai, "async_client"
            ):
                raise RuntimeError("client provided is not instance of ChatOpenAI")

            for client in filter(
                None,
                [getattr(chatopenai, "http_client", None), chatopenai.client._client],
            ):
                if not hasattr(client, "_memori_installed"):
                    client.beta._chat_completions_create = (
                        client.beta.chat.completions.create
                    )
                    client.beta.chat.completions.create = (
                        Invoke(self.config, client.beta._chat_completions_create)
                        .set_client(
                            LANGCHAIN_FRAMEWORK_PROVIDER,
                            LANGCHAIN_OPENAI_LLM_PROVIDER,
                            None,
                        )
                        .invoke
                    )

                    client.beta._chat_completions_parse = (
                        client.beta.chat.completions.parse
                    )
                    client.beta.chat.completions.parse = (
                        Invoke(self.config, client.beta._chat_completions_parse)
                        .set_client(
                            LANGCHAIN_FRAMEWORK_PROVIDER,
                            LANGCHAIN_OPENAI_LLM_PROVIDER,
                            None,
                        )
                        .invoke
                    )

                    client._chat_completions_create = client.chat.completions.create
                    client.chat.completions.create = (
                        Invoke(self.config, client._chat_completions_create)
                        .set_client(
                            LANGCHAIN_FRAMEWORK_PROVIDER,
                            LANGCHAIN_OPENAI_LLM_PROVIDER,
                            None,
                        )
                        .invoke
                    )

                    client._chat_completions_parse = client.chat.completions.parse
                    client.chat.completions.parse = (
                        Invoke(self.config, client._chat_completions_parse)
                        .set_client(
                            LANGCHAIN_FRAMEWORK_PROVIDER,
                            LANGCHAIN_OPENAI_LLM_PROVIDER,
                            None,
                        )
                        .invoke
                    )

                    client._memori_installed = True

            for client in filter(
                None,
                [
                    getattr(chatopenai, "async_http_client", None),
                    chatopenai.async_client._client,
                ],
            ):
                if not hasattr(client, "_memori_installed"):
                    client.beta._chat_completions_create = (
                        client.beta.chat.completions.create
                    )
                    client.beta.chat.completions.create = (
                        InvokeAsyncIterator(
                            self.config, client.beta._chat_completions_create
                        )
                        .set_client(
                            LANGCHAIN_FRAMEWORK_PROVIDER,
                            LANGCHAIN_OPENAI_LLM_PROVIDER,
                            None,
                        )
                        .invoke
                    )

                    client.beta._chat_completions_parse = (
                        client.beta.chat.completions.parse
                    )
                    client.beta.chat.completions.parse = (
                        InvokeAsyncIterator(
                            self.config, client.beta._chat_completions_parse
                        )
                        .set_client(
                            LANGCHAIN_FRAMEWORK_PROVIDER,
                            LANGCHAIN_OPENAI_LLM_PROVIDER,
                            None,
                        )
                        .invoke
                    )

                    client._chat_completions_create = client.chat.completions.create
                    client.chat.completions.create = (
                        InvokeAsyncIterator(
                            self.config, client._chat_completions_create
                        )
                        .set_client(
                            LANGCHAIN_FRAMEWORK_PROVIDER,
                            LANGCHAIN_OPENAI_LLM_PROVIDER,
                            None,
                        )
                        .invoke
                    )

                    client._chat_completions_parse = client.chat.completions.parse
                    client.chat.completions.parse = (
                        InvokeAsyncIterator(self.config, client._chat_completions_parse)
                        .set_client(
                            LANGCHAIN_FRAMEWORK_PROVIDER,
                            LANGCHAIN_OPENAI_LLM_PROVIDER,
                            None,
                        )
                        .invoke
                    )

                    client._memori_installed = True

        if chatvertexai is not None:
            if not hasattr(chatvertexai, "prediction_client"):
                raise RuntimeError("client provided isnot instance of ChatVertexAI")

            if not hasattr(chatvertexai.prediction_client, "_memori_installed"):
                chatvertexai.prediction_client.actual_generate_content = (
                    chatvertexai.prediction_client.generate_content
                )
                chatvertexai.prediction_client.generate_content = (
                    Invoke(
                        self.config,
                        chatvertexai.prediction_client.actual_generate_content,
                    )
                    .set_client(
                        LANGCHAIN_FRAMEWORK_PROVIDER,
                        LANGCHAIN_CHATVERTEXAI_LLM_PROVIDER,
                        None,
                    )
                    .uses_protobuf()
                    .invoke
                )

                chatvertexai.prediction_client._memori_installed = True

        return self


@Registry.register_client(
    lambda client: hasattr(client, "chat") and hasattr(client, "_version")
)
class OpenAi(BaseClient):
    def register(self, client, _provider=None, stream=False):
        if not hasattr(client, "chat"):
            raise RuntimeError("client provided is not instance of OpenAI")

        if not hasattr(client, "_memori_installed"):
            client.beta._chat_completions_parse = client.beta.chat.completions.parse
            client.chat._completions_create = client.chat.completions.create

            try:
                asyncio.get_running_loop()

                if stream is True:
                    client.beta.chat.completions.parse = (
                        InvokeAsyncStream(
                            self.config, client.beta._chat_completions_parse
                        )
                        .set_client(_provider, OPENAI_LLM_PROVIDER, client._version)
                        .invoke
                    )
                    client.chat.completions.create = (
                        InvokeAsyncStream(
                            self.config,
                            client.chat._completions_create,
                        )
                        .set_client(_provider, OPENAI_LLM_PROVIDER, client._version)
                        .invoke
                    )
                else:
                    client.beta.chat.completions.parse = (
                        InvokeAsync(self.config, client.beta._chat_completions_parse)
                        .set_client(_provider, OPENAI_LLM_PROVIDER, client._version)
                        .invoke
                    )
                    client.chat.completions.create = (
                        InvokeAsync(
                            self.config,
                            client.chat._completions_create,
                        )
                        .set_client(_provider, OPENAI_LLM_PROVIDER, client._version)
                        .invoke
                    )
            except RuntimeError:
                if stream is True:
                    client.beta.chat.completions.parse = (
                        InvokeStream(self.config, client.beta._chat_completions_parse)
                        .set_client(_provider, OPENAI_LLM_PROVIDER, client._version)
                        .invoke
                    )
                    client.chat.completions.create = (
                        InvokeStream(
                            self.config,
                            client.chat._completions_create,
                        )
                        .set_client(_provider, OPENAI_LLM_PROVIDER, client._version)
                        .invoke
                    )
                else:
                    client.beta.chat.completions.parse = (
                        Invoke(self.config, client.beta._chat_completions_parse)
                        .set_client(_provider, OPENAI_LLM_PROVIDER, client._version)
                        .invoke
                    )
                    client.chat.completions.create = (
                        Invoke(
                            self.config,
                            client.chat._completions_create,
                        )
                        .set_client(_provider, OPENAI_LLM_PROVIDER, client._version)
                        .invoke
                    )

            client._memori_installed = True

        return self


@Registry.register_client(
    lambda client: hasattr(client, "chat")
    and hasattr(client.chat, "completions")
    and not hasattr(client, "_version")
)
class PydanticAi(BaseClient):
    def register(self, client):
        if not hasattr(client, "chat"):
            raise RuntimeError("client provided was not instantiated using PydanticAi")

        if not hasattr(client, "_memori_installed"):
            client.chat.completions.actual_chat_completions_create = (
                client.chat.completions.create
            )

            client.chat.completions.create = (
                InvokeAsyncIterator(
                    self.config,
                    client.chat.completions.actual_chat_completions_create,
                )
                .set_client(
                    PYDANTIC_AI_FRAMEWORK_PROVIDER,
                    PYDANTIC_AI_OPENAI_LLM_PROVIDER,
                    client._version,
                )
                .invoke
            )

            client._memori_installed = True

        return self


@Registry.register_client(lambda client: "xai" in str(type(client).__module__).lower())
class XAi(BaseClient):
    """
    XAI client requires special handling due to its two-step API.

    Unlike other clients, the actual API call happens on the Chat object
    returned by create(), not on the create() method itself. All wrapping
    logic is delegated to the XAiWrappers class.
    """

    def register(self, client, stream=False):
        from memori.llm._constants import XAI_LLM_PROVIDER
        from memori.llm._xai_wrappers import XAiWrappers

        if not hasattr(client, "chat"):
            raise RuntimeError("client provided is not instance of xAI")

        if not hasattr(client, "_memori_installed"):
            client.chat._create = client.chat.create
            client_version = getattr(client, "_version", None)

            self.config.llm.provider = XAI_LLM_PROVIDER
            self.config.llm.version = client_version

            wrappers = XAiWrappers(self.config)

            def wrapped_create(*args, **kwargs):
                kwargs = wrappers.inject_conversation_history(kwargs)
                chat_obj = client.chat._create(*args, **kwargs)
                wrappers.wrap_chat_methods(chat_obj, client_version)
                return chat_obj

            client.chat.create = wrapped_create
            client._memori_installed = True

        return self
