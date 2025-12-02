from memori.llm._constants import (
    ATHROPIC_LLM_PROVIDER,
    GOOGLE_LLM_PROVIDER,
    LANGCHAIN_CHATBEDROCK_LLM_PROVIDER,
    LANGCHAIN_CHATGOOGLEGENAI_LLM_PROVIDER,
    LANGCHAIN_CHATVERTEXAI_LLM_PROVIDER,
    LANGCHAIN_FRAMEWORK_PROVIDER,
    LANGCHAIN_OPENAI_LLM_PROVIDER,
    OPENAI_LLM_PROVIDER,
)
from memori.llm._utils import (
    client_is_bedrock,
    llm_is_anthropic,
    llm_is_bedrock,
    llm_is_google,
    llm_is_openai,
    provider_is_langchain,
)


def test_client_is_bedrock():
    assert client_is_bedrock("abc", "def") is False
    assert client_is_bedrock(LANGCHAIN_FRAMEWORK_PROVIDER, "def") is False
    assert client_is_bedrock("abc", LANGCHAIN_CHATBEDROCK_LLM_PROVIDER) is False
    assert (
        client_is_bedrock(
            LANGCHAIN_FRAMEWORK_PROVIDER, LANGCHAIN_CHATBEDROCK_LLM_PROVIDER
        )
        is True
    )


def test_llm_is_anthropic():
    assert llm_is_anthropic("abc", "def") is False
    assert llm_is_anthropic("abc", ATHROPIC_LLM_PROVIDER) is True
    assert llm_is_anthropic(None, ATHROPIC_LLM_PROVIDER) is True


def test_llm_is_bedrock():
    assert llm_is_bedrock("abc", "def") is False
    assert (
        llm_is_bedrock(LANGCHAIN_FRAMEWORK_PROVIDER, LANGCHAIN_CHATBEDROCK_LLM_PROVIDER)
        is True
    )
    assert llm_is_bedrock(LANGCHAIN_FRAMEWORK_PROVIDER, "def") is False
    assert llm_is_bedrock("abc", LANGCHAIN_CHATBEDROCK_LLM_PROVIDER) is False


def test_llm_is_google():
    assert llm_is_google("abc", "def") is False
    assert llm_is_google("abc", GOOGLE_LLM_PROVIDER) is True
    assert llm_is_google(None, GOOGLE_LLM_PROVIDER) is True
    assert (
        llm_is_google(
            LANGCHAIN_FRAMEWORK_PROVIDER, LANGCHAIN_CHATGOOGLEGENAI_LLM_PROVIDER
        )
        is True
    )
    assert (
        llm_is_google(LANGCHAIN_FRAMEWORK_PROVIDER, LANGCHAIN_CHATVERTEXAI_LLM_PROVIDER)
        is True
    )


def test_llm_is_openai():
    assert llm_is_openai("abc", "def") is False
    assert llm_is_openai("abc", OPENAI_LLM_PROVIDER) is True
    assert llm_is_openai(None, OPENAI_LLM_PROVIDER) is True
    assert (
        llm_is_openai(LANGCHAIN_FRAMEWORK_PROVIDER, LANGCHAIN_OPENAI_LLM_PROVIDER)
        is True
    )


def test_provider_is_langchain():
    assert provider_is_langchain("abc") is False
    assert provider_is_langchain(LANGCHAIN_FRAMEWORK_PROVIDER) is True
    assert provider_is_langchain(None) is False
