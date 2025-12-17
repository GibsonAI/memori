import math


def recall_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    topk = retrieved[:k]
    hit = any(item in relevant for item in topk)
    return 1.0 if hit else 0.0


def precision_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    topk = retrieved[:k]
    if not topk:
        return 0.0
    hits = sum(1 for item in topk if item in relevant)
    return hits / min(k, len(topk))


def mrr(relevant: set[str], retrieved: list[str]) -> float:
    for i, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / i
    return 0.0


def ndcg_at_k(relevant: set[str], retrieved: list[str], k: int) -> float:
    if k <= 0:
        return 0.0
    topk = retrieved[:k]
    if not topk:
        return 0.0

    def dcg(items: list[str]) -> float:
        score = 0.0
        for i, item in enumerate(items, start=1):
            rel = 1.0 if item in relevant else 0.0
            score += rel / math.log2(i + 1)
        return score

    ideal = list(relevant)[:k]
    ideal_dcg = dcg(ideal)
    if ideal_dcg == 0.0:
        return 0.0
    return dcg(topk) / ideal_dcg
