from memori.llm.adapters.openai._adapter import Adapter


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
