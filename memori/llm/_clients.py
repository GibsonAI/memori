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
    AGNO_FRAMEWORK_PROVIDER,
    AGNO_GOOGLE_LLM_PROVIDER,
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
    def register(self, client, _provider=None):
        if not hasattr(client, "messages"):
            raise RuntimeError("client provided is not instance of Anthropic")

        if not hasattr(client, "_memori_installed"):
            client.beta._messages_create = client.beta.messages.create
            client._messages_create = client.messages.create

            try:
                asyncio.get_running_loop()

                client.beta.messages.create = (
                    InvokeAsync(self.config, client.beta._messages_create)
                    .set_client(_provider, ATHROPIC_LLM_PROVIDER, client._version)
                    .invoke
                )
                client.messages.create = (
                    InvokeAsync(self.config, client._messages_create)
                    .set_client(_provider, ATHROPIC_LLM_PROVIDER, client._version)
                    .invoke
                )
            except RuntimeError:
                client.beta.messages.create = (
                    Invoke(self.config, client.beta._messages_create)
                    .set_client(_provider, ATHROPIC_LLM_PROVIDER, client._version)
                    .invoke
                )
                client.messages.create = (
                    Invoke(self.config, client._messages_create)
                    .set_client(_provider, ATHROPIC_LLM_PROVIDER, client._version)
                    .invoke
                )

            client._memori_installed = True

        return self


