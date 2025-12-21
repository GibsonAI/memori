import datetime
import os
import random
import statistics
from math import sqrt
from typing import TypedDict
from uuid import uuid4

import pytest

from memori._config import Config
from memori.llm import _embeddings as embeddings_mod
from memori.llm._embeddings import embed_texts
from memori.memory.recall import Recall
from tests.benchmarks._results import append_csv_row, results_dir
from tests.benchmarks.fixtures.sample_facts import build_user_data
from tests.benchmarks.semantic_accuracy_dataset import DATASET as CURATED_DATASET
from tests.benchmarks.semantic_accuracy_metrics import (
    mrr,
)


def _embeddings_available() -> bool:
    # If the embedding model can't load, Memori falls back to all-zeros embeddings.
    # That makes semantic accuracy meaningless, so we skip instead of failing.
    cfg = Config()
    vec = embed_texts(
        "sanity check",
        model=cfg.embeddings.model,
        fallback_dimension=cfg.embeddings.fallback_dimension,
    )[0]
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


def _strip_id_suffix(text: str) -> str:
    idx = text.rfind(" (id:")
    if idx == -1 or not text.endswith(")"):
        return text
    return text[:idx]


def _fact_to_text(subject: str, predicate: str, obj: str, *, fact_id: int) -> str:
    subj = subject.replace("_", " ")
    pred = predicate.replace("_", " ")
    obj_text = obj.replace("_", " ")
    return f"{subj} {pred} {obj_text} (id: {fact_id})"


class _SemanticAccuracyDataset(TypedDict):
    corpus_facts: list[str]
    queries: dict[str, list[str]]


def _t_critical_975(df: int) -> float:
    # 97.5% quantiles for Student-t (two-sided 95% CI), df 1..10
    # If df is larger, normal approximation is fine for our benchmark reporting.
    table = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
    }
    return table.get(df, 1.96)


def _mean_ci_95(values: list[float]) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0], values[0]

    mean = statistics.fmean(values)
    stdev = statistics.stdev(values)
    df = len(values) - 1
    half_width = _t_critical_975(df) * (stdev / sqrt(len(values)))
    return mean, mean - half_width, mean + half_width


def _default_semantic_accuracy_csv_path() -> str:
    return str(results_dir() / "semantic_accuracy.csv")


def _default_semantic_accuracy_curated_csv_path() -> str:
    return str(results_dir() / "semantic_accuracy_curated.csv")


def _build_semantic_accuracy_dataset_from_sample_facts() -> _SemanticAccuracyDataset:
    triples: list[tuple[str, str, str]] = build_user_data()["facts"]
    fact_texts = [
        _fact_to_text(s, p, o, fact_id=i) for i, (s, p, o) in enumerate(triples)
    ]

    def _facts(subject: str, pred: str) -> list[str]:
        results: list[str] = []
        for i, (s, p, _) in enumerate(triples):
            if s == subject and p == pred:
                results.append(fact_texts[i])
        return results

    # We generate queries later (with varying seeds / sizes).
    return {"corpus_facts": fact_texts, "queries": {}}


def _subject_variants(subject: str) -> list[str]:
    if subject == "John":
        return ["John", "I", "me", "the user", "this user"]

    subj = subject.replace("_", " ")
    variants = {subj, subj.lower()}

    if subject.startswith("Coworker_") or subject.startswith("Friend_"):
        _, num = subject.split("_", 1)
        label = subject.split("_", 1)[0].lower()
        variants.update(
            {
                f"{label} {num}",
                f"{label} #{num}",
                f"my {label} {num}",
                f"My {label} {num}",
                f"{label.title()} {num}",
            }
        )

    return sorted(variants)


