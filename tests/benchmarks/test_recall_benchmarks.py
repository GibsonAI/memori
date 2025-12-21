"""Performance benchmarks for Memori recall functionality."""

import datetime
import os
from time import perf_counter

import pytest

from memori._config import Config
from memori._search import find_similar_embeddings
from memori.llm._embeddings import embed_texts
from memori.memory.recall import Recall
from tests.benchmarks._results import append_csv_row, results_dir
from tests.benchmarks.memory_utils import measure_peak_rss_bytes


def _default_benchmark_csv_path() -> str:
    return str(results_dir() / "recall_benchmarks.csv")


def _write_benchmark_row(*, benchmark, row: dict[str, object]) -> None:
    csv_path = (
        os.environ.get("BENCHMARK_RESULTS_CSV_PATH") or _default_benchmark_csv_path()
    )
    stats = getattr(benchmark, "stats", None)
    row_out: dict[str, object] = dict(row)
    row_out["timestamp_utc"] = datetime.datetime.now(datetime.UTC).isoformat()

    for key in (
        "mean",
        "stddev",
        "median",
        "min",
        "max",
        "rounds",
        "iterations",
        "ops",
    ):
        value = getattr(stats, key, None) if stats is not None else None
        if value is not None:
            row_out[key] = value

    header = [
        "timestamp_utc",
        "test",
        "db",
        "fact_count",
        "query_size",
        "retrieval_limit",
        "one_shot_seconds",
        "peak_rss_bytes",
        "mean",
        "stddev",
        "median",
        "min",
        "max",
        "rounds",
        "iterations",
        "ops",
    ]
    append_csv_row(csv_path, header=header, row=row_out)


@pytest.mark.benchmark
class TestQueryEmbeddingBenchmarks:
    """Benchmarks for query embedding generation."""

    def test_benchmark_query_embedding_short(self, benchmark, sample_queries):
        """Benchmark embedding generation for short queries."""
        query = sample_queries["short"][0]
        cfg = Config()

        def _embed():
            return embed_texts(
                query,
                model=cfg.embeddings.model,
                fallback_dimension=cfg.embeddings.fallback_dimension,
            )

        start = perf_counter()
        result = benchmark(_embed)
        one_shot_seconds = perf_counter() - start
        assert len(result) > 0
        assert len(result[0]) > 0
        _write_benchmark_row(
            benchmark=benchmark,
            row={
                "test": "query_embedding_short",
                "db": "",
                "fact_count": "",
                "query_size": "short",
                "retrieval_limit": "",
                "one_shot_seconds": one_shot_seconds,
                "peak_rss_bytes": benchmark.extra_info.get("peak_rss_bytes", ""),
            },
        )

    def test_benchmark_query_embedding_medium(self, benchmark, sample_queries):
        """Benchmark embedding generation for medium-length queries."""
        query = sample_queries["medium"][0]
        cfg = Config()

        def _embed():
            return embed_texts(
                query,
                model=cfg.embeddings.model,
                fallback_dimension=cfg.embeddings.fallback_dimension,
            )

        start = perf_counter()
        result = benchmark(_embed)
        one_shot_seconds = perf_counter() - start
        assert len(result) > 0
        assert len(result[0]) > 0
        _write_benchmark_row(
            benchmark=benchmark,
            row={
                "test": "query_embedding_medium",
                "db": "",
                "fact_count": "",
                "query_size": "medium",
                "retrieval_limit": "",
                "one_shot_seconds": one_shot_seconds,
                "peak_rss_bytes": benchmark.extra_info.get("peak_rss_bytes", ""),
            },
        )

    def test_benchmark_query_embedding_long(self, benchmark, sample_queries):
        """Benchmark embedding generation for long queries."""
        query = sample_queries["long"][0]
        cfg = Config()

        def _embed():
            return embed_texts(
                query,
                model=cfg.embeddings.model,
                fallback_dimension=cfg.embeddings.fallback_dimension,
            )

        start = perf_counter()
        result = benchmark(_embed)
        one_shot_seconds = perf_counter() - start
        assert len(result) > 0
        assert len(result[0]) > 0
        _write_benchmark_row(
            benchmark=benchmark,
            row={
                "test": "query_embedding_long",
                "db": "",
                "fact_count": "",
                "query_size": "long",
                "retrieval_limit": "",
                "one_shot_seconds": one_shot_seconds,
                "peak_rss_bytes": benchmark.extra_info.get("peak_rss_bytes", ""),
            },
        )

    def test_benchmark_query_embedding_batch(self, benchmark, sample_queries):
        """Benchmark embedding generation for multiple queries at once."""
        queries = sample_queries["short"][:5]
        cfg = Config()

        def _embed():
            return embed_texts(
                queries,
                model=cfg.embeddings.model,
                fallback_dimension=cfg.embeddings.fallback_dimension,
            )

        start = perf_counter()
        result = benchmark(_embed)
        one_shot_seconds = perf_counter() - start
        assert len(result) == len(queries)
        assert all(len(emb) > 0 for emb in result)
        _write_benchmark_row(
            benchmark=benchmark,
            row={
                "test": "query_embedding_batch",
                "db": "",
                "fact_count": "",
                "query_size": "batch",
                "retrieval_limit": "",
                "one_shot_seconds": one_shot_seconds,
                "peak_rss_bytes": benchmark.extra_info.get("peak_rss_bytes", ""),
            },
        )


