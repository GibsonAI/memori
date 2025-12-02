import json
from unittest.mock import Mock, patch

from memori._config import Config
from memori.llm._base import BaseInvoke, BaseLlmAdaptor
from memori.llm._constants import (
    LANGCHAIN_FRAMEWORK_PROVIDER,
    LANGCHAIN_OPENAI_LLM_PROVIDER,
    OPENAI_LLM_PROVIDER,
)
from tests.llm.unit_test_objects import UnitTestX, UnitTestY


def test_list_to_json_native_types():
    assert BaseInvoke(Config(), "abc").list_to_json([1, 2, 3]) == [1, 2, 3]

    assert BaseInvoke(Config(), "abc").list_to_json([{"a": "b"}, {"c": "d"}]) == [
        {"a": "b"},
        {"c": "d"},
    ]

    assert BaseInvoke(Config(), "abc").list_to_json([[1, 2], [3, 4], [{"a", "b"}]]) == [
        [1, 2],
        [3, 4],
        [{"a", "b"}],
    ]

    assert BaseInvoke(Config(), "abc").list_to_json(
        [[1, {"a": "b"}], [{"c": "d"}, 2]]
    ) == [
        [1, {"a": "b"}],
        [{"c": "d"}, 2],
    ]


def test_list_to_json_object_simple():
    assert BaseInvoke(Config(), "abc").list_to_json([1, UnitTestX()]) == [
        1,
        {"a": 1, "b": 2},
    ]


def test_list_to_json_object_complex():
    assert BaseInvoke(Config(), "abc").list_to_json([1, UnitTestY()]) == [
        1,
        {"c": 3, "d": {"a": 1, "b": 2}},
    ]


def test_list_to_json_list_list_list():
    assert BaseInvoke(Config(), "abc").list_to_json([1, [2, [3, [4]]]]) == [
        1,
        [2, [3, [4]]],
    ]


def test_list_to_dict_to_list():
    assert BaseInvoke(Config(), "abc").list_to_json([{"a": 1, "b": [1, [2]]}]) == [
        {"a": 1, "b": [1, [2]]}
    ]


def test_dict_to_json_dict():
    assert BaseInvoke(Config(), "abc").dict_to_json({"a": "b", "c": "d"}) == {
        "a": "b",
        "c": "d",
    }


def test_dist_to_json_dict_has_dict():
    assert BaseInvoke(Config(), "abc").dict_to_json(
        {"a": {"b": {"c": "d"}, "e": 123}}
    ) == {"a": {"b": {"c": "d"}, "e": 123}}


