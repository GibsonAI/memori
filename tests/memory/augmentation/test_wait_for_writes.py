import sqlite3
import threading
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from memori._config import Config
from memori.memory.augmentation import _db_writer, _manager
from memori.memory.augmentation._db_writer import DbWriterRuntime, WriteTask
from memori.memory.augmentation._manager import Manager
from memori.storage.adapters.dbapi._adapter import Adapter
from memori.storage.migrations._sqlite import migrations


def make_writer(monkeypatch):
    writer = DbWriterRuntime()
    writer.configure(
        SimpleNamespace(
            db_writer_batch_size=10,
            db_writer_batch_timeout=0.01,
            db_writer_queue_size=10,
        )
    )
    monkeypatch.setattr(_manager, "get_db_writer", lambda: writer)
    return writer, Manager(Config())


@pytest.fixture
def pending_commit(tmp_path, monkeypatch):
    database = tmp_path / "memory.sqlite3"
    with sqlite3.connect(database) as conn:
        for step in migrations[1]:
            conn.execute(step["operation"])
    conn.close()

    started = threading.Event()
    release = threading.Event()
    commit = Adapter.commit

    def gated_commit(adapter):
        started.set()
        if not release.wait(5):
            raise RuntimeError("test did not release the commit")
        return commit(adapter)

    monkeypatch.setattr(Adapter, "commit", gated_commit)
    writer, manager = make_writer(monkeypatch)
    assert writer.enqueue_write(
        WriteTask(
            conn_factory=lambda: sqlite3.connect(database),
            method_path="entity.create",
            args=("remember-me",),
        )
    )
    errors = []

    def drain():
        try:
            writer._drain_batches()
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=drain)
    worker.start()
    try:
        assert started.wait(3)
        yield SimpleNamespace(
            writer=writer,
            manager=manager,
            release=release,
            worker=worker,
            database=database,
        )
    finally:
        release.set()
        worker.join(5)
        assert not worker.is_alive()
        assert errors == []


@pytest.mark.parametrize("timeout", [0, 0.03])
def test_wait_times_out_until_sqlite_commit_finishes(pending_commit, timeout):
    state = pending_commit
    assert state.writer.queue.empty()
    with sqlite3.connect(state.database) as reader:
        assert reader.execute("SELECT COUNT(*) FROM memori_entity").fetchone()[0] == 0
    reader.close()

    assert state.manager.wait(timeout=timeout) is False

    state.release.set()
    assert state.manager.wait(timeout=2) is True
    with sqlite3.connect(state.database) as reader:
        assert reader.execute("SELECT external_id FROM memori_entity").fetchall() == [
            ("remember-me",)
        ]
    reader.close()


def test_wait_checks_rust_work_without_a_python_write_queue(monkeypatch, mocker):
    writer = DbWriterRuntime()
    monkeypatch.setattr(_manager, "get_db_writer", lambda: writer)
    config = Config()
    config.rust_core = mocker.Mock()
    config.rust_core.wait_for_augmentation.return_value = False

    assert Manager(config).wait(timeout=0) is False
    config.rust_core.wait_for_augmentation.assert_called_once_with(0)


def test_wait_finishes_after_connection_failure(monkeypatch):
    writer, manager = make_writer(monkeypatch)
    assert writer.enqueue_write(
        WriteTask(conn_factory=lambda: None, method_path="entity.create")
    )
    assert manager.wait(timeout=0) is False

    @contextmanager
    def unavailable_connection(factory):
        raise RuntimeError("database unavailable")
        yield  # pragma: no cover

    monkeypatch.setattr(_db_writer, "connection_context", unavailable_connection)
    with pytest.raises(RuntimeError, match="database unavailable"):
        writer._drain_batches()

    assert manager.wait(timeout=0) is True


def test_wait_times_out_with_queued_work(monkeypatch):
    writer, manager = make_writer(monkeypatch)
    assert writer.enqueue_write(
        WriteTask(conn_factory=lambda: None, method_path="entity.create")
    )
    assert manager.wait(timeout=0.01) is False


def test_wait_succeeds_with_an_empty_writer(monkeypatch):
    _, manager = make_writer(monkeypatch)
    assert manager.wait(timeout=0) is True
