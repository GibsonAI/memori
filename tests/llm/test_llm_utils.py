from memori.llm._constants import (
    AGNO_ANTHROPIC_LLM_PROVIDER,
    AGNO_FRAMEWORK_PROVIDER,
    AGNO_GOOGLE_LLM_PROVIDER,
    AGNO_OPENAI_LLM_PROVIDER,
    AGNO_XAI_LLM_PROVIDER,
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
    agno_is_anthropic,
    agno_is_google,
    agno_is_openai,
    agno_is_xai,
    client_is_bedrock,
    llm_is_anthropic,
    llm_is_bedrock,
    llm_is_google,
    llm_is_openai,
    provider_is_agno,
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


def test_provider_is_agno():
    assert provider_is_agno("abc") is False
    assert provider_is_agno(AGNO_FRAMEWORK_PROVIDER) is True
    assert provider_is_agno(None) is False


def test_agno_is_openai():
    assert agno_is_openai("abc", "def") is False
    assert agno_is_openai(AGNO_FRAMEWORK_PROVIDER, "def") is False
    assert agno_is_openai("abc", AGNO_OPENAI_LLM_PROVIDER) is False
    assert agno_is_openai(AGNO_FRAMEWORK_PROVIDER, AGNO_OPENAI_LLM_PROVIDER) is True


def test_agno_is_anthropic():
    assert agno_is_anthropic("abc", "def") is False
    assert agno_is_anthropic(AGNO_FRAMEWORK_PROVIDER, "def") is False
    assert agno_is_anthropic("abc", AGNO_ANTHROPIC_LLM_PROVIDER) is False
    assert (
        agno_is_anthropic(AGNO_FRAMEWORK_PROVIDER, AGNO_ANTHROPIC_LLM_PROVIDER) is True
    )


def test_agno_is_google():
    assert agno_is_google("abc", "def") is False
    assert agno_is_google(AGNO_FRAMEWORK_PROVIDER, "def") is False
    assert agno_is_google("abc", AGNO_GOOGLE_LLM_PROVIDER) is False
    assert agno_is_google(AGNO_FRAMEWORK_PROVIDER, AGNO_GOOGLE_LLM_PROVIDER) is True


def test_agno_is_xai():
    assert agno_is_xai("abc", "def") is False
    assert agno_is_xai(AGNO_FRAMEWORK_PROVIDER, "def") is False
    assert agno_is_xai("abc", AGNO_XAI_LLM_PROVIDER) is False
    assert agno_is_xai(AGNO_FRAMEWORK_PROVIDER, AGNO_XAI_LLM_PROVIDER) is True