def test_configure_for_streaming_usage_openai():
    invoke = BaseInvoke(Config(), "abc")
    invoke.config.llm.provider = OPENAI_LLM_PROVIDER

    assert invoke.configure_for_streaming_usage({"abc": "def", "stream": True}) == {
        "abc": "def",
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    assert invoke.configure_for_streaming_usage(
        {"abc": "def", "stream": True, "stream_options": {}}
    ) == {"abc": "def", "stream": True, "stream_options": {"include_usage": True}}

    assert invoke.configure_for_streaming_usage(
        {"abc": "def", "stream": True, "stream_options": {"include_usage": False}}
    ) == {"abc": "def", "stream": True, "stream_options": {"include_usage": True}}


def test_configure_for_streaming_usage_streaming_options_is_not_dict_openai():
    invoke = BaseInvoke(Config(), "abc")
    invoke.config.llm.provider = OPENAI_LLM_PROVIDER

    assert invoke.configure_for_streaming_usage(
        {"abc": "def", "stream": True, "stream_options": 123}
    ) == {
        "abc": "def",
        "stream": True,
        "stream_options": {"include_usage": True},
    }


def test_configure_for_streaming_usage_only_if_stream_is_true_openai():
    invoke = BaseInvoke(Config(), "abc")
    invoke.config.llm.provider = OPENAI_LLM_PROVIDER

    assert invoke.configure_for_streaming_usage({"abc": "def"}) == {"abc": "def"}


def test_configure_for_streaming_usage_langchain_openai():
    invoke = BaseInvoke(Config(), "abc")
    invoke.config.framework.provider = LANGCHAIN_FRAMEWORK_PROVIDER
    invoke.config.llm.provider = OPENAI_LLM_PROVIDER

    assert invoke.configure_for_streaming_usage({"abc": "def", "stream": True}) == {
        "abc": "def",
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    assert invoke.configure_for_streaming_usage(
        {"abc": "def", "stream": True, "stream_options": {}}
    ) == {"abc": "def", "stream": True, "stream_options": {"include_usage": True}}

    assert invoke.configure_for_streaming_usage(
        {"abc": "def", "stream": True, "stream_options": {"include_usage": False}}
    ) == {"abc": "def", "stream": True, "stream_options": {"include_usage": True}}


def test_configure_for_streaming_usage_streaming_opts_is_not_dict_langchain_openai():
    invoke = BaseInvoke(Config(), "abc")
    invoke.config.framework.provider = LANGCHAIN_FRAMEWORK_PROVIDER
    invoke.config.llm.provider = LANGCHAIN_OPENAI_LLM_PROVIDER

    assert invoke.configure_for_streaming_usage(
        {"abc": "def", "stream": True, "stream_options": 123}
    ) == {
        "abc": "def",
        "stream": True,
        "stream_options": {"include_usage": True},
    }


def test_configure_for_streaming_usage_only_if_stream_is_true_langchain_openai():
    invoke = BaseInvoke(Config(), "abc")
    invoke.config.framework.provider = LANGCHAIN_FRAMEWORK_PROVIDER
    invoke.config.llm.provider = LANGCHAIN_OPENAI_LLM_PROVIDER

    assert invoke.configure_for_streaming_usage({"abc": "def"}) == {"abc": "def"}


def test_get_response_content():
    invoke = BaseInvoke(Config(), "abc")

    assert invoke.get_response_content({"abc": "def"}) == {"abc": "def"}

    class MockLegacyAPIResponse:
        def __init__(self):
            self.text = json.dumps({"abc": "def"})

    legacy_api_response = MockLegacyAPIResponse()
    legacy_api_response.__class__.__name__ = "LegacyAPIResponse"
    legacy_api_response.__class__.__module__ = "openai._legacy_response"

    assert invoke.get_response_content(legacy_api_response) == {"abc": "def"}


def test_exclude_injected_messages():
    adapter = BaseLlmAdaptor()

    # No injected count - returns all messages
    messages = [{"role": "user", "content": "Hello"}]
    payload = {"conversation": {"query": {}}}
    assert adapter._exclude_injected_messages(messages, payload) == messages

    # Injected count of 2 - slices off first 2 messages
    messages = [
        {"role": "user", "content": "injected 1"},
        {"role": "assistant", "content": "injected 2"},
        {"role": "user", "content": "new message"},
    ]
    payload = {"conversation": {"query": {"_memori_injected_count": 2}}}
    assert adapter._exclude_injected_messages(messages, payload) == [
        {"role": "user", "content": "new message"}
    ]

    # Safe navigation - missing keys don't cause errors
    assert adapter._exclude_injected_messages(messages, {}) == messages


def test_handle_post_response_without_augmentation():
    config = Config()
    invoke = BaseInvoke(config, "test_method")
    invoke.set_client("test_provider", "test_title", "1.0.0")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}
    start_time = 1234567890.0
    raw_response = {"choices": [{"message": {"content": "Hi"}}]}

    with patch("memori.memory._manager.Manager") as mock_memory_manager:
        mock_manager_instance = Mock()
        mock_memory_manager.return_value = mock_manager_instance

        invoke.handle_post_response(kwargs, start_time, raw_response)

        mock_memory_manager.assert_called_once_with(config)
        mock_manager_instance.execute.assert_called_once()


def test_handle_post_response_with_augmentation_no_conversation():
    config = Config()
    config.augmentation = Mock()
    config.entity_id = "test-entity"
    invoke = BaseInvoke(config, "test_method")
    invoke.set_client("test_provider", "test_title", "1.0.0")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}
    start_time = 1234567890.0
    raw_response = {"choices": [{"message": {"content": "Hi"}}]}

    with patch("memori.memory._manager.Manager") as mock_memory_manager:
        mock_manager_instance = Mock()
        mock_memory_manager.return_value = mock_manager_instance

        invoke.handle_post_response(kwargs, start_time, raw_response)

        mock_memory_manager.assert_called_once_with(config)
        mock_manager_instance.execute.assert_called_once()
        config.augmentation.enqueue.assert_called_once()
        call_args = config.augmentation.enqueue.call_args[0][0]
        assert call_args.conversation_id is None


