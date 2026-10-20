from memori.llm._base import BaseClient
from memori.llm._constants import (
    AGNO_FRAMEWORK_PROVIDER,
    AGNO_GOOGLE_LLM_PROVIDER,
    ANTHROPIC_LLM_PROVIDER,
    GOOGLE_LLM_PROVIDER,
    LITELLM_LLM_PROVIDER,
    OPENAI_LLM_PROVIDER,
    PYDANTIC_AI_FRAMEWORK_PROVIDER,
    PYDANTIC_AI_OPENAI_LLM_PROVIDER,
)
from memori.llm._registry import Registry
from memori.llm._utils import (
    client_is_anthropic,
    client_is_google,
    client_is_litellm,
    client_is_openai,
    client_is_pydantic_ai,
    client_is_xai,
)
from memori.llm.invoke.invoke import Invoke, InvokeAsync, InvokeAsyncIterator


@Registry.register_client(client_is_anthropic)
class Anthropic(BaseClient):
    def register(self, client, _provider=None):
        if not hasattr(client, "messages"):
            raise RuntimeError("client provided is not instance of Anthropic")

        if not hasattr(client, "_memori_installed"):
            platform = _detect_platform(client)
            if platform:
                self.config.platform.provider = platform

            client.beta._messages_create = client.beta.messages.create
            client._messages_create = client.messages.create

            try:
                import anthropic

                client_version = anthropic.__version__
            except (ImportError, AttributeError):
                client_version = None

            self._wrap_method(
                client.beta.messages,
                "create",
                client.beta,
                "_messages_create",
                _provider,
                ANTHROPIC_LLM_PROVIDER,
                client_version,
            )
            self._wrap_method(
                client.messages,
                "create",
                client,
                "_messages_create",
                _provider,
                ANTHROPIC_LLM_PROVIDER,
                client_version,
            )

            client._memori_installed = True

        return self


@Registry.register_client(client_is_google)
class Google(BaseClient):
    def register(self, client, _provider=None):
        if not hasattr(client, "models"):
            raise RuntimeError("client provided is not instance of genai.Client")

        if not hasattr(client, "_memori_installed"):
            client.models.actual_generate_content = client.models.generate_content

            try:
                from google import genai

                client_version = genai.__version__
            except (ImportError, AttributeError):
                try:
                    from importlib.metadata import version

                    client_version = version("google-genai")
                except Exception:
                    client_version = None

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


def _detect_platform(client):
    if hasattr(client, "base_url"):
        base_url = str(client.base_url).lower()
        if "nebius" in base_url:
            return "nebius"
        if "deepseek" in base_url:
            return "deepseek"
        if "nvidia" in base_url:
            return "nvidia_nim"
        if "minimax" in base_url:
            return "minimax"
    return None


@Registry.register_client(client_is_openai)
class OpenAi(BaseClient):
    def register(self, client, _provider=None, stream=False):
        if not hasattr(client, "chat"):
            raise RuntimeError("client provided is not instance of OpenAI")

        if not hasattr(client, "_memori_installed"):
            client.beta._chat_completions_parse = client.beta.chat.completions.parse
            client.chat._completions_create = client.chat.completions.create

            platform = _detect_platform(client)
            if platform:
                self.config.platform.provider = platform

            self.config.llm.provider_sdk_version = client._version

            self._wrap_method(
                client.beta.chat.completions,
                "parse",
                client.beta,
                "_chat_completions_parse",
                _provider,
                OPENAI_LLM_PROVIDER,
                client._version,
                stream,
            )
            self._wrap_method(
                client.chat.completions,
                "create",
                client.chat,
                "_completions_create",
                _provider,
                OPENAI_LLM_PROVIDER,
                client._version,
                stream,
            )

            if hasattr(client, "responses"):
                client._responses_create = client.responses.create
                self._wrap_method(
                    client.responses,
                    "create",
                    client,
                    "_responses_create",
                    _provider,
                    OPENAI_LLM_PROVIDER,
                    client._version,
                    stream,
                )

            client._memori_installed = True

        return self


