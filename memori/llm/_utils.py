r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from memori.llm._constants import (
    ATHROPIC_LLM_PROVIDER,
    GOOGLE_LLM_PROVIDER,
    LANGCHAIN_CHATBEDROCK_LLM_PROVIDER,
    LANGCHAIN_CHATGOOGLEGENAI_LLM_PROVIDER,
    LANGCHAIN_CHATVERTEXAI_LLM_PROVIDER,
    LANGCHAIN_FRAMEWORK_PROVIDER,
    LANGCHAIN_OPENAI_LLM_PROVIDER,
    OPENAI_LLM_PROVIDER,
    XAI_LLM_PROVIDER,
)


def client_is_bedrock(provider, title):
    return (
        provider_is_langchain(provider) and title == LANGCHAIN_CHATBEDROCK_LLM_PROVIDER
    )


def llm_is_anthropic(provider, title):
    return title == ATHROPIC_LLM_PROVIDER


def llm_is_bedrock(provider, title):
    return (
        provider_is_langchain(provider) and title == LANGCHAIN_CHATBEDROCK_LLM_PROVIDER
    )


def llm_is_google(provider, title):
    return title == GOOGLE_LLM_PROVIDER or (
        provider_is_langchain(provider)
        and title
        in [LANGCHAIN_CHATGOOGLEGENAI_LLM_PROVIDER, LANGCHAIN_CHATVERTEXAI_LLM_PROVIDER]
    )


def llm_is_openai(provider, title):
    return title == OPENAI_LLM_PROVIDER or (
        provider_is_langchain(provider) and title == LANGCHAIN_OPENAI_LLM_PROVIDER
    )


def llm_is_xai(provider, title):
    return title == XAI_LLM_PROVIDER


def provider_is_langchain(provider):
    return provider == LANGCHAIN_FRAMEWORK_PROVIDER
