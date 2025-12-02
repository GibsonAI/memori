from unittest.mock import Mock, patch

from memori.llm._embeddings import _get_model


def test_get_model_downloads_from_huggingface():
    with patch("memori.llm._embeddings.SentenceTransformer") as mock_transformer:
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        from memori.llm import _embeddings

        _embeddings._MODEL_CACHE.clear()

        result = _get_model("all-mpnet-base-v2")

        assert result is mock_model
        mock_transformer.assert_called_once_with("all-mpnet-base-v2")


def test_get_model_caching():
    with patch("memori.llm._embeddings.SentenceTransformer") as mock_transformer:
        mock_model = Mock()
        mock_transformer.return_value = mock_model

        from memori.llm import _embeddings

        _embeddings._MODEL_CACHE.clear()

        result1 = _get_model("test-model")
        result2 = _get_model("test-model")

        assert result1 is result2
        mock_transformer.assert_called_once()


def test_get_model_different_models():
    with patch("memori.llm._embeddings.SentenceTransformer") as mock_transformer:
        mock_model1 = Mock()
        mock_model2 = Mock()
        mock_transformer.side_effect = [mock_model1, mock_model2]

        from memori.llm import _embeddings

        _embeddings._MODEL_CACHE.clear()

        result1 = _get_model("model-1")
        result2 = _get_model("model-2")

        assert result1 is not result2
        assert mock_transformer.call_count == 2
