from memori._config import Config
from memori.llm._base import BaseInvoke


def test_extract_system_prompt_with_memori_context():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [
        {
            "role": "system",
            "content": "You are a helpful assistant.\n\n<memori_context>\nRelevant context\n</memori_context>",
        },
        {"role": "user", "content": "Hello"},
    ]

    result = invoke._extract_system_prompt(messages)
    assert result == "You are a helpful assistant."


def test_extract_system_prompt_without_memori_context():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
    ]

    result = invoke._extract_system_prompt(messages)
    assert result == "You are a helpful assistant."


def test_extract_system_prompt_no_system_message():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [{"role": "user", "content": "Hello"}]

    result = invoke._extract_system_prompt(messages)
    assert result is None


def test_extract_system_prompt_empty_messages():
    invoke = BaseInvoke(Config(), "test_method")
    result = invoke._extract_system_prompt([])
    assert result is None


def test_extract_system_prompt_not_list():
    invoke = BaseInvoke(Config(), "test_method")
    result = invoke._extract_system_prompt(None)
    assert result is None


def test_extract_system_prompt_empty_content():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [{"role": "system", "content": ""}, {"role": "user", "content": "Hello"}]

    result = invoke._extract_system_prompt(messages)
    assert result is None


def test_extract_system_prompt_only_memori_context():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [
        {
            "role": "system",
            "content": "<memori_context>\nRelevant context\n</memori_context>",
        },
        {"role": "user", "content": "Hello"},
    ]

    result = invoke._extract_system_prompt(messages)
    assert result is None


def test_strip_memori_context_from_messages():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [
        {
            "role": "system",
            "content": "You are helpful.\n\n<memori_context>\nContext\n</memori_context>",
        },
        {"role": "user", "content": "Hello"},
    ]

    result = invoke._strip_memori_context_from_messages(messages)
    assert len(result) == 2
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "You are helpful."
    assert result[1]["role"] == "user"


def test_strip_memori_context_removes_message_if_only_context():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [
        {
            "role": "system",
            "content": "<memori_context>\nContext only\n</memori_context>",
        },
        {"role": "user", "content": "Hello"},
    ]

    result = invoke._strip_memori_context_from_messages(messages)
    assert len(result) == 1
    assert result[0]["role"] == "user"


def test_strip_memori_context_preserves_messages_without_context():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]

    result = invoke._strip_memori_context_from_messages(messages)
    assert len(result) == 3
    assert result == messages


def test_strip_memori_context_empty_messages():
    invoke = BaseInvoke(Config(), "test_method")
    result = invoke._strip_memori_context_from_messages([])
    assert result == []


def test_strip_memori_context_handles_non_dict_messages():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [{"role": "user", "content": "Hello"}, "invalid_message"]

    result = invoke._strip_memori_context_from_messages(messages)
    assert len(result) == 2
    assert result[1] == "invalid_message"


def test_strip_memori_context_multiple_system_messages():
    invoke = BaseInvoke(Config(), "test_method")
    messages = [
        {
            "role": "system",
            "content": "First system.\n\n<memori_context>\nContext\n</memori_context>",
        },
        {"role": "user", "content": "Hello"},
        {"role": "system", "content": "Second system."},
    ]

    result = invoke._strip_memori_context_from_messages(messages)
    assert len(result) == 3
    assert result[0]["content"] == "First system."
    assert result[2]["content"] == "Second system."
