r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""

import json
import struct
from unittest.mock import MagicMock

import numpy as np

from memori._search import find_similar_embeddings, parse_embedding, search_entity_facts


def test_parse_embedding_from_bytes_postgresql():
    embedding = [1.0, 2.0, 3.0]
    raw = struct.pack(f"<{len(embedding)}f", *embedding)
    result = parse_embedding(raw)
    np.testing.assert_array_almost_equal(result, embedding, decimal=5)


def test_parse_embedding_from_memoryview_postgresql():
    embedding = [1.0, 2.0, 3.0]
    raw = memoryview(struct.pack(f"<{len(embedding)}f", *embedding))
    result = parse_embedding(raw)
    np.testing.assert_array_almost_equal(result, embedding, decimal=5)


def test_parse_embedding_from_json_string_mysql():
    embedding = [1.0, 2.0, 3.0]
    raw = json.dumps(embedding)
    result = parse_embedding(raw)
    np.testing.assert_array_almost_equal(result, embedding, decimal=5)


def test_parse_embedding_from_list_mongodb():
    embedding = [1.0, 2.0, 3.0]
    result = parse_embedding(embedding)
    np.testing.assert_array_almost_equal(result, embedding, decimal=5)


def test_parse_embedding_from_numpy_array():
    embedding = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    result = parse_embedding(embedding)
    np.testing.assert_array_almost_equal(result, embedding, decimal=5)


def test_parse_embedding_maintains_float32_dtype():
    embedding = [1.0, 2.0, 3.0]
    raw = json.dumps(embedding)
    result = parse_embedding(raw)
    assert result.dtype == np.float32


def test_find_similar_embeddings_basic():
    embeddings = [
        (1, [1.0, 0.0, 0.0]),
        (2, [0.0, 1.0, 0.0]),
        (3, [0.0, 0.0, 1.0]),
    ]
    query = [1.0, 0.0, 0.0]
    result = find_similar_embeddings(embeddings, query, limit=2)

    assert len(result) == 2
    assert result[0][0] == 1
    assert result[0][1] > 0.9


def test_find_similar_embeddings_cosine_similarity():
    embeddings = [
        (1, [1.0, 0.0]),
        (2, [0.707, 0.707]),
        (3, [0.0, 1.0]),
    ]
    query = [1.0, 0.0]
    result = find_similar_embeddings(embeddings, query, limit=3)

    assert len(result) == 3
    assert result[0][0] == 1
    assert result[1][0] == 2
    assert result[2][0] == 3
    assert result[0][1] > result[1][1] > result[2][1]


def test_find_similar_embeddings_empty_list():
    result = find_similar_embeddings([], [1.0, 0.0], limit=5)
    assert result == []


def test_find_similar_embeddings_limit_larger_than_embeddings():
    embeddings = [(1, [1.0, 0.0]), (2, [0.0, 1.0])]
    query = [1.0, 0.0]
    result = find_similar_embeddings(embeddings, query, limit=10)

    assert len(result) == 2


def test_find_similar_embeddings_limit_smaller_than_embeddings():
    embeddings = [
        (1, [1.0, 0.0]),
        (2, [0.0, 1.0]),
        (3, [0.5, 0.5]),
    ]
    query = [1.0, 0.0]
    result = find_similar_embeddings(embeddings, query, limit=1)

    assert len(result) == 1
    assert result[0][0] == 1


def test_find_similar_embeddings_skips_malformed():
    embeddings = [
        (1, [1.0, 0.0, 0.0]),
        (2, "not_valid_json"),
        (3, [0.0, 0.0, 1.0]),
    ]
    query = [1.0, 0.0, 0.0]
    result = find_similar_embeddings(embeddings, query, limit=5)

    assert len(result) == 2
    assert result[0][0] in [1, 3]
    assert result[1][0] in [1, 3]


