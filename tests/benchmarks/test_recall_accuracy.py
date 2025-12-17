import random

from memori.memory.recall import Recall


def test_recall_accuracy_topk(memori_instance, entity_with_n_facts):
    """
    Accuracy proxy: for a sample of stored facts, querying with the exact fact text
    should retrieve that fact in top-k (ideally top-1).

    This validates the end-to-end recall pipeline returns the correct row given an
    exact-match query (embedding + DB pull + FAISS + content fetch).
    """
    entity_db_id = entity_with_n_facts["entity_db_id"]
    facts = entity_with_n_facts["facts"]

    rng = random.Random(42)
    sample_size = min(10, len(facts))
    sampled = rng.sample(facts, k=sample_size)

    recall = Recall(memori_instance.config)

    top1_hits = 0
    top5_hits = 0

    for fact in sampled:
        results = recall.search_facts(query=fact, limit=5, entity_id=entity_db_id)
        contents = [r.get("content") for r in results]

        if contents and contents[0] == fact:
            top1_hits += 1
        if fact in contents:
            top5_hits += 1

    # Print a small summary if running with -s
    db_type = entity_with_n_facts["db_type"]
    n = entity_with_n_facts["fact_count"]
    size = entity_with_n_facts["content_size"]
    print(
        f"[recall-accuracy] db={db_type} n={n} size={size} "
        f"top1={top1_hits}/{sample_size} top5={top5_hits}/{sample_size}"
    )

    # Hard assertions: exact-match should always be in top-5 for this pipeline.
    assert top5_hits == sample_size
