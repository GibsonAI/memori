from memori.llm._constants import OPENAI_LLM_PROVIDER
from memori.memory._writer import Writer


def test_execute(config, mocker):
    mock_messages = [
        {"role": "user", "content": "abc"},
        {"role": "assistant", "content": "def"},
        {"role": "assistant", "content": "ghi"},
    ]
    config.storage.adapter.execute.return_value.mappings.return_value.fetchall.return_value = mock_messages

    Writer(config).execute(
        {
            "conversation": {
                "client": {"provider": None, "title": OPENAI_LLM_PROVIDER},
                "query": {"messages": [{"content": "abc", "role": "user"}]},
                "response": {
                    "choices": [
                        {"message": {"content": "def", "role": "assistant"}},
                        {"message": {"content": "ghi", "role": "assistant"}},
                    ]
                },
            }
        }
    )

    assert config.cache.session_id is not None
    assert config.cache.conversation_id is not None

    assert config.storage.driver.session.create.called
    assert config.storage.driver.conversation.create.called
    assert config.storage.driver.conversation.message.create.call_count == 3

    calls = config.storage.driver.conversation.message.create.call_args_list
    assert calls[0][0][1] == "user"
    assert calls[0][0][3] == "abc"
    assert calls[1][0][1] == "assistant"
    assert calls[1][0][3] == "def"
    assert calls[2][0][1] == "assistant"
    assert calls[2][0][3] == "ghi"


def test_execute_with_entity_and_process(config, mocker):
    config.entity_id = "123"
    config.process_id = "456"

    mock_messages = [
        {"role": "user", "content": "abc"},
        {"role": "assistant", "content": "def"},
        {"role": "assistant", "content": "ghi"},
    ]
    config.storage.adapter.execute.return_value.mappings.return_value.fetchall.return_value = mock_messages
    config.storage.adapter.execute.return_value.mappings.return_value.fetchone.return_value = {
        "external_id": "123"
    }

    Writer(config).execute(
        {
            "conversation": {
                "client": {"provider": None, "title": OPENAI_LLM_PROVIDER},
                "query": {"messages": [{"content": "abc", "role": "user"}]},
                "response": {
                    "choices": [
                        {"message": {"content": "def", "role": "assistant"}},
                        {"message": {"content": "ghi", "role": "assistant"}},
                    ]
                },
            }
        }
    )

    assert config.cache.entity_id is not None
    assert config.cache.process_id is not None
    assert config.cache.session_id is not None
    assert config.cache.conversation_id is not None

    assert config.storage.driver.entity.create.called
    assert config.storage.driver.entity.create.call_args[0][0] == "123"

    assert config.storage.driver.process.create.called
    assert config.storage.driver.process.create.call_args[0][0] == "456"

    assert config.storage.driver.session.create.called
    session_call_args = config.storage.driver.session.create.call_args[0]
    assert session_call_args[1] == config.cache.entity_id
    assert session_call_args[2] == config.cache.process_id

    assert config.storage.driver.conversation.message.create.call_count == 3


def test_execute_skips_system_messages(config, mocker):
    mock_messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    config.storage.adapter.execute.return_value.mappings.return_value.fetchall.return_value = mock_messages

    Writer(config).execute(
        {
            "conversation": {
                "client": {"provider": None, "title": OPENAI_LLM_PROVIDER},
                "query": {
                    "messages": [
                        {"content": "You are a helpful assistant", "role": "system"},
                        {"content": "Hello", "role": "user"},
                    ]
                },
                "response": {
                    "choices": [
                        {"message": {"content": "Hi there!", "role": "assistant"}}
                    ]
                },
            }
        }
    )

    assert config.storage.driver.conversation.message.create.call_count == 2

    calls = config.storage.driver.conversation.message.create.call_args_list
    assert calls[0][0][1] == "user"
    assert calls[0][0][3] == "Hello"
    assert calls[1][0][1] == "assistant"
    assert calls[1][0][3] == "Hi there!"


def test_execute_multiple_turns_ingests_all_messages(config, mocker):
    """Test that multiple conversation turns properly ingest all user and assistant messages."""
    from unittest.mock import Mock

    # Mock the conversation.create to return a consistent conversation_id
    conversation_id = 123
    config.storage.driver.conversation.create.return_value = conversation_id
    config.cache.conversation_id = None  # Start with no conversation_id

    # First turn: user message + assistant response
    mock_messages_turn1 = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    config.storage.adapter.execute.return_value.mappings.return_value.fetchall.return_value = (
        mock_messages_turn1
    )

    payload_turn1 = {
        "conversation": {
            "client": {"provider": None, "title": OPENAI_LLM_PROVIDER},
            "query": {"messages": [{"content": "Hello", "role": "user"}]},
            "response": {
                "choices": [{"message": {"content": "Hi there!", "role": "assistant"}}]
            },
        }
    }

    Writer(config).execute(payload_turn1)

    # Verify first turn was written
    assert config.cache.conversation_id == conversation_id
    assert config.storage.driver.conversation.message.create.call_count == 2

    calls_turn1 = config.storage.driver.conversation.message.create.call_args_list
    assert calls_turn1[0][0][1] == "user"
    assert calls_turn1[0][0][3] == "Hello"
    assert calls_turn1[1][0][1] == "assistant"
    assert calls_turn1[1][0][3] == "Hi there!"

    # Reset mocks for second turn
    config.storage.driver.conversation.message.create.reset_mock()

    # Second turn: new user message + assistant response
    # The conversation should have previous messages injected, but only new messages should be written
    mock_messages_turn2 = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "What's the weather?"},
        {"role": "assistant", "content": "I don't have access to weather data."},
    ]
    config.storage.adapter.execute.return_value.mappings.return_value.fetchall.return_value = (
        mock_messages_turn2
    )

    # Simulate that previous messages were injected (so they're excluded from writing)
    payload_turn2 = {
        "conversation": {
            "client": {"provider": None, "title": OPENAI_LLM_PROVIDER},
            "query": {
                "messages": [
                    {"content": "Hello", "role": "user"},
                    {"content": "Hi there!", "role": "assistant"},
                    {"content": "What's the weather?", "role": "user"},
                ],
                "_memori_injected_count": 2,  # First 2 messages were injected
            },
            "response": {
                "choices": [
                    {
                        "message": {
                            "content": "I don't have access to weather data.",
                            "role": "assistant",
                        }
                    }
                ]
            },
        }
    }

    Writer(config).execute(payload_turn2)

    # Verify second turn was written (only new messages, not injected ones)
    assert config.cache.conversation_id == conversation_id
    assert config.storage.driver.conversation.message.create.call_count == 2

    calls_turn2 = config.storage.driver.conversation.message.create.call_args_list
    assert calls_turn2[0][0][1] == "user"
    assert calls_turn2[0][0][3] == "What's the weather?"
    assert calls_turn2[1][0][1] == "assistant"
    assert calls_turn2[1][0][3] == "I don't have access to weather data."
