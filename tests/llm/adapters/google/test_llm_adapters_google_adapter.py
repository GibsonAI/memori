from memori.llm.adapters.google._adapter import Adapter


def test_get_formatted_query():
    assert Adapter().get_formatted_query({}) == []
    assert Adapter().get_formatted_query({"conversation": {"query": {}}}) == []

    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "contents": [
                        {"parts": [{"text": "abc"}, {"text": "def"}], "role": "user"},
                        {"parts": [{"text": "ghi"}], "role": "system"},
                    ]
                }
            }
        }
    ) == [{"content": "abc def", "role": "user"}, {"content": "ghi", "role": "system"}]


def test_get_formatted_response_streamed():
    assert Adapter().get_formatted_response({}) == []
    assert Adapter().get_formatted_query({"conversation": {"response": {}}}) == []

    assert Adapter().get_formatted_response(
        {
            "conversation": {
                "response": [
                    {
                        "candidates": [
                            {
                                "content": {
                                    "parts": [{"text": "abc"}, {"text": "def"}],
                                    "role": "model",
                                }
                            },
                        ]
                    },
                    {
                        "candidates": [
                            {"content": {"parts": [{"text": "ghi"}], "role": "model"}}
                        ]
                    },
                ]
            }
        }
    ) == [{"role": "model", "text": "abcdefghi", "type": "text"}]


def test_get_formatted_response_unstreamed():
    assert Adapter().get_formatted_response({}) == []
    assert Adapter().get_formatted_query({"conversation": {"response": {}}}) == []

    assert Adapter().get_formatted_response(
        {
            "conversation": {
                "response": {
                    "candidates": [
                        {"content": {"parts": [{"text": "abc"}], "role": "model"}},
                        {"content": {"parts": [{"text": "def"}], "role": "model"}},
                    ]
                }
            }
        }
    ) == [
        {"role": "model", "text": "abc", "type": "text"},
        {"role": "model", "text": "def", "type": "text"},
    ]


def test_get_formatted_query_with_injected_messages():
    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "_memori_injected_count": 2,
                    "contents": [
                        {"parts": [{"text": "injected 1"}], "role": "user"},
                        {"parts": [{"text": "injected 2"}], "role": "model"},
                        {"parts": [{"text": "new message"}], "role": "user"},
                    ],
                }
            }
        }
    ) == [{"content": "new message", "role": "user"}]
