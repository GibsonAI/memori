from memori.llm.adapters.xai._adapter import Adapter


def test_get_formatted_query_empty_payload():
    assert Adapter().get_formatted_query({}) == []


def test_get_formatted_query_missing_messages():
    assert Adapter().get_formatted_query({"conversation": {"query": {}}}) == []


def test_get_formatted_query_with_user_message():
    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "messages": [
                        {
                            "role": "ROLE_USER",
                            "content": [{"text": "Hello"}],
                        }
                    ]
                }
            }
        }
    ) == [{"role": "user", "content": "Hello"}]


def test_get_formatted_query_with_assistant_message():
    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "messages": [
                        {
                            "role": "ROLE_ASSISTANT",
                            "content": [{"text": "Hi there"}],
                        }
                    ]
                }
            }
        }
    ) == [{"role": "assistant", "content": "Hi there"}]


def test_get_formatted_query_with_system_message():
    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "messages": [
                        {
                            "role": "ROLE_SYSTEM",
                            "content": [{"text": "You are helpful"}],
                        }
                    ]
                }
            }
        }
    ) == [{"role": "system", "content": "You are helpful"}]


def test_get_formatted_query_with_multiple_messages():
    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "messages": [
                        {
                            "role": "ROLE_USER",
                            "content": [{"text": "Hello"}],
                        },
                        {
                            "role": "ROLE_ASSISTANT",
                            "content": [{"text": "Hi"}],
                        },
                        {
                            "role": "ROLE_USER",
                            "content": [{"text": "How are you?"}],
                        },
                    ]
                }
            }
        }
    ) == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
        {"role": "user", "content": "How are you?"},
    ]


def test_get_formatted_query_with_multiple_content_parts():
    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "messages": [
                        {
                            "role": "ROLE_USER",
                            "content": [
                                {"text": "Hello"},
                                {"text": "world"},
                                {"text": "!"},
                            ],
                        }
                    ]
                }
            }
        }
    ) == [{"role": "user", "content": "Hello world !"}]


def test_get_formatted_query_with_missing_role():
    assert (
        Adapter().get_formatted_query(
            {
                "conversation": {
                    "query": {
                        "messages": [
                            {
                                "content": [{"text": "Hello"}],
                            }
                        ]
                    }
                }
            }
        )
        == []
    )


def test_get_formatted_query_with_unknown_role():
    assert (
        Adapter().get_formatted_query(
            {
                "conversation": {
                    "query": {
                        "messages": [
                            {
                                "role": "ROLE_UNKNOWN",
                                "content": [{"text": "Hello"}],
                            }
                        ]
                    }
                }
            }
        )
        == []
    )


def test_get_formatted_query_with_empty_content():
    assert (
        Adapter().get_formatted_query(
            {
                "conversation": {
                    "query": {
                        "messages": [
                            {
                                "role": "ROLE_USER",
                                "content": [],
                            }
                        ]
                    }
                }
            }
        )
        == []
    )


def test_get_formatted_query_with_content_without_text():
    assert (
        Adapter().get_formatted_query(
            {
                "conversation": {
                    "query": {
                        "messages": [
                            {
                                "role": "ROLE_USER",
                                "content": [{"image": "data"}],
                            }
                        ]
                    }
                }
            }
        )
        == []
    )


def test_get_formatted_query_with_injected_messages():
    assert Adapter().get_formatted_query(
        {
            "conversation": {
                "query": {
                    "_memori_injected_count": 2,
                    "messages": [
                        {
                            "role": "ROLE_USER",
                            "content": [{"text": "injected 1"}],
                        },
                        {
                            "role": "ROLE_ASSISTANT",
                            "content": [{"text": "injected 2"}],
                        },
                        {
                            "role": "ROLE_USER",
                            "content": [{"text": "new message"}],
                        },
                        {
                            "role": "ROLE_ASSISTANT",
                            "content": [{"text": "new response"}],
                        },
                    ],
                }
            }
        }
    ) == [
        {"role": "user", "content": "new message"},
        {"role": "assistant", "content": "new response"},
    ]


def test_get_formatted_response_empty_payload():
    assert Adapter().get_formatted_response({}) == []


def test_get_formatted_response_missing_response():
    assert Adapter().get_formatted_response({"conversation": {"response": {}}}) == []


def test_get_formatted_response_with_string_content():
    assert Adapter().get_formatted_response(
        {
            "conversation": {
                "response": {
                    "role": "assistant",
                    "content": "Hello world",
                }
            }
        }
    ) == [{"role": "assistant", "text": "Hello world", "type": "text"}]


def test_get_formatted_response_with_list_of_dicts():
    assert Adapter().get_formatted_response(
        {
            "conversation": {
                "response": {
                    "role": "assistant",
                    "content": [
                        {"text": "Hello"},
                        {"text": "world"},
                    ],
                }
            }
        }
    ) == [
        {"role": "assistant", "text": "Hello", "type": "text"},
        {"role": "assistant", "text": "world", "type": "text"},
    ]


def test_get_formatted_response_with_list_of_strings():
    assert Adapter().get_formatted_response(
        {
            "conversation": {
                "response": {
                    "role": "assistant",
                    "content": ["Hello", "world"],
                }
            }
        }
    ) == [
        {"role": "assistant", "text": "Hello", "type": "text"},
        {"role": "assistant", "text": "world", "type": "text"},
    ]


def test_get_formatted_response_with_mixed_list():
    assert Adapter().get_formatted_response(
        {
            "conversation": {
                "response": {
                    "role": "assistant",
                    "content": [
                        {"text": "Hello"},
                        "world",
                        {"text": "!"},
                    ],
                }
            }
        }
    ) == [
        {"role": "assistant", "text": "Hello", "type": "text"},
        {"role": "assistant", "text": "world", "type": "text"},
        {"role": "assistant", "text": "!", "type": "text"},
    ]


def test_get_formatted_response_with_missing_role():
    assert (
        Adapter().get_formatted_response(
            {
                "conversation": {
                    "response": {
                        "content": "Hello world",
                    }
                }
            }
        )
        == []
    )


def test_get_formatted_response_with_missing_content():
    assert (
        Adapter().get_formatted_response(
            {
                "conversation": {
                    "response": {
                        "role": "assistant",
                    }
                }
            }
        )
        == []
    )


def test_get_formatted_response_with_dict_without_text():
    assert (
        Adapter().get_formatted_response(
            {
                "conversation": {
                    "response": {
                        "role": "assistant",
                        "content": [{"image": "data"}],
                    }
                }
            }
        )
        == []
    )
