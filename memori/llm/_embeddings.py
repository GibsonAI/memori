r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                 perfectam memoriam
                      memorilabs.ai
"""

import asyncio
import logging
import os
import struct
from collections.abc import Iterable
from typing import Any

os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_MODEL_CACHE: dict[str, SentenceTransformer] = {}


def _get_model(model_name: str) -> SentenceTransformer:
    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
    return _MODEL_CACHE[model_name]


def _prepare_text_inputs(texts: str | Iterable[str]) -> list[str]:
    if isinstance(texts, str):
        return [texts]
    return [t for t in texts if t]


def _embedding_dimension(model: Any, default: int) -> int:
    try:
        dim_value = model.get_sentence_embedding_dimension()
        return int(dim_value) if dim_value is not None else default
    except (RuntimeError, ValueError, AttributeError, TypeError):
        return default


def _zero_vectors(count: int, dim: int) -> list[list[float]]:
    return [[0.0] * dim for _ in range(count)]


def format_embedding_for_db(embedding: list[float], dialect: str) -> Any:
    binary_data = struct.pack(f"<{len(embedding)}f", *embedding)

    if dialect == "mongodb":
        try:
            import bson

            return bson.Binary(binary_data)
        except ImportError:
            return binary_data
    return binary_data


def embed_texts(
    texts: str | list[str],
    model: str,
    fallback_dimension: int,
) -> list[list[float]]:
    inputs = _prepare_text_inputs(texts)
    if not inputs:
        logger.debug("embed_texts called with empty input")
        return []

    logger.debug(
        "Generating embedding using model: %s for %d text(s)", model, len(inputs)
    )

    try:
        encoder = _get_model(model)
    except (OSError, RuntimeError, ValueError):
        logger.debug("Failed to load model %s, returning zero embeddings", model)
        return _zero_vectors(len(inputs), fallback_dimension)

    try:
        embeddings = encoder.encode(inputs, convert_to_numpy=True)
        result = embeddings.tolist()
        if result:
            logger.debug(
                "Embedding generated - dimension: %d, count: %d",
                len(result[0]),
                len(result),
            )
        return result
    except ValueError as e:
        # Some models can raise "all input arrays must have the same shape" when
        # encoding batches. Retry one-by-one to avoid internal stacking.
        if "same shape" not in str(e):
            raise

        try:
            vectors: list[list[float]] = []
            for text in inputs:
                single = encoder.encode([text], convert_to_numpy=True)
                vectors.append(single[0].tolist())

            dim_set = {len(v) for v in vectors}
            if len(dim_set) != 1:
                raise ValueError("all input arrays must have the same shape") from e

            if vectors:
                logger.debug(
                    "Embedding generated (one-by-one) - dimension: %d, count: %d",
                    len(vectors[0]),
                    len(vectors),
                )
            return vectors
        except Exception:
            dim = _embedding_dimension(encoder, default=fallback_dimension)
            logger.debug(
                "Embedding encode failed, returning zero embeddings of dim %d", dim
            )
            return _zero_vectors(len(inputs), dim)
    except RuntimeError:
        dim = _embedding_dimension(encoder, default=fallback_dimension)
        logger.debug(
            "Embedding encode failed, returning zero embeddings of dim %d", dim
        )
        return _zero_vectors(len(inputs), dim)


async def embed_texts_async(
    texts: str | list[str],
    model: str,
    fallback_dimension: int,
) -> list[list[float]]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, embed_texts, texts, model, fallback_dimension
    )
