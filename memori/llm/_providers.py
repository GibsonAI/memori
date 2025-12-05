r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""

import warnings

from memori.llm._base import BaseProvider
from memori.llm._clients import Agno as AgnoMemoriClient
from memori.llm._clients import Anthropic as AnthropicMemoriClient
from memori.llm._clients import Google as GoogleMemoriClient
from memori.llm._clients import LangChain as LangChainMemoriClient
from memori.llm._clients import OpenAi as OpenAiMemoriClient
from memori.llm._clients import PydanticAi as PydanticAiMemoriClient
from memori.llm._clients import XAi as XAiMemoriClient


class Agno(BaseProvider):
    def register(self, openai_chat=None, claude=None, gemini=None, xai=None):
        warnings.warn(
            "memori.agno.register() is deprecated. Use memori.llm.register(client) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.client is None:
            self.client = AgnoMemoriClient(self.config).register(
                openai_chat=openai_chat,
                claude=claude,
                gemini=gemini,
                xai=xai,
            )

        return self.entity


class Anthropic(BaseProvider):
    def register(self, client):
        warnings.warn(
            "memori.anthropic.register() is deprecated. Use memori.llm.register(client) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.client is None:
            self.client = AnthropicMemoriClient(self.config).register(client)

        return self.entity


class Google(BaseProvider):
    def register(self, client):
        warnings.warn(
            "memori.google.register() is deprecated. Use memori.llm.register(client) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.client is None:
            self.client = GoogleMemoriClient(self.config).register(client)

        return self.entity


class LangChain(BaseProvider):
    def register(
        self, chatbedrock=None, chatgooglegenai=None, chatopenai=None, chatvertexai=None
    ):
        warnings.warn(
            "memori.langchain.register() is deprecated. Use memori.llm.register(client) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.client is None:
            self.client = LangChainMemoriClient(self.config).register(
                chatbedrock=chatbedrock,
                chatgooglegenai=chatgooglegenai,
                chatopenai=chatopenai,
                chatvertexai=chatvertexai,
            )

        return self.entity


class OpenAi(BaseProvider):
    def register(self, client, stream=False):
        warnings.warn(
            "memori.openai.register() is deprecated. Use memori.llm.register(client) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.client is None:
            self.client = OpenAiMemoriClient(self.config).register(
                client, stream=stream
            )

        return self.entity


class PydanticAi(BaseProvider):
    def register(self, client):
        warnings.warn(
            "memori.pydantic_ai.register() is deprecated. Use memori.llm.register(client) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.client is None:
            self.client = PydanticAiMemoriClient(self.config).register(client)

        return self.entity


class XAi(BaseProvider):
    def register(self, client, stream=False):
        warnings.warn(
            "memori.xai.register() is deprecated. Use memori.llm.register(client) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.client is None:
            self.client = XAiMemoriClient(self.config).register(client, stream=stream)

        return self.entity
