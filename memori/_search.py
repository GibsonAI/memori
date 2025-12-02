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
from typing import Any

import faiss
import numpy as np


def parse_embedding(raw) -> np.ndarray:
    """Parse embedding from database format to numpy array.

    Handles multiple storage formats:
    - Binary (BYTEA/BLOB/BinData): Most common, used by all databases
    - JSON string: Legacy format
    - Native array: Fallback
    """
    if isinstance(raw, bytes | memoryview):
        return np.frombuffer(raw, dtype="<f4")
    elif isinstance(raw, str):
        # Legacy JSON format
        return np.array(json.loads(raw), dtype=np.float32)
    else:
        # Try to extract bytes from bson.Binary or other wrappers
        if hasattr(raw, "__bytes__"):
            return np.frombuffer(bytes(raw), dtype="<f4")
        # Fallback to native array (MongoDB array format)
        return np.asarray(raw, dtype=np.float32)


def find_similar_embeddings(
    embeddings: list[tuple[int, Any]],
    query_embedding: list[float],
    limit: int = 5,
) -> list[tuple[int, float]]:
    """Find most similar embeddings using FAISS cosine similarity.

    Args:
        embeddings: List of (id, embedding_raw) tuples
        query_embedding: Query embedding as list of floats
        limit: Number of results to return

    Returns:
        List of (id, similarity_score) tuples, sorted by similarity desc
    """
    if not embeddings:
        return []

    embeddings_list = []
    id_list = []

    for fact_id, raw in embeddings:
        try:
            parsed = parse_embedding(raw)
            embeddings_list.append(parsed)
            id_list.append(fact_id)
        except Exception:
            continue

    if not embeddings_list:
        return []

    embeddings_array = np.stack(embeddings_list, axis=0)

    faiss.normalize_L2(embeddings_array)
    query_array = np.asarray([query_embedding], dtype=np.float32)

    if embeddings_array.shape[1] != query_array.shape[1]:
        return []

    faiss.normalize_L2(query_array)

    index = faiss.IndexFlatIP(embeddings_array.shape[1])
    index.add(embeddings_array)  # type: ignore[call-arg]

    k = min(limit, len(embeddings_array))
    similarities, indices = index.search(query_array, k)  # type: ignore[call-arg]

    results = []
    for result_idx, embedding_idx in enumerate(indices[0]):
        if embedding_idx >= 0 and embedding_idx < len(id_list):
            results.append((id_list[embedding_idx], float(similarities[0][result_idx])))

    return results


def search_entity_facts(
    entity_fact_driver,
    entity_id: int,
    query_embedding: list[float],
    limit: int,
    embeddings_limit: int,
) -> list[dict]:
    """Search entity facts by embedding similarity.

    Args:
        entity_fact_driver: Driver instance with get_embeddings and get_facts_by_ids methods
        entity_id: Entity ID to search within
        query_embedding: Query embedding as list of floats
        limit: Number of results to return
        embeddings_limit: Number of embeddings to retrieve from database

    Returns:
        List of dicts with keys: id, content, similarity
    """
    results = entity_fact_driver.get_embeddings(entity_id, embeddings_limit)

    if not results:
        return []

    embeddings = [(row["id"], row["content_embedding"]) for row in results]
    similar = find_similar_embeddings(embeddings, query_embedding, limit)

    if not similar:
        return []

    top_ids = [fact_id for fact_id, _ in similar]
    similarities_map = dict(similar)

    content_results = entity_fact_driver.get_facts_by_ids(top_ids)
    content_map = {row["id"]: row["content"] for row in content_results}

    facts_with_similarity = []
    for fact_id in top_ids:
        if fact_id in content_map:
            facts_with_similarity.append(
                {
                    "id": fact_id,
                    "content": content_map[fact_id],
                    "similarity": similarities_map[fact_id],
                }
            )

    return facts_with_similarity
