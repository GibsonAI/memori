from unittest.mock import MagicMock, patch

import pytest

from memori._config import Config
from memori.llm._base import BaseInvoke
from memori.llm.adapters.openai._adapter import Adapter
from memori.llm.helpers.query_extraction import extract_user_query
from memori.llm.invoke.invoke import Invoke, InvokeAsync
from memori.llm.invoke.iterator import AsyncIterator, Iterator
from memori.llm.pipelines.conversation_injection import inject_conversation_messages
from memori.llm.pipelines.recall_injection import inject_recalled_facts


class MockEvent:
    def __init__(self, event_type: str, response=None):
        self.type = event_type
        if response is not None:
            self.response = response


class MockResponse:
    def __init__(self, output_text: str):
        self.output_text = output_text
        self.output = [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": output_text}],
            }
        ]

    def model_dump(self):
        return {"output_text": self.output_text, "output": self.output}


class MockResponsesResponse:
    def __init__(self):
        self.output = []
        self.output_text = "Test response"

    def model_dump(self):
        return {"output": self.output, "output_text": self.output_text}


def test_get_formatted_query():
    assert Adapter().get_formatted_query({}) == []
    assert Adapter().get_formatted_query({"conversation": {"query": {}}}) == []

    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "messages": [
                        {"content": "abc", "role": "user"},
                        {"content": "def", "role": "assistant"},
                    ]
                }
            }
        }
    ) == [{"content": "abc", "role": "user"}, {"content": "def", "role": "assistant"}]


def test_get_formatted_response_streamed():
    assert Adapter().get_formatted_response({}) == []
    assert Adapter().get_formatted_query({"conversation": {"response": {}}}) == []

    assert Adapter().get_formatted_response(
        {
            "conversation": {
                "query": {"stream": True},
                "response": {
                    "choices": [
                        {
                            "delta": {
                                "content": "abc",
                                "role": "assistant",
                            }
                        },
                        {
                            "delta": {
                                "content": "def",
                                "role": "assistant",
                            }
                        },
                    ]
                },
            }
        }
    ) == [{"role": "assistant", "text": "abcdef", "type": "text"}]


def test_get_formatted_response_unstreamed():
    assert Adapter().get_formatted_response({}) == []
    assert Adapter().get_formatted_query({"conversation": {"response": {}}}) == []

    assert Adapter().get_formatted_response(
        {
            "conversation": {
                "query": {},
                "response": {
                    "choices": [
                        {"message": {"content": "abc", "role": "assistant"}},
                        {"message": {"content": "def", "role": "assistant"}},
                    ]
                },
            }
        }
    ) == [
        {"role": "assistant", "text": "abc", "type": "text"},
        {"role": "assistant", "text": "def", "type": "text"},
    ]


def test_get_formatted_query_with_injected_messages():
    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "_memori_injected_count": 2,
                    "messages": [
                        {"content": "injected 1", "role": "user"},
                        {"content": "injected 2", "role": "assistant"},
                        {"content": "new message", "role": "user"},
                        {"content": "new response", "role": "assistant"},
                    ],
                }
            }
        }
    ) == [
        {"content": "new message", "role": "user"},
        {"content": "new response", "role": "assistant"},
    ]


def test_responses_get_formatted_query_string_input():
    payload = {
        "conversation": {
            "query": {
                "input": "Hello, how are you?",
                "instructions": "You are a helpful assistant.",
            }
        }
    }
    result = Adapter().get_formatted_query(payload)
    assert len(result) == 2
    assert result[0] == {"role": "system", "content": "You are a helpful assistant."}
    assert result[1] == {"role": "user", "content": "Hello, how are you?"}


def test_responses_get_formatted_query_list_input():
    payload = {
        "conversation": {
            "query": {
                "input": [
                    {"role": "user", "content": "First message"},
                    {"role": "assistant", "content": "First response"},
                    {"role": "user", "content": "Second message"},
                ]
            }
        }
    }
    result = Adapter().get_formatted_query(payload)
    assert len(result) == 3
    assert result[0] == {"role": "user", "content": "First message"}