def test_find_similar_embeddings_all_malformed():
    embeddings = [
        (1, "invalid"),
        (2, "also_invalid"),
    ]
    query = [1.0, 0.0]
    result = find_similar_embeddings(embeddings, query, limit=5)

    assert result == []


def test_find_similar_embeddings_dimension_mismatch():
    embeddings = [
        (1, [1.0, 0.0]),
        (2, [0.0, 1.0]),
    ]
    query = [1.0, 0.0, 0.0]
    result = find_similar_embeddings(embeddings, query, limit=5)

    assert result == []


def test_find_similar_embeddings_mixed_formats():
    embeddings = [
        (1, json.dumps([1.0, 0.0, 0.0])),
        (2, struct.pack("<3f", 0.0, 1.0, 0.0)),
        (3, [0.0, 0.0, 1.0]),
    ]
    query = [1.0, 0.0, 0.0]
    result = find_similar_embeddings(embeddings, query, limit=3)

    assert len(result) == 3
    assert result[0][0] == 1


def test_find_similar_embeddings_returns_similarity_scores():
    embeddings = [(1, [1.0, 0.0])]
    query = [1.0, 0.0]
    result = find_similar_embeddings(embeddings, query, limit=1)

    assert len(result) == 1
    assert isinstance(result[0][1], float)
    assert 0.0 <= result[0][1] <= 1.0


def test_find_similar_embeddings_high_dimensional():
    dim = 768
    embeddings = [
        (1, [1.0 if i == 0 else 0.0 for i in range(dim)]),
        (2, [1.0 if i == 1 else 0.0 for i in range(dim)]),
    ]
    query = [1.0 if i == 0 else 0.0 for i in range(dim)]
    result = find_similar_embeddings(embeddings, query, limit=2)

    assert len(result) == 2
    assert result[0][0] == 1


def test_search_entity_facts_success():
    mock_driver = MagicMock()
    mock_driver.get_embeddings.return_value = [
        {"id": 1, "content_embedding": [1.0, 0.0, 0.0]},
        {"id": 2, "content_embedding": [0.0, 1.0, 0.0]},
        {"id": 3, "content_embedding": [0.0, 0.0, 1.0]},
    ]
    mock_driver.get_facts_by_ids.return_value = [
        {"id": 1, "content": "Fact one"},
        {"id": 2, "content": "Fact two"},
    ]

    query_embedding = [1.0, 0.0, 0.0]
    result = search_entity_facts(
        mock_driver,
        entity_id=42,
        query_embedding=query_embedding,
        limit=2,
        embeddings_limit=1000,
    )

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["content"] == "Fact one"
    assert "similarity" in result[0]
    assert isinstance(result[0]["similarity"], float)

    mock_driver.get_embeddings.assert_called_once_with(42, 1000)
    mock_driver.get_facts_by_ids.assert_called_once()


def test_search_entity_facts_no_embeddings():
    mock_driver = MagicMock()
    mock_driver.get_embeddings.return_value = []

    query_embedding = [1.0, 0.0, 0.0]
    result = search_entity_facts(
        mock_driver,
        entity_id=42,
        query_embedding=query_embedding,
        limit=5,
        embeddings_limit=1000,
    )

    assert result == []
    mock_driver.get_embeddings.assert_called_once_with(42, 1000)
    mock_driver.get_facts_by_ids.assert_not_called()


def test_search_entity_facts_no_similar_results():
    mock_driver = MagicMock()
    mock_driver.get_embeddings.return_value = [
        {"id": 1, "content_embedding": "invalid_json"},
    ]

    query_embedding = [1.0, 0.0, 0.0]
    result = search_entity_facts(
        mock_driver,
        entity_id=42,
        query_embedding=query_embedding,
        limit=5,
        embeddings_limit=1000,
    )

    assert result == []
    mock_driver.get_facts_by_ids.assert_not_called()


