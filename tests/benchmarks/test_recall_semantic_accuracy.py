import random

import pytest

from memori.llm._embeddings import embed_texts
from memori.memory.recall import Recall
from tests.benchmarks.semantic_accuracy_dataset import DATASET
from tests.benchmarks.semantic_accuracy_metrics import (
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


def _embeddings_available() -> bool:
    # If the embedding model can't load, Memori falls back to all-zeros embeddings.
    # That makes semantic accuracy meaningless, so we skip instead of failing.
    vec = embed_texts("sanity check")[0]
    return any(v != 0.0 for v in vec)


def _generate_hard_distractors(
    count: int, *, rng: random.Random, forbidden: set[str]
) -> list[str]:
    cities = ["London", "Berlin", "Rome", "Madrid", "Lisbon", "Dublin", "Vienna"]
    colors = ["red", "green", "yellow", "purple", "orange", "black", "white"]
    foods = ["sushi", "tacos", "ramen", "burgers", "pasta", "salad", "ice cream"]
    drinks = ["tea", "sparkling water", "matcha", "hot chocolate", "juice"]
    companies = ["Acme Corp", "Globex", "Initech", "Hooli", "Soylent", "Umbrella"]
    activities = ["running", "swimming", "reading", "gaming", "cycling", "yoga"]
    themes = ["light mode", "system theme", "high contrast mode"]
    birthdays = ["April 1st", "May 20th", "June 7th", "July 30th", "Oct 12th"]
    pets = ["1 cat", "3 cats", "2 dogs", "a dog", "a cat", "no pets"]

    templates = [
        lambda v: f"User lives in {v}",
        lambda v: f"User's favorite color is {v}",
        lambda v: f"User likes {v}",
        lambda v: f"User works at {v}",
        lambda v: f"User enjoys {v}",
        lambda v: f"User prefers {v}",
        lambda v: f"User's birthday is {v}",
        lambda v: f"User has {v}",
    ]
    values = [
        cities,
        colors,
        foods + drinks,
        companies,
        activities,
        themes,
        birthdays,
        pets,
    ]

    distractors: list[str] = []
    for i in range(count):
        idx = i % len(templates)
        base = templates[idx](rng.choice(values[idx]))
        candidate = f"{base} (id: d{i})"
        if candidate in forbidden:
            candidate = f"{base} (note: alt) (id: d{i})"
        distractors.append(candidate)

    return distractors


@pytest.mark.skipif(not _embeddings_available(), reason="Embedding model unavailable")
@pytest.mark.parametrize(
    "total_records", [10, 100, 500, 1000, 5000], ids=lambda n: f"n{n}"
)
def test_semantic_recall_accuracy(memori_instance, total_records):
    """
    Semantic accuracy evaluation (the "right way"):
    - seed a labeled dataset of facts
    - run a labeled set of queries
    - compute standard IR metrics (Recall@k, Precision@k, MRR, nDCG@k)
    """
    # Seed dataset facts + distractors into a fresh entity
    facts = list(DATASET["facts"])
    queries = DATASET["queries"]

    # Expand to the requested total size by adding distractors.
    # This lets us evaluate how accuracy changes as the number of stored records grows.
    if total_records < len(facts):
        pytest.skip(
            f"total_records={total_records} is smaller than labeled fact count={len(facts)}"
        )

    distractor_count = total_records - len(facts)
    rng = random.Random(123)
    forbidden = set(facts)
    distractors = _generate_hard_distractors(
        distractor_count, rng=rng, forbidden=forbidden
    )
    rng.shuffle(distractors)
    facts.extend(distractors)

    entity_id = f"semantic-accuracy-entity-{total_records}"
    memori_instance.attribution(entity_id=entity_id, process_id="semantic-accuracy")
    entity_db_id = memori_instance.config.storage.driver.entity.create(entity_id)

    fact_embeddings = embed_texts(facts)
    memori_instance.config.storage.driver.entity_fact.create(
        entity_db_id, facts, fact_embeddings
    )

    # Make the evaluation honest: search across the full corpus for this N.
    # Otherwise recall will only consider the first `recall_embeddings_limit` rows (default 1000).
    memori_instance.config.recall_embeddings_limit = total_records

    recall = Recall(memori_instance.config)

    k = 5
    scores = {
        "recall@5": [],
        "precision@5": [],
        "mrr": [],
        "ndcg@5": [],
    }

    for query, expected in queries.items():
        relevant = set(expected)
        results = recall.search_facts(query=query, limit=k, entity_id=entity_db_id)
        retrieved = [r.get("content", "") for r in results]

        scores["recall@5"].append(recall_at_k(relevant, retrieved, k))
        scores["precision@5"].append(precision_at_k(relevant, retrieved, k))
        scores["mrr"].append(mrr(relevant, retrieved))
        scores["ndcg@5"].append(ndcg_at_k(relevant, retrieved, k))

    # Aggregate (mean) metrics
    mean_scores = {k: sum(v) / len(v) for k, v in scores.items()}

    db_type = getattr(memori_instance, "_benchmark_db_type", "unknown")
    print(
        f"[semantic-accuracy] db={db_type} total={total_records} "
        f"labeled={len(DATASET['facts'])} distractors={distractor_count} "
        f"embeddings_limit={memori_instance.config.recall_embeddings_limit} {mean_scores}"
    )

    # We intentionally don't hard-fail on aggressive thresholds here because the goal
    # is to *benchmark* accuracy as N grows. The printed metrics are the artifact.