def _predicate_question_variants(subject: str, predicate: str) -> list[str]:
    pred_words = predicate.replace("_", " ")

    templates: list[str]
    if predicate == "member_of_team":
        templates = [
            "Which team is {subj} a member of?",
            "What team is {subj} on?",
            "Which team does {subj} belong to?",
            "What is {subj}'s team?",
        ]
    elif predicate == "located_in":
        templates = [
            "Where is {subj} located?",
            "What city is {subj} in?",
            "Where can I find {subj}?",
        ]
    elif predicate == "in_country":
        templates = [
            "What country is {subj} in?",
            "Which country is {subj} in?",
        ]
    elif predicate == "has_timezone":
        templates = [
            "What timezone does {subj} have?",
            "What is {subj}'s timezone?",
        ]
    elif predicate == "uses_llm_for":
        templates = [
            "What does {subj} use LLM for?",
            "What does {subj} use an LLM for?",
            "Why does {subj} use LLMs?",
        ]
    elif predicate == "uses_llm_provider":
        templates = [
            "Which LLM providers does {subj} use?",
            "What LLM providers does {subj} use?",
        ]
    elif predicate == "uses_model_family":
        templates = [
            "Which model families does {subj} use?",
            "What model families does {subj} use?",
        ]
    elif predicate == "type":
        templates = [
            "What type is {subj}?",
            "What kind of entity is {subj}?",
        ]
    elif predicate.startswith("has_"):
        rest = predicate.removeprefix("has_").replace("_", " ")
        templates = [
            f"What {rest} does {{subj}} have?",
            f"Which {rest} does {{subj}} have?",
        ]
    else:
        templates = [
            f"What is {{subj}} {pred_words}?",
            f"What does {{subj}} {pred_words}?",
        ]

    questions: list[str] = []
    for subj in _subject_variants(subject):
        for t in templates:
            questions.append(t.format(subj=subj))

    # Deduplicate but preserve a stable order
    seen: set[str] = set()
    out: list[str] = []
    for q in questions:
        if q in seen:
            continue
        out.append(q)
        seen.add(q)
    return out


def _generate_query_set(
    *,
    triples: list[tuple[str, str, str]],
    fact_texts: list[str],
    rng: random.Random,
    query_count: int,
    expected_cap: int = 5,
) -> dict[str, list[str]]:
    # Group facts by (subject, predicate) so we can accept any of the values.
    grouped: dict[tuple[str, str], list[str]] = {}
    for i, (s, p, _) in enumerate(triples):
        grouped.setdefault((s, p), []).append(_strip_id_suffix(fact_texts[i]))

    items = list(grouped.items())
    rng.shuffle(items)

    queries: dict[str, list[str]] = {}

    # Always include the coworker-035 query if present (user requested).
    key = ("Coworker_035", "member_of_team")
    if key in grouped:
        variants = _predicate_question_variants(*key)
        queries[rng.choice(variants)] = grouped[key][:1]

    for (s, p), expected in items:
        if len(queries) >= query_count:
            break
        variants = _predicate_question_variants(s, p)
        rng.shuffle(variants)
        for question in variants:
            if question in queries:
                continue
            queries[question] = expected[:expected_cap]
            break

    return queries


