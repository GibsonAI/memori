from memori.llm.adapters.bedrock._adapter import Adapter


def test_get_formatted_query():
    assert Adapter().get_formatted_query({}) == []
    assert Adapter().get_formatted_query({"conversation": {"query": {}}}) == []

    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "body": {
                        "messages": [
                            {"content": "abc", "role": "user"},
                            {"content": "def", "role": "system"},
                        ]
                    }
                }
            }
        }
    ) == [{"content": "abc", "role": "user"}, {"content": "def", "role": "system"}]


def test_get_formatted_response_streamed():
    assert Adapter().get_formatted_response({}) == []
    assert Adapter().get_formatted_query({"conversation": {"response": {}}}) == []

    assert Adapter().get_formatted_response(
        {
            "conversation": {
                "response": [
                    {"chunk": {"bytes": {"message": {"role": "assistant"}}}},
                    {"chunk": {"bytes": {"delta": {"text": "abc"}}}},
                    {"chunk": {"bytes": {"delta": {"text": "def"}}}},
                ]
            }
        }
    ) == [{"role": "assistant", "text": "abcdef", "type": "text"}]


def test_get_formatted_query_with_injected_messages():
    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "_memori_injected_count": 1,
                    "body": {
                        "messages": [
                            {"content": "injected 1", "role": "user"},
                            {"content": "new message", "role": "user"},
                        ]
                    },
                }
            }
        }
    ) == [{"content": "new message", "role": "user"}]
