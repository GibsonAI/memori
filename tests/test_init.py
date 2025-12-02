import pytest

from memori import Memori


def test_attribution_exceptions(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback"])
    mock_conn.__module__ = "psycopg"
    type(mock_conn).__module__ = "psycopg"
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)

    with pytest.raises(RuntimeError) as e:
        Memori(conn=lambda: mock_conn).attribution(entity_id="a" * 101)

    assert str(e.value) == "entity_id cannot be greater than 100 characters"

    with pytest.raises(RuntimeError) as e:
        Memori(conn=lambda: mock_conn).attribution(process_id="a" * 101)

    assert str(e.value) == "process_id cannot be greater than 100 characters"


def test_new_session(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback"])
    mock_conn.__module__ = "psycopg"
    type(mock_conn).__module__ = "psycopg"
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)

    mem = Memori(conn=lambda: mock_conn)

    session_id = mem.config.session_id
    assert session_id is not None

    mem.new_session()

    assert mem.config.session_id is not None
    assert mem.config.session_id != session_id


def test_set_session(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback"])
    mock_conn.__module__ = "psycopg"
    type(mock_conn).__module__ = "psycopg"
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)

    mem = Memori(conn=lambda: mock_conn).set_session(
        "66cf2a0b-7503-4dcd-b717-b29c826fa1db"
    )
    assert mem.config.session_id == "66cf2a0b-7503-4dcd-b717-b29c826fa1db"


def test_set_session_resets_cache(mocker):
    mock_conn = mocker.Mock(spec=["cursor", "commit", "rollback"])
    mock_conn.__module__ = "psycopg"
    type(mock_conn).__module__ = "psycopg"
    mock_cursor = mocker.MagicMock()
    mock_conn.cursor = mocker.MagicMock(return_value=mock_cursor)

    mem = Memori(conn=lambda: mock_conn)
    mem.config.cache.conversation_id = 123
    mem.config.cache.session_id = 456

    mem.new_session()

    assert mem.config.cache.conversation_id is None
    assert mem.config.cache.session_id is None