@pytest.mark.benchmark
class TestDatabaseEmbeddingRetrievalBenchmarks:
    """Benchmarks for database embedding retrieval."""

    def test_benchmark_db_embedding_retrieval(
        self, benchmark, memori_instance, entity_with_n_facts
    ):
        """Benchmark retrieving embeddings from database for different fact counts."""
        entity_db_id = entity_with_n_facts["entity_db_id"]
        fact_count = entity_with_n_facts["fact_count"]
        entity_fact_driver = memori_instance.config.storage.driver.entity_fact

        def _retrieve():
            return entity_fact_driver.get_embeddings(entity_db_id, limit=fact_count)

        _, peak_rss = measure_peak_rss_bytes(_retrieve)
        if peak_rss is not None:
            benchmark.extra_info["peak_rss_bytes"] = peak_rss

        result = benchmark(_retrieve)
        assert len(result) == fact_count
        assert all("id" in row and "content_embedding" in row for row in result)
        _write_benchmark_row(
            benchmark=benchmark,
            row={
                "test": "db_embedding_retrieval",
                "db": entity_with_n_facts["db_type"],
                "fact_count": fact_count,
                "query_size": "",
                "retrieval_limit": "",
                "one_shot_seconds": "",
                "peak_rss_bytes": benchmark.extra_info.get("peak_rss_bytes", ""),
            },
        )


@pytest.mark.benchmark
class TestDatabaseFactContentRetrievalBenchmarks:
    """Benchmarks for fetching fact content by ids (final recall DB step).

    This benchmarks the final step after semantic search has already identified
    the top-k most similar embeddings. We only retrieve content for those top results
    (typically 5-10 facts), not all facts in the database.
    """

    @pytest.mark.parametrize("retrieval_limit", [5, 10], ids=["limit5", "limit10"])
    def test_benchmark_db_fact_content_retrieval(
        self, benchmark, memori_instance, entity_with_n_facts, retrieval_limit
    ):
        """Benchmark retrieving content for top-k facts after semantic search.

        Args:
            retrieval_limit: Number of fact IDs to retrieve content for (after semantic
                search has already filtered to top results). This should be small (5-10).
        """
        entity_db_id = entity_with_n_facts["entity_db_id"]
        entity_fact_driver = memori_instance.config.storage.driver.entity_fact

        # Simulate semantic search returning top-k IDs (outside benchmark timing)
        # In real flow: get_embeddings(embeddings_limit=1000) -> FAISS search -> top-k IDs
        seed_rows = entity_fact_driver.get_embeddings(
            entity_db_id, limit=retrieval_limit
        )
        fact_ids = [row["id"] for row in seed_rows]

        def _retrieve():
            return entity_fact_driver.get_facts_by_ids(fact_ids)

        _, peak_rss = measure_peak_rss_bytes(_retrieve)
        if peak_rss is not None:
            benchmark.extra_info["peak_rss_bytes"] = peak_rss

        result = benchmark(_retrieve)
        assert len(result) == len(fact_ids)
        assert all("id" in row and "content" in row for row in result)
        _write_benchmark_row(
            benchmark=benchmark,
            row={
                "test": "db_fact_content_retrieval",
                "db": entity_with_n_facts["db_type"],
                "fact_count": entity_with_n_facts["fact_count"],
                "query_size": "",
                "retrieval_limit": retrieval_limit,
                "one_shot_seconds": "",
                "peak_rss_bytes": benchmark.extra_info.get("peak_rss_bytes", ""),
            },
        )