def test_handle_post_response_with_augmentation_and_conversation():
    config = Config()
    config.augmentation = Mock()
    config.entity_id = "test-entity"
    config.cache.conversation_id = 123
    invoke = BaseInvoke(config, "test_method")
    invoke.set_client("test_provider", "test_title", "1.0.0")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}
    start_time = 1234567890.0
    raw_response = {"choices": [{"message": {"content": "Hi"}}]}

    with patch("memori.memory._manager.Manager") as mock_memory_manager:
        mock_manager_instance = Mock()
        mock_memory_manager.return_value = mock_manager_instance

        invoke.handle_post_response(kwargs, start_time, raw_response)

        mock_memory_manager.assert_called_once_with(config)
        mock_manager_instance.execute.assert_called_once()
        config.augmentation.enqueue.assert_called_once()
        call_args = config.augmentation.enqueue.call_args[0][0]
        assert call_args.conversation_id == 123


def test_extract_user_query_with_user_message():
    invoke = BaseInvoke(Config(), "test_method")
    kwargs = {
        "messages": [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "What is the weather?"},
        ]
    }
    assert invoke._extract_user_query(kwargs) == "What is the weather?"


def test_extract_user_query_with_multiple_user_messages():
    invoke = BaseInvoke(Config(), "test_method")
    kwargs = {
        "messages": [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Second question"},
        ]
    }
    assert invoke._extract_user_query(kwargs) == "Second question"


def test_extract_user_query_no_messages():
    invoke = BaseInvoke(Config(), "test_method")
    assert invoke._extract_user_query({}) == ""
    assert invoke._extract_user_query({"messages": []}) == ""


def test_extract_user_query_no_user_messages():
    invoke = BaseInvoke(Config(), "test_method")
    kwargs = {
        "messages": [
            {"role": "system", "content": "You are helpful"},
            {"role": "assistant", "content": "I can help"},
        ]
    }
    assert invoke._extract_user_query(kwargs) == ""


def test_inject_recalled_facts_no_storage():
    config = Config()
    config.storage = None
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}
    result = invoke.inject_recalled_facts(kwargs)

    assert result == kwargs


def test_inject_recalled_facts_no_entity_id():
    config = Config()
    config.storage = Mock()
    config.entity_id = None
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}
    result = invoke.inject_recalled_facts(kwargs)

    assert result == kwargs


def test_inject_recalled_facts_entity_create_returns_none():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = None
    config.entity_id = "test-entity"
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}
    result = invoke.inject_recalled_facts(kwargs)

    assert result == kwargs


def test_inject_recalled_facts_no_user_query():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = 1
    config.entity_id = "test-entity"
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "system", "content": "You are helpful"}]}
    result = invoke.inject_recalled_facts(kwargs)

    assert result == kwargs


def test_inject_recalled_facts_no_facts_found():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = 1
    config.entity_id = "test-entity"
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}

    with patch("memori.memory.recall.Recall") as mock_recall:
        mock_recall.return_value.search_facts.return_value = []
        result = invoke.inject_recalled_facts(kwargs)

    assert result == kwargs
    assert len(kwargs["messages"]) == 1


def test_inject_recalled_facts_no_relevant_facts():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = 1
    config.entity_id = "test-entity"
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}

    with patch("memori.memory.recall.Recall") as mock_recall:
        mock_recall.return_value.search_facts.return_value = [
            {"content": "Irrelevant fact", "similarity": 0.05}
        ]
        result = invoke.inject_recalled_facts(kwargs)

    assert result == kwargs
    assert len(kwargs["messages"]) == 1


