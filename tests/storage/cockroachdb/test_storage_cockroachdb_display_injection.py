from memori.storage.cockroachdb._display import Display


class DummyFiles:
    def __init__(self):
        self.called = True


def test_files_injection():
    dummy = DummyFiles()
    d = Display(files=dummy)
    assert d.files is dummy
