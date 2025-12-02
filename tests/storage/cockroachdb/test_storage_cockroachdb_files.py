import os

import pytest

from memori.storage.cockroachdb._files import Files


def test_storage_dir_exceptions():
    try:
        del os.environ["HOME"]
    except KeyError:
        pass

    try:
        del os.environ["MEMORI_HOME"]
    except KeyError:
        pass

    with pytest.raises(RuntimeError) as e:
        Files().storage_dir()

    assert str(e.value) == "neither MEMORI_HOME nor HOME environment variable is set"


def test_storage_dir_home():
    os.environ["HOME"] = "/abc"
    assert Files().storage_dir() == "/abc/.memori"


def test_storage_dir_memori_home():
    os.environ["MEMORI_HOME"] = "/def"
    assert Files().storage_dir() == "/def/.memori"


def test_cluster_dir():
    os.environ["MEMORI_HOME"] = "/def"
    assert Files().cluster_dir() == "/def/.memori/cluster"


def test_cluster_id():
    os.environ["MEMORI_HOME"] = "/def"
    assert Files().cluster_id() == "/def/.memori/cluster/id"


def test_read_id_no_such_file():
    os.environ["MEMORI_HOME"] = "/tmp"
    assert Files().read_id() is None


def test_write_id():
    os.environ["MEMORI_HOME"] = "/tmp"

    cluster_id = Files().cluster_id()

    try:
        Files().write_id("abcdef")

        assert os.path.isfile(cluster_id)
    finally:
        try:
            os.unlink(cluster_id)
        except FileNotFoundError:
            pass


def test_write_then_read_id():
    os.environ["MEMORI_HOME"] = "/tmp"

    cluster_id = Files().cluster_id()

    try:
        Files().write_id("abcdef")

        assert os.path.isfile(cluster_id)
        assert Files().read_id() == "abcdef"
    finally:
        try:
            os.unlink(cluster_id)
        except FileNotFoundError:
            pass


def test_remove_id():
    os.environ["MEMORI_HOME"] = "/tmp"

    cluster_id = Files().cluster_id()

    try:
        Files().write_id("abcdef")
        assert os.path.isfile(cluster_id)

        Files().remove_id()
        assert not os.path.isfile(cluster_id)
    finally:
        try:
            os.unlink(cluster_id)
        except FileNotFoundError:
            pass
