"""Pytest fixtures for performance benchmarks."""

import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from memori import Memori
from memori.llm._embeddings import embed_texts
from tests.benchmarks.fixtures.sample_data import (
    generate_facts,
    generate_facts_with_size,
    generate_sample_queries,
)


@pytest.fixture
def sqlite_db_connection():
    """Create a temporary SQLite database connection factory for benchmarking."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    sqlite_uri = f"sqlite:///{db_path}"
    engine = create_engine(
        sqlite_uri,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield Session

    engine.dispose()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def postgres_db_connection():
    """Create a PostgreSQL database connection factory for benchmarking (via Docker)."""
    postgres_uri = os.environ.get(
        "BENCHMARK_POSTGRES_URL",
        # Matches docker-compose.yml default DB name
        "postgresql://memori:memori@localhost:5432/memori_test",
    )

    from sqlalchemy import text

    engine = create_engine(postgres_uri, pool_pre_ping=True, pool_recycle=300)

    # Try to connect to the target database. We don't auto-create databases here
    # because hosted/managed Postgres users often lack CREATEDB permissions.
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(
            f"PostgreSQL not available at {postgres_uri}: {e}. "
            "Set BENCHMARK_POSTGRES_URL to a database that exists."
        )

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield Session
    engine.dispose()


@pytest.fixture
def cockroachdb_connection():
    """Create a CockroachDB connection factory for benchmarking (hosted instance)."""
    cockroachdb_uri = os.environ.get("BENCHMARK_COCKROACHDB_URL")

    if not cockroachdb_uri:
        pytest.skip("BENCHMARK_COCKROACHDB_URL environment variable not set")

    import psycopg

    def get_connection():
        return psycopg.connect(cockroachdb_uri)

    # Test connection
    try:
        conn = get_connection()
        conn.close()
    except Exception as e:
        pytest.skip(f"CockroachDB not available: {e}")

    yield get_connection


@pytest.fixture(
    params=["sqlite", "postgres", "cockroachdb"],
    ids=["sqlite", "postgres", "cockroachdb"],
)
def db_connection(request):
    """Parameterized fixture for different database types."""
    db_type = request.param

    if db_type == "sqlite":
        return request.getfixturevalue("sqlite_db_connection")
    elif db_type == "postgres":
        return request.getfixturevalue("postgres_db_connection")
    elif db_type == "cockroachdb":
        return request.getfixturevalue("cockroachdb_connection")

    pytest.skip(f"Unknown database type: {db_type}")


@pytest.fixture
def memori_instance(db_connection, request):
    """Create a Memori instance with the specified database for benchmarking."""
    mem = Memori(conn=db_connection)
    mem.config.storage.build()

    # Store database type for later reference
    db_type_param = None
    for marker in request.node.iter_markers("parametrize"):
        if "db_connection" in marker.args[0]:
            db_type_param = marker.args[1][0] if marker.args[1] else None
            break

    # Try to infer from connection
    if not db_type_param:
        try:
            # SQLAlchemy sessionmaker is callable, so detect it first by presence of a bind.
            bind = getattr(db_connection, "kw", {}).get("bind", None)
            if bind is not None:
                db_type_param = bind.dialect.name
            else:
                # Fallback: assume callable non-sessionmaker is cockroach factory.
                # (We only use a raw callable for cockroachdb in these benchmarks.)
                db_type_param = "cockroachdb" if callable(db_connection) else "unknown"
        except Exception:
            db_type_param = "unknown"

    mem._benchmark_db_type = db_type_param
    return mem


@pytest.fixture
def sample_queries():
    """Provide sample queries of varying lengths."""
    return generate_sample_queries()


@pytest.fixture
def entity_with_facts(memori_instance):
    """Create an entity with pre-populated facts for benchmarking."""
    entity_id = "benchmark-entity-123"
    memori_instance.attribution(entity_id=entity_id, process_id="benchmark-process")

    facts = generate_facts(100)
    fact_embeddings = embed_texts(facts)

    entity_db_id = memori_instance.config.storage.driver.entity.create(entity_id)
    memori_instance.config.storage.driver.entity_fact.create(
        entity_db_id, facts, fact_embeddings
    )

    return {
        "entity_id": entity_id,
        "entity_db_id": entity_db_id,
        "fact_count": len(facts),
    }


@pytest.fixture
def entity_with_small_facts(memori_instance):
    """Create an entity with a small number of facts (10-100)."""
    entity_id = "benchmark-entity-small"
    memori_instance.attribution(entity_id=entity_id, process_id="benchmark-process")

    facts = generate_facts(50)
    fact_embeddings = embed_texts(facts)

    entity_db_id = memori_instance.config.storage.driver.entity.create(entity_id)
    memori_instance.config.storage.driver.entity_fact.create(
        entity_db_id, facts, fact_embeddings
    )

    return {
        "entity_id": entity_id,
        "entity_db_id": entity_db_id,
        "fact_count": len(facts),
    }


@pytest.fixture
def entity_with_medium_facts(memori_instance):
    """Create an entity with a medium number of facts (100-1,000)."""
    entity_id = "benchmark-entity-medium"
    memori_instance.attribution(entity_id=entity_id, process_id="benchmark-process")

    facts = generate_facts(500)
    fact_embeddings = embed_texts(facts)

    entity_db_id = memori_instance.config.storage.driver.entity.create(entity_id)
    memori_instance.config.storage.driver.entity_fact.create(
        entity_db_id, facts, fact_embeddings
    )

    return {
        "entity_id": entity_id,
        "entity_db_id": entity_db_id,
        "fact_count": len(facts),
    }


@pytest.fixture
def entity_with_large_facts(memori_instance):
    """Create an entity with a large number of facts (1,000-10,000)."""
    entity_id = "benchmark-entity-large"
    memori_instance.attribution(entity_id=entity_id, process_id="benchmark-process")

    facts = generate_facts(5000)
    fact_embeddings = embed_texts(facts)

    entity_db_id = memori_instance.config.storage.driver.entity.create(entity_id)
    memori_instance.config.storage.driver.entity_fact.create(
        entity_db_id, facts, fact_embeddings
    )

    return {
        "entity_id": entity_id,
        "entity_db_id": entity_db_id,
        "fact_count": len(facts),
    }


@pytest.fixture(params=["small", "medium", "large"], ids=["small", "medium", "large"])
def fact_content_size(request):
    """Parameterized fixture for different fact content sizes.

    Note: Embeddings are always 768 dimensions (3072 bytes binary) regardless of text size.
    This tests how text content size affects database retrieval when combined with
    fixed-size binary embeddings.
    """
    return request.param


@pytest.fixture(
    params=[5, 50, 100, 300, 600, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000],
    ids=lambda x: f"n{x}",
)
def entity_with_n_facts(memori_instance, fact_content_size, request):
    """Create an entity with N facts for benchmarking database retrieval."""
    fact_count = request.param
    entity_id = f"benchmark-entity-{fact_count}-{fact_content_size}"
    memori_instance.attribution(entity_id=entity_id, process_id="benchmark-process")

    facts = generate_facts_with_size(fact_count, fact_content_size)
    fact_embeddings = embed_texts(facts)

    entity_db_id = memori_instance.config.storage.driver.entity.create(entity_id)
    memori_instance.config.storage.driver.entity_fact.create(
        entity_db_id, facts, fact_embeddings
    )

    db_type = getattr(memori_instance, "_benchmark_db_type", "unknown")

    return {
        "entity_id": entity_id,
        "entity_db_id": entity_db_id,
        "fact_count": fact_count,
        "content_size": fact_content_size,
        "db_type": db_type,
        # Include ground-truth facts for accuracy evaluation.
        # (Used by tests; not timed by benchmarks.)
        "facts": facts,
    }
