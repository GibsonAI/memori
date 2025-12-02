from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from memori._config import Config
from memori.llm._xai_wrappers import XAiWrappers


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def xai_wrappers(config):
    return XAiWrappers(config)


def test_inject_conversation_history_no_conversation_id(xai_wrappers):
    kwargs = {"messages": ["msg1", "msg2"]}
    result = xai_wrappers.inject_conversation_history(kwargs)
    assert result == {"messages": ["msg1", "msg2"]}


def test_inject_conversation_history_empty_messages(xai_wrappers, config, mocker):
    config.cache.conversation_id = "conv123"
    mock_driver = mocker.MagicMock()
    mock_driver.conversation.messages.read.return_value = []
    mock_storage = mocker.MagicMock()
    mock_storage.driver = mock_driver
    config.storage = mock_storage

    kwargs = {"messages": ["msg1"]}
    result = xai_wrappers.inject_conversation_history(kwargs)

    mock_driver.conversation.messages.read.assert_called_once_with("conv123")
    assert result == {"messages": ["msg1"]}


def test_inject_conversation_history_with_user_messages(xai_wrappers, config, mocker):
    with (
        patch("xai_sdk.chat.user") as mock_user,
        patch("xai_sdk.chat.assistant"),
    ):
        config.cache.conversation_id = "conv123"
        mock_driver = mocker.MagicMock()
        mock_driver.conversation.messages.read.return_value = [
            {"role": "user", "content": "Hello"}
        ]
        mock_storage = mocker.MagicMock()
        mock_storage.driver = mock_driver
        config.storage = mock_storage

        mock_user.return_value = "user_msg"
        kwargs = {"messages": ["new_msg"]}
        result = xai_wrappers.inject_conversation_history(kwargs)

        mock_driver.conversation.messages.read.assert_called_once_with("conv123")
        mock_user.assert_called_once_with("Hello")
        assert result == {"messages": ["user_msg", "new_msg"]}


def test_inject_conversation_history_with_assistant_messages(
    xai_wrappers, config, mocker
):
    with (
        patch("xai_sdk.chat.user"),
        patch("xai_sdk.chat.assistant") as mock_assistant,
    ):
        config.cache.conversation_id = "conv123"
        mock_driver = mocker.MagicMock()
        mock_driver.conversation.messages.read.return_value = [
            {"role": "assistant", "content": "Hi there"}
        ]
        mock_storage = mocker.MagicMock()
        mock_storage.driver = mock_driver
        config.storage = mock_storage

        mock_assistant.return_value = "assistant_msg"
        kwargs = {"messages": ["new_msg"]}
        result = xai_wrappers.inject_conversation_history(kwargs)

        mock_driver.conversation.messages.read.assert_called_once_with("conv123")
        mock_assistant.assert_called_once_with("Hi there")
        assert result == {"messages": ["assistant_msg", "new_msg"]}


def test_inject_conversation_history_with_multiple_messages(
    xai_wrappers, config, mocker
):
    with (
        patch("xai_sdk.chat.user") as mock_user,
        patch("xai_sdk.chat.assistant") as mock_assistant,
    ):
        config.cache.conversation_id = "conv123"
        mock_driver = mocker.MagicMock()
        mock_driver.conversation.messages.read.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
        ]
        mock_storage = mocker.MagicMock()
        mock_storage.driver = mock_driver
        config.storage = mock_storage

        mock_user.side_effect = ["user_msg1", "user_msg2"]
        mock_assistant.return_value = "assistant_msg"
        kwargs = {"messages": ["new_msg"]}
        result = xai_wrappers.inject_conversation_history(kwargs)

        assert result == {
            "messages": ["user_msg1", "assistant_msg", "user_msg2", "new_msg"]
        }


