from memori.storage.cockroachdb._display import Display


class DummyFilesWithID:
    def __init__(self, id="cluster-123"):
        self._id = id

    def read_id(self):
        return self._id


class DummyFilesNoID:
    def read_id(self):
        return None


def test_banner_contains_branding():
    assert "perfectam memoriam" in Display().banner()


def test_cluster_status_when_started():
    d = Display(files=DummyFilesWithID())
    out = d.cluster_status()
    assert "active CockroachDB cluster id" in out
    assert "cluster-123" in out
    assert "cluster delete" in out


def test_cluster_status_when_not_started():
    d = Display(files=DummyFilesNoID())
    assert d.cluster_status() == d.cluster_was_not_started()


def test_connection_string_when_started():
    d = Display(files=DummyFilesWithID())
    assert "cockroach sql" in d.connection_string()
    assert "cluster-123" in d.connection_string()


def test_connection_string_when_not_started():
    d = Display(files=DummyFilesNoID())
    assert "No active CockroachDB cluster found" in d.connection_string()