@Registry.register_client(lambda client: hasattr(client, "models"))
class Google(BaseClient):
    def register(self, client, _provider=None):
        if not hasattr(client, "models"):
            raise RuntimeError("client provided is not instance of genai.Client")

        if not hasattr(client, "_memori_installed"):
            client.models.actual_generate_content = client.models.generate_content
            client_version = getattr(client, "_version", None)

            llm_provider = (
                AGNO_GOOGLE_LLM_PROVIDER
                if _provider == AGNO_FRAMEWORK_PROVIDER
                else GOOGLE_LLM_PROVIDER
            )

            client.models.generate_content = (
                Invoke(self.config, client.models.actual_generate_content)
                .set_client(_provider, llm_provider, client_version)
                .uses_protobuf()
                .invoke
            )

            # Register sync streaming if available
            if hasattr(client.models, "generate_content_stream"):
                client.models.actual_generate_content_stream = (
                    client.models.generate_content_stream
                )
                client.models.generate_content_stream = (
                    Invoke(
                        self.config,
                        client.models.actual_generate_content_stream,
                    )
                    .set_client(_provider, llm_provider, client_version)
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
                    .set_client(_provider, llm_provider, client_version)
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
                        .set_client(_provider, llm_provider, client_version)
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

        if self.config.llm.provider is None:
            raise RuntimeError("Unsupported LLM client")

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

    def register(self, client, _provider=None, stream=False):
        from memori.llm._constants import XAI_LLM_PROVIDER
        from memori.llm._xai_wrappers import XAiWrappers

        if not hasattr(client, "chat"):
            raise RuntimeError("client provided is not instance of xAI")

        if not hasattr(client, "_memori_installed"):
            if hasattr(client.chat, "completions"):
                client.beta._chat_completions_parse = client.beta.chat.completions.parse
                client.chat._completions_create = client.chat.completions.create
                client_version = getattr(client, "_version", None)

                self.config.framework.provider = _provider
                self.config.llm.provider = XAI_LLM_PROVIDER
                self.config.llm.version = client_version

                try:
                    asyncio.get_running_loop()

                    if stream is True:
                        client.beta.chat.completions.parse = (
                            InvokeAsyncStream(
                                self.config, client.beta._chat_completions_parse
                            )
                            .set_client(_provider, XAI_LLM_PROVIDER, client_version)
                            .invoke
                        )
                        client.chat.completions.create = (
                            InvokeAsyncStream(
                                self.config,
                                client.chat._completions_create,
                            )
                            .set_client(_provider, XAI_LLM_PROVIDER, client_version)
                            .invoke
                        )
                    else:
                        client.beta.chat.completions.parse = (
                            InvokeAsync(
                                self.config, client.beta._chat_completions_parse
                            )
                            .set_client(_provider, XAI_LLM_PROVIDER, client_version)
                            .invoke
                        )
                        client.chat.completions.create = (
                            InvokeAsync(
                                self.config,
                                client.chat._completions_create,
                            )
                            .set_client(_provider, XAI_LLM_PROVIDER, client_version)
                            .invoke
                        )
                except RuntimeError:
                    if stream is True:
                        client.beta.chat.completions.parse = (
                            InvokeStream(
                                self.config, client.beta._chat_completions_parse
                            )
                            .set_client(_provider, XAI_LLM_PROVIDER, client_version)
                            .invoke
                        )
                        client.chat.completions.create = (
                            InvokeStream(
                                self.config,
                                client.chat._completions_create,
                            )
                            .set_client(_provider, XAI_LLM_PROVIDER, client_version)
                            .invoke
                        )
                    else:
                        client.beta.chat.completions.parse = (
                            Invoke(self.config, client.beta._chat_completions_parse)
                            .set_client(_provider, XAI_LLM_PROVIDER, client_version)
                            .invoke
                        )
                        client.chat.completions.create = (
                            Invoke(
                                self.config,
                                client.chat._completions_create,
                            )
                            .set_client(_provider, XAI_LLM_PROVIDER, client_version)
                            .invoke
                        )
            else:
                client.chat._create = client.chat.create
                client_version = getattr(client, "_version", None)

                self.config.framework.provider = _provider
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


class Agno(BaseClient):
    def register(self, openai_chat=None, claude=None, gemini=None, xai=None):
        if openai_chat is None and claude is None and gemini is None and xai is None:
            raise RuntimeError("Agno::register called without model")

        if openai_chat is not None:
            if not self._is_agno_openai_model(openai_chat):
                raise RuntimeError(
                    "model provided is not instance of agno.models.openai.OpenAIChat"
                )
            client = openai_chat.get_client()
            OpenAi(self.config).register(client, _provider=AGNO_FRAMEWORK_PROVIDER)

            if not hasattr(openai_chat, "_memori_original_get_client"):
                original_get_client = openai_chat.get_client
                openai_chat._memori_original_get_client = original_get_client
                openai_wrapper = OpenAi(self.config)

                def wrapped_get_client():
                    client = openai_chat._memori_original_get_client()
                    openai_wrapper.register(client, _provider=AGNO_FRAMEWORK_PROVIDER)
                    return client

                openai_chat.get_client = wrapped_get_client

                # Also wrap get_async_client for async support
                if hasattr(openai_chat, "get_async_client"):
                    original_get_async_client = openai_chat.get_async_client
                    openai_chat._memori_original_get_async_client = (
                        original_get_async_client
                    )

                    def wrapped_get_async_client():
                        client = openai_chat._memori_original_get_async_client()
                        openai_wrapper.register(
                            client, _provider=AGNO_FRAMEWORK_PROVIDER
                        )
                        return client

                    openai_chat.get_async_client = wrapped_get_async_client

        if claude is not None:
            if not self._is_agno_anthropic_model(claude):
                raise RuntimeError(
                    "model provided is not instance of agno.models.anthropic.Claude"
                )
            client = claude.get_client()
            Anthropic(self.config).register(client, _provider=AGNO_FRAMEWORK_PROVIDER)

            if not hasattr(claude, "_memori_original_get_client"):
                original_get_client = claude.get_client
                claude._memori_original_get_client = original_get_client
                anthropic_wrapper = Anthropic(self.config)

                def wrapped_get_client():
                    client = claude._memori_original_get_client()
                    anthropic_wrapper.register(
                        client, _provider=AGNO_FRAMEWORK_PROVIDER
                    )
                    return client

                claude.get_client = wrapped_get_client

                # Also wrap get_async_client for async support
                if hasattr(claude, "get_async_client"):
                    original_get_async_client = claude.get_async_client
                    claude._memori_original_get_async_client = original_get_async_client

                    def wrapped_get_async_client():
                        client = claude._memori_original_get_async_client()
                        anthropic_wrapper.register(
                            client, _provider=AGNO_FRAMEWORK_PROVIDER
                        )
                        return client

                    claude.get_async_client = wrapped_get_async_client

        if gemini is not None:
            if not self._is_agno_google_model(gemini):
                raise RuntimeError(
                    "model provided is not instance of agno.models.google.Gemini"
                )
            client = gemini.get_client()
            Google(self.config).register(client, _provider=AGNO_FRAMEWORK_PROVIDER)

            # Wrap get_client to ensure all future client instances are wrapped
            if not hasattr(gemini, "_memori_original_get_client"):
                original_get_client = gemini.get_client
                gemini._memori_original_get_client = original_get_client
                google_wrapper = Google(self.config)

                def wrapped_get_client():
                    client = gemini._memori_original_get_client()
                    google_wrapper.register(client, _provider=AGNO_FRAMEWORK_PROVIDER)
                    return client

                gemini.get_client = wrapped_get_client

        if xai is not None:
            if not self._is_agno_xai_model(xai):
                raise RuntimeError(
                    "model provided is not instance of agno.models.xai.xAI"
                )
            client = xai.get_client()
            XAi(self.config).register(client, _provider=AGNO_FRAMEWORK_PROVIDER)

            if not hasattr(xai, "_memori_original_get_client"):
                original_get_client = xai.get_client
                xai._memori_original_get_client = original_get_client
                xai_wrapper = XAi(self.config)

                def wrapped_get_client():
                    client = xai._memori_original_get_client()
                    xai_wrapper.register(client, _provider=AGNO_FRAMEWORK_PROVIDER)
                    return client

                xai.get_client = wrapped_get_client

                # Also wrap get_async_client for async support
                if hasattr(xai, "get_async_client"):
                    original_get_async_client = xai.get_async_client
                    xai._memori_original_get_async_client = original_get_async_client

                    def wrapped_get_async_client():
                        client = xai._memori_original_get_async_client()
                        xai_wrapper.register(client, _provider=AGNO_FRAMEWORK_PROVIDER)
                        return client

                    xai.get_async_client = wrapped_get_async_client

        return self

    def _is_agno_openai_model(self, model):
        return "agno.models.openai" in str(type(model).__module__)

    def _is_agno_anthropic_model(self, model):
        return "agno.models.anthropic" in str(type(model).__module__)

    def _is_agno_google_model(self, model):
        return "agno.models.google" in str(type(model).__module__)

    def _is_agno_xai_model(self, model):
        return "agno.models.xai" in str(type(model).__module__)
