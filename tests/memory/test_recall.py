r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.exc import OperationalError

from memori._config import Config
from memori.memory.recall import MAX_RETRIES, RETRY_BACKOFF_BASE, Recall


def test_recall_init():
    config = Config()
    recall = Recall(config)
    assert recall.config is config


def test_search_facts_no_storage():
    config = Config()
    config.storage = None
    recall = Recall(config)

    result = recall.search_facts("test query")

    assert result == []


def test_search_facts_no_driver():
    config = Config()
    config.storage = Mock()
    config.storage.driver = None
    recall = Recall(config)

    result = recall.search_facts("test query")

    assert result == []


def test_search_facts_no_entity_id_in_config():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.entity_id = None
    recall = Recall(config)

    result = recall.search_facts("test query", entity_id=None)

    assert result == []


def test_search_facts_entity_create_returns_none():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = None
    config.entity_id = "test-entity"
    recall = Recall(config)

    result = recall.search_facts("test query")

    assert result == []
    config.storage.driver.entity.create.assert_called_once_with("test-entity")


def test_search_facts_uses_provided_entity_id():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.entity_id = None
    recall = Recall(config)

    with patch("memori.memory.recall.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        with patch("memori.memory.recall.search_entity_facts") as mock_search:
            mock_search.return_value = [{"content": "fact 1", "similarity": 0.9}]

            result = recall.search_facts("test query", entity_id=42)

            assert len(result) == 1
            mock_search.assert_called_once()
            args = mock_search.call_args[0]
            assert args[1] == 42


def test_search_facts_success():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    config.storage.driver.entity.create.return_value = 1
    config.entity_id = "test-entity"
    recall = Recall(config)

    with patch("memori.memory.recall.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        with patch("memori.memory.recall.search_entity_facts") as mock_search:
            mock_search.return_value = [
                {"content": "User likes pizza", "similarity": 0.9},
                {"content": "User lives in NYC", "similarity": 0.85},
            ]

            result = recall.search_facts("What do I like?", limit=5, entity_id=1)

            assert len(result) == 2
            assert result[0]["content"] == "User likes pizza"
            assert result[1]["content"] == "User lives in NYC"

            mock_embed.assert_called_once_with("What do I like?")
            mock_search.assert_called_once_with(
                config.storage.driver.entity_fact,
                1,
                [0.1, 0.2, 0.3],
                5,
                1000,
            )


def test_search_facts_with_custom_limit():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    recall = Recall(config)

    with patch("memori.memory.recall.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        with patch("memori.memory.recall.search_entity_facts") as mock_search:
            mock_search.return_value = []

            recall.search_facts("test query", limit=10, entity_id=1)

            mock_search.assert_called_once()
            assert mock_search.call_args[0][3] == 10
            assert mock_search.call_args[0][4] == 1000


def test_search_facts_retry_on_operational_error():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    recall = Recall(config)

    with patch("memori.memory.recall.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        with patch("memori.memory.recall.search_entity_facts") as mock_search:
            mock_search.side_effect = [
                OperationalError(
                    "statement", "params", Exception("restart transaction")
                ),
                [{"content": "fact", "similarity": 0.9}],
            ]

            with patch("memori.memory.recall.time.sleep") as mock_sleep:
                result = recall.search_facts("test query", entity_id=1)

                assert len(result) == 1
                assert mock_search.call_count == 2
                mock_sleep.assert_called_once()
                assert mock_sleep.call_args[0][0] == RETRY_BACKOFF_BASE * (2**0)


def test_search_facts_retry_multiple_times():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    recall = Recall(config)

    with patch("memori.memory.recall.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        with patch("memori.memory.recall.search_entity_facts") as mock_search:
            mock_search.side_effect = [
                OperationalError(
                    "statement", "params", Exception("restart transaction")
                ),
                OperationalError(
                    "statement", "params", Exception("restart transaction")
                ),
                [{"content": "fact", "similarity": 0.9}],
            ]

            with patch("memori.memory.recall.time.sleep") as mock_sleep:
                result = recall.search_facts("test query", entity_id=1)

                assert len(result) == 1
                assert mock_search.call_count == 3
                assert mock_sleep.call_count == 2
                assert mock_sleep.call_args_list[0][0][0] == RETRY_BACKOFF_BASE * (2**0)
                assert mock_sleep.call_args_list[1][0][0] == RETRY_BACKOFF_BASE * (2**1)


def test_search_facts_raises_after_max_retries():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    recall = Recall(config)

    with patch("memori.memory.recall.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        with patch("memori.memory.recall.search_entity_facts") as mock_search:
            mock_search.side_effect = OperationalError(
                "statement", "params", Exception("restart transaction")
            )

            with patch("memori.memory.recall.time.sleep"):
                with pytest.raises(OperationalError):
                    recall.search_facts("test query", entity_id=1)

                assert mock_search.call_count == MAX_RETRIES


def test_search_facts_raises_on_non_restart_error():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    recall = Recall(config)

    with patch("memori.memory.recall.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        with patch("memori.memory.recall.search_entity_facts") as mock_search:
            mock_search.side_effect = OperationalError(
                "statement", "params", Exception("some other error")
            )

            with pytest.raises(OperationalError):
                recall.search_facts("test query", entity_id=1)

            assert mock_search.call_count == 1


def test_search_facts_returns_empty_on_no_results():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    recall = Recall(config)

    with patch("memori.memory.recall.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        with patch("memori.memory.recall.search_entity_facts") as mock_search:
            mock_search.return_value = []

            result = recall.search_facts("test query", entity_id=1)

            assert result == []


def test_search_facts_embeds_query_correctly():
    config = Config()
    config.storage = Mock()
    config.storage.driver = Mock()
    recall = Recall(config)

    with patch("memori.memory.recall.embed_texts") as mock_embed:
        mock_embed.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]

        with patch("memori.memory.recall.search_entity_facts") as mock_search:
            mock_search.return_value = []

            recall.search_facts("My test query", entity_id=1)

            mock_embed.assert_called_once_with("My test query")
            mock_search.assert_called_once()
            assert mock_search.call_args[0][2] == [0.1, 0.2, 0.3, 0.4, 0.5]


def test_constants():
    assert MAX_RETRIES == 3
    assert RETRY_BACKOFF_BASE == 0.05