def test_responses_get_formatted_query_strips_memori_context():
    payload = {
        "conversation": {
            "query": {
                "input": "Hello",
                "instructions": "Be helpful.\n\n<memori_context>\nUser likes cats.\n</memori_context>",
            }
        }
    }
    result = Adapter().get_formatted_query(payload)
    assert len(result) == 2
    assert result[0]["content"] == "Be helpful."


def test_responses_get_formatted_query_with_injected_messages():
    payload = {
        "conversation": {
            "query": {
                "_memori_injected_count": 2,
                "input": [
                    {"role": "user", "content": "Injected 1"},
                    {"role": "assistant", "content": "Injected 2"},
                    {"role": "user", "content": "Actual query"},
                ],
            }
        }
    }
    result = Adapter().get_formatted_query(payload)
    assert len(result) == 1
    assert result[0] == {"role": "user", "content": "Actual query"}


def test_responses_get_formatted_response_with_output_message():
    payload = {
        "conversation": {
            "query": {},
            "response": {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Hello!"}],
                    }
                ]
            },
        }
    }
    result = Adapter().get_formatted_response(payload)
    assert len(result) == 1
    assert result[0] == {"role": "assistant", "text": "Hello!", "type": "text"}


def test_responses_get_formatted_response_fallback_to_output_text():
    payload = {
        "conversation": {
            "query": {},
            "response": {"output": [], "output_text": "Fallback text"},
        }
    }
    result = Adapter().get_formatted_response(payload)
    assert len(result) == 1
    assert result[0] == {"role": "assistant", "text": "Fallback text", "type": "text"}


def test_iterator_iter_returns_self():
    config = Config()
    iterator = Iterator(config, iter([]))
    assert iterator.__iter__() is iterator


@patch("memori.llm.invoke.iterator.run_post_invoke")
@patch("memori.llm.invoke.iterator.format_payload", return_value={})
def test_iterator_yields_all_events(mock_format_payload, mock_run_post_invoke):
    config = Config()
    events = [
        MockEvent("response.created"),
        MockEvent("response.completed", MockResponse("Hello")),
    ]
    iterator = Iterator(config, iter(events))

    mock_invoke = MagicMock()
    mock_invoke._uses_protobuf = False
    mock_invoke._injected_message_count = 0
    mock_invoke._format_payload.return_value = {}
    mock_invoke._format_kwargs.return_value = {}
    mock_invoke._format_response.return_value = {}
    iterator.configure_invoke(mock_invoke)
    iterator.configure_request({"input": "test"}, 0)

    collected = list(iterator)
    assert len(collected) == 2


@patch("memori.llm.invoke.iterator.run_post_invoke")
@patch("memori.llm.invoke.iterator.format_payload", return_value={})
def test_iterator_captures_response_on_completed_event(
    mock_format_payload, mock_run_post_invoke
):
    config = Config()
    mock_response = MockResponse("Test output")
    events = [MockEvent("response.completed", mock_response)]
    iterator = Iterator(config, iter(events))

    mock_invoke = MagicMock()
    mock_invoke._uses_protobuf = False
    mock_invoke._injected_message_count = 0
    mock_invoke._format_payload.return_value = {}
    mock_invoke._format_kwargs.return_value = {}
    mock_invoke._format_response.return_value = {}
    iterator.configure_invoke(mock_invoke)
    iterator.configure_request({"input": "test"}, 0)

    list(iterator)
    assert iterator.raw_response == mock_response.model_dump()


def test_async_iterator_aiter_returns_self():
    config = Config()
    mock_source = MagicMock()
    mock_source.__aiter__.return_value = mock_source
    iterator = AsyncIterator(config, mock_source)
    assert iterator.__aiter__() is iterator