@Registry.register_client(client_is_pydantic_ai)
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


@Registry.register_client(client_is_xai)
class XAi(BaseClient):
    def register(self, client, _provider=None, stream=False):
        from memori.llm._constants import XAI_LLM_PROVIDER
        from memori.llm._xai_wrappers import XAiWrappers

        if not hasattr(client, "chat"):
            raise RuntimeError("client provided is not instance of xAI")

        try:
            import xai_sdk

            client_version = xai_sdk.__version__
        except (ImportError, AttributeError):
            client_version = None

        if not hasattr(client, "_memori_installed"):
            if hasattr(client.chat, "completions"):
                client.beta._chat_completions_parse = client.beta.chat.completions.parse
                client.chat._completions_create = client.chat.completions.create

                self.config.framework.provider = _provider
                self.config.llm.provider = XAI_LLM_PROVIDER
                self.config.llm.provider_sdk_version = client_version

                self._wrap_method(
                    client.beta.chat.completions,
                    "parse",
                    client.beta,
                    "_chat_completions_parse",
                    _provider,
                    XAI_LLM_PROVIDER,
                    client_version,
                    stream,
                )
                self._wrap_method(
                    client.chat.completions,
                    "create",
                    client.chat,
                    "_completions_create",
                    _provider,
                    XAI_LLM_PROVIDER,
                    client_version,
                    stream,
                )
            else:
                client.chat._create = client.chat.create

                self.config.framework.provider = _provider
                self.config.llm.provider = XAI_LLM_PROVIDER
                self.config.llm.provider_sdk_version = client_version

                wrappers = XAiWrappers(self.config)

                def wrapped_create(*args, **kwargs):
                    model = kwargs.get("model")
                    kwargs = wrappers.inject_conversation_history(kwargs)
                    chat_obj = client.chat._create(*args, **kwargs)
                    wrappers.wrap_chat_methods(chat_obj, client_version, model)
                    return chat_obj

                client.chat.create = wrapped_create

            client._memori_installed = True

        return self


@Registry.register_client(client_is_litellm)
class LiteLLM(BaseClient):
    """Memori integration for LiteLLM (module or Router).

    Accepts two registration patterns:

    **Router (recommended for apps/servers):**
        import litellm
        from memori import Memori

        router = litellm.Router(model_list=[...])
        memori = Memori(...)
        memori.llm.register(router)

    **Module (convenience for simple scripts):**
        import litellm
        from memori import Memori

        memori = Memori(...)
        memori.llm.register(litellm)   # patches litellm.completion + litellm.acompletion

    Router registration is preferred because it wraps instance methods
    instead of patching global module functions, making it safe for
    concurrent use in servers.
    """

    def register(self, client, _provider=None):
        # `client` is the litellm module or a litellm.Router instance.
        if not hasattr(client, "completion"):
            raise RuntimeError(
                "expected the litellm module or a LiteLLM Router object "
                "with a `completion` method"
            )

        if not hasattr(client, "_memori_installed"):
            client_version = (
                getattr(client, "__version__", None) or _resolve_litellm_version()
            )

            self.config.framework.provider = _provider
            self.config.llm.provider = LITELLM_LLM_PROVIDER
            self.config.llm.provider_sdk_version = client_version

            client._completion = client.completion
            self._wrap_method(
                client,
                "completion",
                client,
                "_completion",
                _provider,
                LITELLM_LLM_PROVIDER,
                client_version,
            )

            if hasattr(client, "acompletion"):
                client._acompletion = client.acompletion
                self._wrap_method(
                    client,
                    "acompletion",
                    client,
                    "_acompletion",
                    _provider,
                    LITELLM_LLM_PROVIDER,
                    client_version,
                )

            client._memori_installed = True

        return self


def _resolve_litellm_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("litellm")
    except Exception:
        return None
