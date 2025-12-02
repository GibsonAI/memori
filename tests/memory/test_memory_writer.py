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