def test_inject_conversation_history_ignores_unknown_roles(
    xai_wrappers, config, mocker
):
    with (
        patch("xai_sdk.chat.user") as mock_user,
        patch("xai_sdk.chat.assistant"),
    ):
        config.cache.conversation_id = "conv123"
        mock_driver = mocker.MagicMock()
        mock_driver.conversation.messages.read.return_value = [
            {"role": "system", "content": "ignored"},
            {"role": "user", "content": "Hello"},
        ]
        mock_storage = mocker.MagicMock()
        mock_storage.driver = mock_driver
        config.storage = mock_storage

        mock_user.return_value = "user_msg"
        kwargs = {"messages": ["new_msg"]}
        result = xai_wrappers.inject_conversation_history(kwargs)

        assert result == {"messages": ["user_msg", "new_msg"]}


def test_wrap_chat_methods_already_installed(xai_wrappers):
    chat_obj = MagicMock()
    chat_obj._memori_installed = True
    original_sample = chat_obj.sample

    xai_wrappers.wrap_chat_methods(chat_obj, "1.0.0")

    assert chat_obj.sample == original_sample


def test_wrap_chat_methods_sync(xai_wrappers):
    chat_obj = MagicMock()
    chat_obj.sample = MagicMock()
    del chat_obj._memori_installed

    xai_wrappers.wrap_chat_methods(chat_obj, "1.0.0")

    assert hasattr(chat_obj, "_sample")
    assert hasattr(chat_obj, "_memori_installed")
    assert chat_obj._memori_installed is True


def test_wrap_chat_methods_async(xai_wrappers):
    chat_obj = MagicMock()
    chat_obj.sample = AsyncMock()
    del chat_obj._memori_installed

    xai_wrappers.wrap_chat_methods(chat_obj, "1.0.0")

    assert hasattr(chat_obj, "_sample")
    assert hasattr(chat_obj, "_memori_installed")
    assert chat_obj._memori_installed is True


def test_wrap_chat_methods_with_stream(xai_wrappers):
    chat_obj = MagicMock()
    chat_obj.sample = MagicMock()
    chat_obj.stream = MagicMock()
    del chat_obj._memori_installed

    xai_wrappers.wrap_chat_methods(chat_obj, "1.0.0")

    assert hasattr(chat_obj, "_stream")
    assert hasattr(chat_obj, "_memori_installed")


def test_normalize_role_assistant(xai_wrappers):
    response = MagicMock()
    response.role.name = "ROLE_ASSISTANT"

    assert xai_wrappers._normalize_role(response) == "assistant"


def test_normalize_role_user(xai_wrappers):
    response = MagicMock()
    response.role.name = "ROLE_USER"

    assert xai_wrappers._normalize_role(response) == "user"


def test_normalize_role_system(xai_wrappers):
    response = MagicMock()
    response.role.name = "ROLE_SYSTEM"

    assert xai_wrappers._normalize_role(response) == "system"


def test_normalize_role_unknown(xai_wrappers):
    response = MagicMock()
    response.role.name = "ROLE_CUSTOM"

    assert xai_wrappers._normalize_role(response) == "custom"


def test_normalize_role_without_name_attr(xai_wrappers):
    response = MagicMock()
    mock_role = MagicMock()
    mock_role.__str__ = lambda self: "ROLE_ASSISTANT"
    del mock_role.name
    response.role = mock_role

    assert xai_wrappers._normalize_role(response) == "assistant"


def test_build_payload(xai_wrappers, config):
    query_formatted = {"messages": [{"role": "user", "content": "Hello"}]}
    response_json = {"content": "Hi", "role": "assistant"}
    client_version = "1.0.0"
    start_time = 1234567890.0

    payload = xai_wrappers._build_payload(
        query_formatted, response_json, client_version, start_time
    )

    assert payload["attribution"]["entity"]["id"] == config.entity_id
    assert payload["attribution"]["process"]["id"] == config.process_id
    assert payload["conversation"]["client"]["title"] == "xai"
    assert payload["conversation"]["client"]["version"] == "1.0.0"
    assert payload["conversation"]["query"] == query_formatted
    assert payload["conversation"]["response"] == response_json
    assert payload["meta"]["api"]["key"] == config.api_key
    assert payload["meta"]["fnfg"]["status"] == "succeeded"
    assert payload["session"]["uuid"] == str(config.session_id)
    assert payload["time"]["start"] == start_time
    assert "end" in payload["time"]