def test_search_entity_facts_respects_limit():
    mock_driver = MagicMock()
    mock_driver.get_embeddings.return_value = [
        {"id": i, "content_embedding": [1.0 if j == i else 0.0 for j in range(5)]}
        for i in range(5)
    ]
    mock_driver.get_facts_by_ids.return_value = [
        {"id": i, "content": f"Fact {i}"} for i in range(3)
    ]

    query_embedding = [1.0, 0.0, 0.0, 0.0, 0.0]
    result = search_entity_facts(
        mock_driver,
        entity_id=42,
        query_embedding=query_embedding,
        limit=3,
        embeddings_limit=1000,
    )

    assert len(result) <= 3


def test_search_entity_facts_returns_required_keys():
    mock_driver = MagicMock()
    mock_driver.get_embeddings.return_value = [
        {"id": 1, "content_embedding": [1.0, 0.0, 0.0]},
    ]
    mock_driver.get_facts_by_ids.return_value = [
        {"id": 1, "content": "Fact one"},
    ]

    query_embedding = [1.0, 0.0, 0.0]
    result = search_entity_facts(
        mock_driver,
        entity_id=42,
        query_embedding=query_embedding,
        limit=5,
        embeddings_limit=1000,
    )

    assert len(result) == 1
    assert "id" in result[0]
    assert "content" in result[0]
    assert "similarity" in result[0]


def test_search_entity_facts_handles_missing_content():
    mock_driver = MagicMock()
    mock_driver.get_embeddings.return_value = [
        {"id": 1, "content_embedding": [1.0, 0.0, 0.0]},
        {"id": 2, "content_embedding": [0.0, 1.0, 0.0]},
    ]
    mock_driver.get_facts_by_ids.return_value = [
        {"id": 1, "content": "Fact one"},
    ]

    query_embedding = [1.0, 0.0, 0.0]
    result = search_entity_facts(
        mock_driver,
        entity_id=42,
        query_embedding=query_embedding,
        limit=2,
        embeddings_limit=1000,
    )

    assert len(result) == 1
    assert result[0]["id"] == 1


def test_search_entity_facts_maintains_similarity_order():
    mock_driver = MagicMock()
    mock_driver.get_embeddings.return_value = [
        {"id": 1, "content_embedding": [1.0, 0.0, 0.0]},
        {"id": 2, "content_embedding": [0.707, 0.707, 0.0]},
        {"id": 3, "content_embedding": [0.0, 1.0, 0.0]},
    ]
    mock_driver.get_facts_by_ids.return_value = [
        {"id": 1, "content": "Most similar"},
        {"id": 2, "content": "Somewhat similar"},
        {"id": 3, "content": "Least similar"},
    ]

    query_embedding = [1.0, 0.0, 0.0]
    result = search_entity_facts(
        mock_driver,
        entity_id=42,
        query_embedding=query_embedding,
        limit=3,
        embeddings_limit=1000,
    )

    assert len(result) == 3
    assert result[0]["id"] == 1
    assert result[0]["similarity"] > result[1]["similarity"]
    assert result[1]["similarity"] > result[2]["similarity"]


def test_search_entity_facts_with_different_db_formats():
    mock_driver = MagicMock()
    mock_driver.get_embeddings.return_value = [
        {"id": 1, "content_embedding": json.dumps([1.0, 0.0, 0.0])},
        {"id": 2, "content_embedding": struct.pack("<3f", 0.0, 1.0, 0.0)},
        {"id": 3, "content_embedding": [0.0, 0.0, 1.0]},
    ]
    mock_driver.get_facts_by_ids.return_value = [
        {"id": 1, "content": "Fact one"},
        {"id": 2, "content": "Fact two"},
        {"id": 3, "content": "Fact three"},
    ]

    query_embedding = [1.0, 0.0, 0.0]
    result = search_entity_facts(
        mock_driver,
        entity_id=42,
        query_embedding=query_embedding,
        limit=3,
        embeddings_limit=1000,
    )

    assert len(result) == 3
    assert result[0]["id"] == 1