def test_inject_recalled_facts_success():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = 1
    config.entity_id = "test-entity"
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "What do I like?"}]}

    with patch("memori.memory.recall.Recall") as mock_recall:
        mock_recall.return_value.search_facts.return_value = [
            {"content": "User likes pizza", "similarity": 0.9},
            {"content": "User likes coding", "similarity": 0.85},
        ]
        result = invoke.inject_recalled_facts(kwargs)

    assert len(result["messages"]) == 2
    assert result["messages"][0]["role"] == "system"
    assert "User likes pizza" in result["messages"][0]["content"]
    assert "User likes coding" in result["messages"][0]["content"]
    assert result["messages"][1]["role"] == "user"


def test_inject_recalled_facts_filters_by_relevance():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = 1
    config.entity_id = "test-entity"
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}

    with patch("memori.memory.recall.Recall") as mock_recall:
        mock_recall.return_value.search_facts.return_value = [
            {"content": "Relevant fact", "similarity": 0.9},
            {"content": "Irrelevant fact", "similarity": 0.05},
        ]
        result = invoke.inject_recalled_facts(kwargs)

    assert len(result["messages"]) == 2
    assert "Relevant fact" in result["messages"][0]["content"]
    assert "Irrelevant fact" not in result["messages"][0]["content"]


def test_inject_recalled_facts_extends_existing_system_message():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = 1
    config.entity_id = "test-entity"
    invoke = BaseInvoke(config, "test_method")

    kwargs = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What do I like?"},
        ]
    }

    with patch("memori.memory.recall.Recall") as mock_recall:
        mock_recall.return_value.search_facts.return_value = [
            {"content": "User likes pizza", "similarity": 0.9},
        ]
        result = invoke.inject_recalled_facts(kwargs)

    # Should still have 2 messages (not 3)
    assert len(result["messages"]) == 2
    # First message should still be system role
    assert result["messages"][0]["role"] == "system"
    # System message should contain both original content and recalled facts
    assert "You are a helpful assistant." in result["messages"][0]["content"]
    assert "User likes pizza" in result["messages"][0]["content"]
    assert "Relevant context about the user" in result["messages"][0]["content"]


def test_inject_recalled_facts_creates_system_message_when_none_exists():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = 1
    config.entity_id = "test-entity"
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "What do I like?"}]}

    with patch("memori.memory.recall.Recall") as mock_recall:
        mock_recall.return_value.search_facts.return_value = [
            {"content": "User likes pizza", "similarity": 0.9},
        ]
        result = invoke.inject_recalled_facts(kwargs)

    # Should have 2 messages now (system + user)
    assert len(result["messages"]) == 2
    # First message should be system role
    assert result["messages"][0]["role"] == "system"
    # System message should contain recalled facts
    assert "User likes pizza" in result["messages"][0]["content"]
    assert "Relevant context about the user" in result["messages"][0]["content"]


def test_inject_conversation_messages_no_conversation_id():
    config = Config()
    config.cache.conversation_id = None
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}
    result = invoke.inject_conversation_messages(kwargs)

    assert result == kwargs


def test_inject_conversation_messages_no_storage():
    config = Config()
    config.cache.conversation_id = 123
    config.storage = None
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}
    result = invoke.inject_conversation_messages(kwargs)

    assert result == kwargs


def test_inject_conversation_messages_no_messages():
    config = Config()
    config.cache.conversation_id = 123
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.conversation.messages.read.return_value = []
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "Hello"}]}
    result = invoke.inject_conversation_messages(kwargs)

    assert result == kwargs
    assert invoke._injected_message_count == 0


def test_inject_conversation_messages_openai_success():
    config = Config()
    config.cache.conversation_id = 123
    config.llm.provider = OPENAI_LLM_PROVIDER
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.conversation.messages.read.return_value = [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"},
    ]
    invoke = BaseInvoke(config, "test_method")

    kwargs = {"messages": [{"role": "user", "content": "New question"}]}
    result = invoke.inject_conversation_messages(kwargs)

    assert len(result["messages"]) == 3
    assert result["messages"][0]["content"] == "Previous question"
    assert result["messages"][1]["content"] == "Previous answer"
    assert result["messages"][2]["content"] == "New question"
    assert invoke._injected_message_count == 2