@pytest.mark.skipif(not _embeddings_available(), reason="Embedding model unavailable")
@pytest.mark.parametrize(
    "total_records",
    [10, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
    ids=lambda n: f"n{n}",
)
def test_semantic_recall_accuracy(memori_instance, total_records):
    """
    Semantic accuracy evaluation (the "right way"):
    - seed a labeled dataset of facts
    - run a labeled set of queries
    - report hit@k (a.k.a. recall-as-hit), plus MRR
    """
    dataset = _build_semantic_accuracy_dataset_from_sample_facts()
    corpus_facts = dataset["corpus_facts"]
    triples: list[tuple[str, str, str]] = build_user_data()["facts"]

    query_count = int(os.environ.get("SEMANTIC_ACCURACY_QUERY_COUNT", "150"))
    repeats = int(os.environ.get("SEMANTIC_ACCURACY_REPEATS", "5"))
    base_seed = int(os.environ.get("SEMANTIC_ACCURACY_BASE_SEED", "123"))

    if query_count < 1:
        pytest.skip("SEMANTIC_ACCURACY_QUERY_COUNT must be >= 1")
    if repeats < 1:
        pytest.skip("SEMANTIC_ACCURACY_REPEATS must be >= 1")

    if os.environ.get("SEMANTIC_ACCURACY_DUMP_FACTS") == "1":
        limit_raw = os.environ.get("SEMANTIC_ACCURACY_DUMP_FACTS_LIMIT")
        limit = int(limit_raw) if limit_raw else None
        facts_to_print = corpus_facts[:limit] if limit else corpus_facts
        for fact in facts_to_print:
            print(fact)
        pytest.skip("Dumped semantic accuracy facts")

    # Repeat full evaluation with different seeds/query sets to report variance.
    per_run: dict[str, list[float]] = {
        "hit@1": [],
        "hit@3": [],
        "hit@5": [],
        "mrr": [],
    }

    for rep in range(repeats):
        rng = random.Random(base_seed + rep)
        queries = _generate_query_set(
            triples=triples,
            fact_texts=corpus_facts,
            rng=rng,
            query_count=query_count,
        )
        labeled_norm_set = {fact for expected in queries.values() for fact in expected}
        if not labeled_norm_set:
            pytest.skip("No labeled facts available from generated query set")

        if total_records < len(labeled_norm_set):
            pytest.skip(
                f"total_records={total_records} is smaller than labeled fact count={len(labeled_norm_set)}"
            )

        distractor_count = total_records - len(labeled_norm_set)
        distractor_pool = [
            f for f in corpus_facts if _strip_id_suffix(f) not in labeled_norm_set
        ]
        forbidden = set(labeled_norm_set)

        # Nested distractors per (total_records, rep): deterministic shuffle + prefix.
        distractor_pool_shuffled = list(distractor_pool)
        rng.shuffle(distractor_pool_shuffled)

        if distractor_count <= len(distractor_pool_shuffled):
            distractors = distractor_pool_shuffled[:distractor_count]
        else:
            distractors = list(distractor_pool_shuffled)
            remaining = distractor_count - len(distractor_pool_shuffled)
            distractors.extend(
                _generate_hard_distractors(remaining, rng=rng, forbidden=forbidden)
            )

        rng.shuffle(distractors)

        labeled_facts_with_ids: list[str] = []
        labeled_with_ids_set: set[str] = set()
        for full_fact in corpus_facts:
            norm = _strip_id_suffix(full_fact)
            if norm in labeled_norm_set and full_fact not in labeled_with_ids_set:
                labeled_facts_with_ids.append(full_fact)
                labeled_with_ids_set.add(full_fact)

        facts = list(labeled_facts_with_ids)
        rng.shuffle(facts)
        facts.extend(distractors)

        # IMPORTANT: use a unique entity per run to avoid accumulating facts
        # across reruns (especially if embedding dimensions/models change).
        entity_id = f"semantic-accuracy-entity-{total_records}-rep{rep}-{uuid4()}"
        memori_instance.attribution(entity_id=entity_id, process_id="semantic-accuracy")
        entity_db_id = memori_instance.config.storage.driver.entity.create(entity_id)

        fact_embeddings = embed_texts(
            facts,
            model=memori_instance.config.embeddings.model,
            fallback_dimension=memori_instance.config.embeddings.fallback_dimension,
        )
        memori_instance.config.storage.driver.entity_fact.create(
            entity_db_id, facts, fact_embeddings
        )

        memori_instance.config.recall_embeddings_limit = total_records
        recall = Recall(memori_instance.config)

        scores = {
            "hit@1": [],
            "hit@3": [],
            "hit@5": [],
            "mrr": [],
        }

        debug_limit = int(os.environ.get("SEMANTIC_ACCURACY_DEBUG_LIMIT", "50"))
        debug_printed = 0

        for query, expected in queries.items():
            results = recall.search_facts(query=query, limit=5, entity_id=entity_db_id)
            retrieved = [r.get("content", "") for r in results]
            retrieved_norm = [_strip_id_suffix(r) for r in retrieved]

            relevant = set(expected)
            scores["hit@1"].append(
                1.0 if any(f in retrieved_norm[:1] for f in relevant) else 0.0
            )
            scores["hit@3"].append(
                1.0 if any(f in retrieved_norm[:3] for f in relevant) else 0.0
            )
            scores["hit@5"].append(
                1.0 if any(f in retrieved_norm[:5] for f in relevant) else 0.0
            )
            scores["mrr"].append(mrr(relevant, retrieved_norm))

            if (
                os.environ.get("SEMANTIC_ACCURACY_DEBUG") == "1"
                and debug_printed < debug_limit
            ):
                hit_rank: int | None = None
                for i, item in enumerate(retrieved_norm, start=1):
                    if item in relevant:
                        hit_rank = i
                        break

                tag = "HIT" if hit_rank is not None else "MISS"
                extra = f"rank={hit_rank} " if hit_rank is not None else ""
                print(
                    f"[semantic-accuracy][debug][{tag}] total={total_records} rep={rep} "
                    f"query={query!r} {extra}"
                    f"expected={expected!r} retrieved={retrieved_norm!r}"
                )
                debug_printed += 1

        per_run["hit@1"].append(statistics.fmean(scores["hit@1"]))
        per_run["hit@3"].append(statistics.fmean(scores["hit@3"]))
        per_run["hit@5"].append(statistics.fmean(scores["hit@5"]))
        per_run["mrr"].append(statistics.fmean(scores["mrr"]))

    db_type = getattr(memori_instance, "_benchmark_db_type", "unknown")

    hit5_mean, hit5_lo, hit5_hi = _mean_ci_95(per_run["hit@5"])
    hit1_mean, hit1_lo, hit1_hi = _mean_ci_95(per_run["hit@1"])
    hit3_mean, hit3_lo, hit3_hi = _mean_ci_95(per_run["hit@3"])
    mrr_mean, mrr_lo, mrr_hi = _mean_ci_95(per_run["mrr"])

    hit5_min = min(per_run["hit@5"])
    hit5_max = max(per_run["hit@5"])

    print(
        f"[semantic-accuracy] db={db_type} total={total_records} "
        f"queries={query_count} repeats={repeats} "
        f"hit@5(min/mean/max)={hit5_min:.3f}/{hit5_mean:.3f}/{hit5_max:.3f} "
        f"hit@5_ci95=({hit5_lo:.3f},{hit5_hi:.3f}) "
        f"hit@3_mean={hit3_mean:.3f} ci95=({hit3_lo:.3f},{hit3_hi:.3f}) "
        f"hit@1_mean={hit1_mean:.3f} ci95=({hit1_lo:.3f},{hit1_hi:.3f}) "
        f"mrr_mean={mrr_mean:.3f} ci95=({mrr_lo:.3f},{mrr_hi:.3f})"
    )

    csv_path = (
        os.environ.get("SEMANTIC_ACCURACY_CSV_PATH")
        or _default_semantic_accuracy_csv_path()
    )
    run_id = str(uuid4())
    ts = datetime.datetime.now(datetime.UTC).isoformat()
    header = [
        "timestamp_utc",
        "run_id",
        "db",
        "total_records",
        "query_count",
        "repeats",
        "base_seed",
        "embedding_model",
        "embedding_default_dim",
        "hit1_mean",
        "hit1_ci_lo",
        "hit1_ci_hi",
        "hit3_mean",
        "hit3_ci_lo",
        "hit3_ci_hi",
        "hit5_min",
        "hit5_mean",
        "hit5_max",
        "hit5_ci_lo",
        "hit5_ci_hi",
        "mrr_mean",
        "mrr_ci_lo",
        "mrr_ci_hi",
    ]
    append_csv_row(
        csv_path,
        header=header,
        row={
            "timestamp_utc": ts,
            "run_id": run_id,
            "db": db_type,
            "total_records": total_records,
            "query_count": query_count,
            "repeats": repeats,
            "base_seed": base_seed,
            "embedding_model": getattr(embeddings_mod, "_DEFAULT_MODEL", ""),
            "embedding_default_dim": getattr(embeddings_mod, "_DEFAULT_DIMENSION", ""),
            "hit1_mean": hit1_mean,
            "hit1_ci_lo": hit1_lo,
            "hit1_ci_hi": hit1_hi,
            "hit3_mean": hit3_mean,
            "hit3_ci_lo": hit3_lo,
            "hit3_ci_hi": hit3_hi,
            "hit5_min": hit5_min,
            "hit5_mean": hit5_mean,
            "hit5_max": hit5_max,
            "hit5_ci_lo": hit5_lo,
            "hit5_ci_hi": hit5_hi,
            "mrr_mean": mrr_mean,
            "mrr_ci_lo": mrr_lo,
            "mrr_ci_hi": mrr_hi,
        },
    )

    # We intentionally don't hard-fail on aggressive thresholds here because the goal
    # is to *benchmark* accuracy as N grows. The printed metrics are the artifact.


@pytest.mark.skipif(not _embeddings_available(), reason="Embedding model unavailable")
@pytest.mark.parametrize(
    "distractor_count", [0, 200], ids=["no_distractors", "plus200_distractors"]
)
def test_semantic_recall_accuracy_curated(memori_instance, distractor_count):
    """
    Semantic accuracy benchmark on a small curated dataset.

    This provides a stable baseline (fixed facts + fixed queries) that is easier to
    defend over time than purely generated query sets.
    """
    facts = list(CURATED_DATASET["facts"])
    queries = CURATED_DATASET["queries"]

    rng = random.Random(123)
    forbidden = set(facts)
    distractors = _generate_hard_distractors(
        distractor_count, rng=rng, forbidden=forbidden
    )
    rng.shuffle(distractors)
    facts.extend(distractors)
    rng.shuffle(facts)

    entity_id = f"semantic-accuracy-curated-{distractor_count}-{uuid4()}"
    memori_instance.attribution(
        entity_id=entity_id, process_id="semantic-accuracy-curated"
    )
    entity_db_id = memori_instance.config.storage.driver.entity.create(entity_id)

    fact_embeddings = embed_texts(
        facts,
        model=memori_instance.config.embeddings.model,
        fallback_dimension=memori_instance.config.embeddings.fallback_dimension,
    )
    memori_instance.config.storage.driver.entity_fact.create(
        entity_db_id, facts, fact_embeddings
    )

    memori_instance.config.recall_embeddings_limit = len(facts)
    recall = Recall(memori_instance.config)

    k = 5
    hit1: list[float] = []
    hit3: list[float] = []
    hit5: list[float] = []
    mrr_scores: list[float] = []

    for query, expected in queries.items():
        results = recall.search_facts(query=query, limit=k, entity_id=entity_db_id)
        retrieved = [r.get("content", "") for r in results]
        retrieved_norm = [_strip_id_suffix(r) for r in retrieved]

        relevant_norm = {_strip_id_suffix(e) for e in expected}
        hit1.append(1.0 if any(f in retrieved_norm[:1] for f in relevant_norm) else 0.0)
        hit3.append(1.0 if any(f in retrieved_norm[:3] for f in relevant_norm) else 0.0)
        hit5.append(1.0 if any(f in retrieved_norm[:5] for f in relevant_norm) else 0.0)
        mrr_scores.append(mrr(relevant_norm, retrieved_norm))

    db_type = getattr(memori_instance, "_benchmark_db_type", "unknown")
    print(
        f"[semantic-accuracy-curated] db={db_type} total={len(facts)} "
        f"distractors={distractor_count} "
        f"hit@1={statistics.fmean(hit1):.3f} "
        f"hit@3={statistics.fmean(hit3):.3f} "
        f"hit@5={statistics.fmean(hit5):.3f} "
        f"mrr={statistics.fmean(mrr_scores):.3f}"
    )

    curated_csv_path = (
        os.environ.get("SEMANTIC_ACCURACY_CURATED_CSV_PATH")
        or _default_semantic_accuracy_curated_csv_path()
    )
    curated_header = [
        "timestamp_utc",
        "run_id",
        "db",
        "total_records",
        "distractor_count",
        "embedding_model",
        "embedding_default_dim",
        "hit1_mean",
        "hit3_mean",
        "hit5_mean",
        "mrr_mean",
    ]
    append_csv_row(
        curated_csv_path,
        header=curated_header,
        row={
            "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
            "run_id": str(uuid4()),
            "db": db_type,
            "total_records": len(facts),
            "distractor_count": distractor_count,
            "embedding_model": getattr(embeddings_mod, "_DEFAULT_MODEL", ""),
            "embedding_default_dim": getattr(embeddings_mod, "_DEFAULT_DIMENSION", ""),
            "hit1_mean": statistics.fmean(hit1),
            "hit3_mean": statistics.fmean(hit3),
            "hit5_mean": statistics.fmean(hit5),
            "mrr_mean": statistics.fmean(mrr_scores),
        },
    )
