import pytest

from memori.llm._constants import (
    ATHROPIC_LLM_PROVIDER,
    GOOGLE_LLM_PROVIDER,
    LANGCHAIN_CHATBEDROCK_LLM_PROVIDER,
    LANGCHAIN_FRAMEWORK_PROVIDER,
    OPENAI_LLM_PROVIDER,
)
from memori.llm._registry import Registry
from memori.llm.adapters.anthropic._adapter import Adapter as AnthropicLlmAdapter
from memori.llm.adapters.bedrock._adapter import Adapter as BedrockLlmAdapter
from memori.llm.adapters.google._adapter import Adapter as GoogleLlmAdapter
from memori.llm.adapters.openai._adapter import Adapter as OpenAiLlmAdapter


def test_llm_anthropic():
    assert isinstance(
        Registry().adapter(None, ATHROPIC_LLM_PROVIDER), AnthropicLlmAdapter
    )


def test_llm_bedrock():
    assert isinstance(
        Registry().adapter(
            LANGCHAIN_FRAMEWORK_PROVIDER, LANGCHAIN_CHATBEDROCK_LLM_PROVIDER
        ),
        BedrockLlmAdapter,
    )


def test_llm_google():
    assert isinstance(Registry().adapter(None, GOOGLE_LLM_PROVIDER), GoogleLlmAdapter)


def test_llm_openai():
    assert isinstance(Registry().adapter(None, OPENAI_LLM_PROVIDER), OpenAiLlmAdapter)


def test_llm_adapter_raises_for_none_provider():
    """Test that providing None as both provider and title raises RuntimeError."""

    with pytest.raises(RuntimeError, match="Unsupported LLM provider"):
        Registry().adapter(None, None)


def test_llm_adapter_raises_for_unsupported_provider():
    """Test that providing an unsupported provider raises RuntimeError."""

    with pytest.raises(RuntimeError, match="Unsupported LLM provider"):
        Registry().adapter("mistral", "mistral")


def test_llm_client_raises_helpful_error_for_langchain():
    """Test that LangChain clients produce a helpful error message."""

    class MockLangChainClient:
        pass

    MockLangChainClient.__module__ = "langchain_openai.chat_models.base"
    MockLangChainClient.__name__ = "ChatOpenAI"

    mock_client = MockLangChainClient()
    mock_config = None

    with pytest.raises(
        RuntimeError,
        match=r"LangChain models require named parameters.*llm\.register\(chatopenai=client\)",
    ):
        Registry().client(mock_client, mock_config)