@pytest.mark.asyncio
@patch("memori.llm.invoke.iterator.run_post_invoke")
@patch("memori.llm.invoke.iterator.format_payload", return_value={})
async def test_async_iterator_yields_all_events(
    mock_format_payload, mock_run_post_invoke
):
    config = Config()
    events = [
        MockEvent("response.created"),
        MockEvent("response.completed", MockResponse("Hello")),
    ]

    async def async_gen():
        for event in events:
            yield event

    iterator = AsyncIterator(config, async_gen())

    mock_invoke = MagicMock()
    mock_invoke._uses_protobuf = False
    mock_invoke._injected_message_count = 0
    mock_invoke._format_payload.return_value = {}
    mock_invoke._format_kwargs.return_value = {}
    mock_invoke._format_response.return_value = {}
    iterator.configure_invoke(mock_invoke)
    iterator.configure_request({"input": "test"}, 0)
    iterator.__aiter__()

    collected = []
    async for event in iterator:
        collected.append(event)
    assert len(collected) == 2


@pytest.mark.asyncio
async def test_async_iterator_raises_runtime_error_if_not_initialized():
    config = Config()
    iterator = AsyncIterator(config, MagicMock())
    with pytest.raises(RuntimeError, match="Iterator not initialized"):
        await iterator.__anext__()


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"input": "What is 2+2?"}, "What is 2+2?"),
        (
            {
                "input": [
                    {"role": "user", "content": "First"},
                    {"role": "user", "content": "Second"},
                ]
            },
            "Second",
        ),
        ({}, ""),
    ],
)
def test_extract_user_query(kwargs, expected):
    assert extract_user_query(kwargs) == expected


def test_inject_recalled_facts_returns_kwargs_when_no_storage():
    config = Config()
    config.storage = None
    invoke = BaseInvoke(config, lambda **kwargs: None)
    kwargs = {"input": "test", "instructions": "Be helpful"}
    assert inject_recalled_facts(invoke, kwargs) == kwargs


def test_inject_recalled_facts_appends_facts_to_instructions():
    config = Config()
    config.storage = MagicMock()
    config.storage.driver = MagicMock()
    config.storage.driver.entity.create.return_value = 1
    config.entity_id = "test-entity"
    config.recall_relevance_threshold = 0.1
    config.llm.provider = "openai_responses"

    invoke = BaseInvoke(config, lambda **kwargs: None)
    invoke.set_client(None, "openai_responses", "1.0.0")

    mock_facts = [{"content": "User likes Python", "similarity": 0.8}]

    with patch("memori.memory.recall.Recall") as MockRecall:
        MockRecall.return_value.search_facts.return_value = mock_facts
        kwargs = {"input": "Test", "instructions": "Be helpful."}
        result = inject_recalled_facts(invoke, kwargs)
        assert "<memori_context>" in result["instructions"]
        assert "User likes Python" in result["instructions"]


def test_inject_conversation_messages_returns_kwargs_when_no_conversation_id():
    config = Config()
    config.cache.conversation_id = None
    invoke = BaseInvoke(config, lambda **kwargs: None)
    kwargs = {"input": "test"}
    assert inject_conversation_messages(invoke, kwargs) == kwargs


def test_inject_conversation_messages_converts_string_input_to_list():
    config = Config()
    config.cache.conversation_id = 1
    config.storage = MagicMock()
    config.storage.driver = MagicMock()
    config.storage.driver.conversation.messages.read.return_value = [
        {"role": "user", "content": "Previous"},
    ]
    config.llm.provider = "openai_responses"

    invoke = BaseInvoke(config, lambda **kwargs: None)
    invoke.set_client(None, "openai_responses", "1.0.0")

    result = inject_conversation_messages(invoke, {"input": "New"})
    assert isinstance(result["input"], list)
    assert len(result["input"]) == 2


def test_invoke_calls_method():
    config = Config()
    config.storage = None

    mock_response = MockResponsesResponse()
    mock_method = MagicMock(return_value=mock_response)

    invoke = Invoke(config, mock_method)
    invoke.set_client(None, "openai_responses", "1.0.0")

    result = invoke.invoke(model="gpt-4o", input="test")
    mock_method.assert_called_once()
    assert result == mock_response


@pytest.mark.asyncio
async def test_async_invoke_calls_method():
    config = Config()
    config.storage = None

    mock_response = MockResponsesResponse()

    async def mock_method(**kwargs):
        return mock_response

    invoke = InvokeAsync(config, mock_method)
    invoke.set_client(None, "openai_responses", "1.0.0")

    result = await invoke.invoke(model="gpt-4o", input="test")
    assert result == mock_response
