from memori.storage.cockroachdb._display import Display


def test_cluster_already_started():
    assert Display().cluster_already_started() == (
        """You already have an active CockroachDB cluster running. To start
  a new one, execute this command first:

    python -m memori cockroachdb cluster delete
"""
    )


def test_cluster_was_not_started():
    assert Display().cluster_was_not_started() == (
        """You do not have an active CockroachDB cluster running. To start
  a new one, execute this command first:

    python -m memori cockroachdb cluster start
"""
    )