def test_create_sync_sample_wrapper(xai_wrappers, mocker):
    chat_obj = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Hello world"
    mock_response.role.name = "ROLE_ASSISTANT"
    chat_obj._sample = MagicMock(return_value=mock_response)
    chat_obj.messages = []

    mock_manager = mocker.patch("memori.memory._manager.Manager")

    wrapper = xai_wrappers._create_sync_sample_wrapper(chat_obj, "1.0.0")
    result = wrapper()

    assert result == mock_response
    chat_obj._sample.assert_called_once()
    mock_manager.assert_called_once()


@pytest.mark.asyncio
async def test_create_async_sample_wrapper(xai_wrappers, mocker):
    chat_obj = MagicMock()
    mock_response = MagicMock()
    mock_response.content = "Hello world"
    mock_response.role.name = "ROLE_ASSISTANT"
    chat_obj._sample = AsyncMock(return_value=mock_response)
    chat_obj.messages = []

    mock_manager = mocker.patch("memori.memory._manager.Manager")

    wrapper = xai_wrappers._create_async_sample_wrapper(chat_obj, "1.0.0")
    result = await wrapper()

    assert result == mock_response
    chat_obj._sample.assert_called_once()
    mock_manager.assert_called_once()


@pytest.mark.asyncio
async def test_create_stream_wrapper_with_tuple_items(xai_wrappers, mocker):
    chat_obj = MagicMock()
    mock_delta1 = MagicMock()
    mock_delta1.content = "Hello"
    mock_delta2 = MagicMock()
    mock_delta2.content = " world"
    mock_response = MagicMock()
    mock_response.role.name = "ROLE_ASSISTANT"

    async def mock_stream(*args, **kwargs):
        yield (mock_response, mock_delta1)
        yield (mock_response, mock_delta2)

    chat_obj._stream = mock_stream
    chat_obj.messages = []

    mock_manager = mocker.patch("memori.memory._manager.Manager")

    wrapper = xai_wrappers._create_stream_wrapper(chat_obj, "1.0.0")

    items = []
    async for item in wrapper():
        items.append(item)

    assert len(items) == 2
    mock_manager.assert_called_once()


@pytest.mark.asyncio
async def test_create_stream_wrapper_with_content_items(xai_wrappers, mocker):
    chat_obj = MagicMock()
    mock_item1 = MagicMock()
    mock_item1.content = "Hello"
    mock_item1.role.name = "ROLE_ASSISTANT"
    mock_item2 = MagicMock()
    mock_item2.content = " world"
    mock_item2.role.name = "ROLE_ASSISTANT"

    async def mock_stream(*args, **kwargs):
        yield mock_item1
        yield mock_item2

    chat_obj._stream = mock_stream
    chat_obj.messages = []

    mock_manager = mocker.patch("memori.memory._manager.Manager")

    wrapper = xai_wrappers._create_stream_wrapper(chat_obj, "1.0.0")

    items = []
    async for item in wrapper():
        items.append(item)

    assert len(items) == 2
    mock_manager.assert_called_once()


@pytest.mark.asyncio
async def test_create_stream_wrapper_without_content(xai_wrappers, mocker):
    chat_obj = MagicMock()
    mock_item = MagicMock(spec=[])

    async def mock_stream(*args, **kwargs):
        yield mock_item

    chat_obj._stream = mock_stream
    chat_obj.messages = []

    mock_manager = mocker.patch("memori.memory._manager.Manager")

    wrapper = xai_wrappers._create_stream_wrapper(chat_obj, "1.0.0")

    items = []
    async for item in wrapper():
        items.append(item)

    assert len(items) == 1
    mock_manager.assert_not_called()
