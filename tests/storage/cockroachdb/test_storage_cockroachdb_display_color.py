from memori.storage.cockroachdb._display import Display


class DummyFilesWithID:
    def __init__(self, id="cluster-xyz"):
        self._id = id

    def read_id(self):
        return self._id


def test_colorize_connection_string_has_ansi():
    d = Display(files=DummyFilesWithID(), colorize=True)
    cs = d.connection_string()
    assert "cockroach sql" in cs
    assert "\x1b[" in cs


def test_no_color_by_default():
    d = Display(files=DummyFilesWithID())
    cs = d.connection_string()
    assert "cockroach sql" in cs
    assert "\x1b[" not in cs


def test_example_block_when_started_colorized():
    d = Display(files=DummyFilesWithID(), colorize=True)
    blk = d.example_connection_block()
    assert "To connect to your cluster" in blk
    assert "\x1b[" in blk


def test_example_block_when_not_started():
    d = Display(files=type("F", (), {"read_id": lambda self: None})())
    blk = d.example_connection_block()
    assert "Start a cluster first" in blk
