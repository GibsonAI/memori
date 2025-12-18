"""Pytest fixtures for performance benchmarks."""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from memori import Memori
from memori.llm._embeddings import embed_texts
from tests.benchmarks.fixtures.sample_data import (
    generate_facts_with_size,
    generate_sample_queries,
)


@pytest.fixture
def postgres_db_connection():
    """Create a PostgreSQL database connection factory for benchmarking (via AWS/Docker)."""
    postgres_uri = os.environ.get(
        "BENCHMARK_POSTGRES_URL",
        # Matches docker-compose.yml default DB name
        "postgresql://memori:memori@localhost:5432/memori_test",
    )

    from sqlalchemy import text

    # Support SSL root certificate via environment variable (for AWS RDS)
    connect_args = {}
    sslrootcert = os.environ.get("BENCHMARK_POSTGRES_SSLROOTCERT")
    if sslrootcert:
        connect_args["sslrootcert"] = sslrootcert
        # Ensure sslmode is set if using SSL cert
        if "sslmode" not in postgres_uri:
            # Add sslmode=require if not already in URI
            separator = "&" if "?" in postgres_uri else "?"
            postgres_uri = f"{postgres_uri}{separator}sslmode=require"

    engine = create_engine(
        postgres_uri,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args=connect_args if connect_args else None,
    )

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
def mysql_db_connection():
    """Create a MySQL database connection factory for benchmarking (via AWS/Docker)."""
    mysql_uri = os.environ.get(
        "BENCHMARK_MYSQL_URL",
        "mysql+pymysql://memori:memori@localhost:3306/memori_test",
    )

    from sqlalchemy import text

    engine = create_engine(
        mysql_uri,
        pool_pre_ping=True,
        pool_recycle=300,
    )

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        pytest.skip(f"MySQL not available at {mysql_uri}: {e}")

    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield Session
    engine.dispose()


@pytest.fixture(
    params=["postgres", "mysql"],
    ids=["postgres", "mysql"],
)
def db_connection(request):
    """Parameterized fixture for realistic database types (no SQLite)."""
    db_type = request.param

    if db_type == "postgres":
        return request.getfixturevalue("postgres_db_connection")
    elif db_type == "mysql":
        return request.getfixturevalue("mysql_db_connection")

    pytest.skip(f"Unsupported benchmark database type: {db_type}")


@pytest.fixture
def memori_instance(db_connection, request):
    """Create a Memori instance with the specified database for benchmarking."""
    mem = Memori(conn=db_connection)
    mem.config.storage.build()

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
                db_type_param = "unknown"
        except Exception:
            db_type_param = "unknown"

    mem._benchmark_db_type = db_type_param  # ty: ignore[unresolved-attribute]
    return mem


@pytest.fixture
def sample_queries():
    """Provide sample queries of varying lengths."""
    return generate_sample_queries()


@pytest.fixture
def fact_content_size():
    """Fixture for fact content size.

    Note: Embeddings are always 768 dimensions (3072 bytes binary) regardless of text size.
    """
    return "small"


@pytest.fixture(
    params=[5, 50, 100, 300, 600, 1000],
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
        "facts": facts,
    }