@pytest.mark.benchmark
class TestSemanticSearchBenchmarks:
    """Benchmarks for semantic search (FAISS similarity search)."""

    def test_benchmark_semantic_search(
        self, benchmark, memori_instance, entity_with_n_facts, sample_queries
    ):
        """Benchmark FAISS similarity search for different embedding counts."""
        entity_db_id = entity_with_n_facts["entity_db_id"]
        fact_count = entity_with_n_facts["fact_count"]
        entity_fact_driver = memori_instance.config.storage.driver.entity_fact

        # Pre-fetch embeddings (not part of benchmark)
        db_results = entity_fact_driver.get_embeddings(entity_db_id, limit=fact_count)
        embeddings = [(row["id"], row["content_embedding"]) for row in db_results]

        # Pre-generate query embedding (not part of benchmark)
        query = sample_queries["short"][0]
        query_embedding = embed_texts(
            query,
            model=memori_instance.config.embeddings.model,
            fallback_dimension=memori_instance.config.embeddings.fallback_dimension,
        )[0]

        # Benchmark only the similarity search
        def _search():
            return find_similar_embeddings(embeddings, query_embedding, limit=5)

        _, peak_rss = measure_peak_rss_bytes(_search)
        if peak_rss is not None:
            benchmark.extra_info["peak_rss_bytes"] = peak_rss

        result = benchmark(_search)
        assert len(result) > 0
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
        assert all(
            isinstance(item[0], int) and isinstance(item[1], float) for item in result
        )
        _write_benchmark_row(
            benchmark=benchmark,
            row={
                "test": "semantic_search_faiss",
                "db": entity_with_n_facts["db_type"],
                "fact_count": fact_count,
                "query_size": "short",
                "retrieval_limit": "",
                "one_shot_seconds": "",
                "peak_rss_bytes": benchmark.extra_info.get("peak_rss_bytes", ""),
            },
        )


@pytest.mark.benchmark
class TestEndToEndRecallBenchmarks:
    """Benchmarks for end-to-end recall (embed query + DB + FAISS + content fetch)."""

    @pytest.mark.parametrize(
        "query_size",
        ["short", "medium", "long"],
        ids=["short_query", "medium_query", "long_query"],
    )
    def test_benchmark_end_to_end_recall(
        self,
        benchmark,
        memori_instance,
        entity_with_n_facts,
        sample_queries,
        query_size,
    ):
        entity_db_id = entity_with_n_facts["entity_db_id"]
        query = sample_queries[query_size][0]

        recall = Recall(memori_instance.config)

        def _recall():
            return recall.search_facts(query=query, limit=5, entity_id=entity_db_id)

        _, peak_rss = measure_peak_rss_bytes(_recall)
        if peak_rss is not None:
            benchmark.extra_info["peak_rss_bytes"] = peak_rss

        start = perf_counter()
        result = benchmark(_recall)
        one_shot_seconds = perf_counter() - start
        assert isinstance(result, list)
        assert len(result) <= 5
        _write_benchmark_row(
            benchmark=benchmark,
            row={
                "test": "end_to_end_recall",
                "db": entity_with_n_facts["db_type"],
                "fact_count": entity_with_n_facts["fact_count"],
                "query_size": query_size,
                "retrieval_limit": "",
                "one_shot_seconds": one_shot_seconds,
                "peak_rss_bytes": benchmark.extra_info.get("peak_rss_bytes", ""),
            },
        )
