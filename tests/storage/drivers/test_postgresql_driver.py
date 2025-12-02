from unittest.mock import MagicMock
from uuid import UUID

from memori.storage.drivers.postgresql._driver import (
    Conversation,
    ConversationMessage,
    ConversationMessages,
    Driver,
    Entity,
    Process,
    Schema,
    SchemaVersion,
    Session,
)


def test_driver_initialization(mock_conn):
    """Test that Driver initializes all components correctly."""
    driver = Driver(mock_conn)

    assert isinstance(driver.conversation, Conversation)
    assert isinstance(driver.entity, Entity)
    assert isinstance(driver.process, Process)
    assert isinstance(driver.schema, Schema)
    assert isinstance(driver.session, Session)


def test_entity_create(mock_conn, mock_single_result):
    """Test creating a entity record."""
    mock_conn.execute.return_value = mock_single_result({"id": 123})

    entity = Entity(mock_conn)
    result = entity.create("external-entity-id")

    assert result == 123
    assert mock_conn.execute.call_count == 2
    assert mock_conn.commit.call_count == 1

    # Verify INSERT query
    insert_call = mock_conn.execute.call_args_list[0]
    assert "INSERT INTO memori_entity" in insert_call[0][0]
    assert "ON CONFLICT DO NOTHING" in insert_call[0][0]
    assert insert_call[0][1][1] == "external-entity-id"

    # Verify SELECT query
    select_call = mock_conn.execute.call_args_list[1]
    assert "SELECT id" in select_call[0][0]
    assert "FROM memori_entity" in select_call[0][0]
    assert select_call[0][1] == ("external-entity-id",)


def test_entity_generates_uuid(mock_conn, mock_single_result):
    """Test that create generates a valid UUID."""
    mock_conn.execute.return_value = mock_single_result({"id": 123})

    entity = Entity(mock_conn)
    entity.create("external-entity-id")

    # Check that a UUID was generated in the INSERT
    insert_call = mock_conn.execute.call_args_list[0]
    uuid_arg = insert_call[0][1][0]

    # Verify it's a valid UUID string
    UUID(uuid_arg)  # Will raise ValueError if invalid


def test_process_create(mock_conn, mock_single_result):
    """Test creating a process record."""
    mock_conn.execute.return_value = mock_single_result({"id": 456})

    process = Process(mock_conn)
    result = process.create("external-process-id")

    assert result == 456
    assert mock_conn.execute.call_count == 2
    assert mock_conn.commit.call_count == 1

    # Verify INSERT query
    insert_call = mock_conn.execute.call_args_list[0]
    assert "INSERT INTO memori_process" in insert_call[0][0]
    assert "ON CONFLICT DO NOTHING" in insert_call[0][0]
    assert insert_call[0][1][1] == "external-process-id"

    # Verify SELECT query
    select_call = mock_conn.execute.call_args_list[1]
    assert "SELECT id" in select_call[0][0]
    assert "FROM memori_process" in select_call[0][0]
    assert select_call[0][1] == ("external-process-id",)


def test_session_create(mock_conn, mock_single_result):
    """Test creating a session record."""
    mock_conn.execute.return_value = mock_single_result({"id": 789})

    session = Session(mock_conn)
    session_uuid = "test-session-uuid"
    result = session.create(session_uuid, entity_id=123, process_id=456)

    assert result == 789
    assert mock_conn.execute.call_count == 2
    assert mock_conn.commit.call_count == 1

    # Verify INSERT query
    insert_call = mock_conn.execute.call_args_list[0]
    assert "INSERT INTO memori_session" in insert_call[0][0]
    assert "ON CONFLICT DO NOTHING" in insert_call[0][0]
    assert insert_call[0][1] == (session_uuid, 123, 456)

    # Verify SELECT query
    select_call = mock_conn.execute.call_args_list[1]
    assert "SELECT id" in select_call[0][0]
    assert "FROM memori_session" in select_call[0][0]
    assert select_call[0][1] == (session_uuid,)


def test_conversation_initialization(mock_conn):
    """Test that Conversation initializes its sub-components."""
    conversation = Conversation(mock_conn)

    assert isinstance(conversation.message, ConversationMessage)
    assert isinstance(conversation.messages, ConversationMessages)
    assert conversation.conn == mock_conn


def test_conversation_create(mock_conn, mock_single_result):
    """Test creating a conversation record when none exists."""
    mock_empty_result = MagicMock()
    mock_empty_result.mappings.return_value.fetchone.return_value = None
    mock_conn.execute.side_effect = [
        mock_empty_result,
        None,
        mock_single_result({"id": 101}),
    ]

    conversation = Conversation(mock_conn)
    result = conversation.create(session_id=789, timeout_minutes=30)

    assert result == 101
    assert mock_conn.execute.call_count == 3  # Check existing, INSERT, SELECT
    assert mock_conn.commit.call_count == 1

    # Verify check for existing conversation
    check_call = mock_conn.execute.call_args_list[0]
    assert (
        "COALESCE(MAX(m.date_created), c.date_created) as last_activity"
        in check_call[0][0]
    )
    assert check_call[0][1] == (789,)

    # Verify INSERT query
    insert_call = mock_conn.execute.call_args_list[1]
    assert "INSERT INTO memori_conversation" in insert_call[0][0]
    assert "ON CONFLICT DO NOTHING" in insert_call[0][0]

    # Verify the UUID is generated and session_id is passed
    uuid_arg, session_id_arg = insert_call[0][1]
    UUID(uuid_arg)  # Validate UUID
    assert session_id_arg == 789

    # Verify SELECT query
    select_call = mock_conn.execute.call_args_list[2]
    assert "SELECT id" in select_call[0][0]
    assert "FROM memori_conversation" in select_call[0][0]
    assert select_call[0][1] == (789,)


def test_conversation_create_returns_existing_within_timeout(mock_conn):
    """Test returning existing conversation when within timeout period."""
    from datetime import datetime, timedelta

    last_activity = datetime.now() - timedelta(minutes=15)

    mock_existing = MagicMock()
    mock_existing.mappings.return_value.fetchone.return_value = {
        "id": 101,
        "last_activity": last_activity,
    }

    mock_timeout_check = MagicMock()
    mock_timeout_check.fetchone.return_value = [15.0]  # 15 minutes elapsed

    mock_conn.execute.side_effect = [
        mock_existing,  # Existing conversation found
        mock_timeout_check,  # Time check: 15 min < 30 min timeout
    ]

    conversation = Conversation(mock_conn)
    result = conversation.create(session_id=789, timeout_minutes=30)

    assert result == 101  # Returns existing conversation id
    assert mock_conn.execute.call_count == 2  # Check existing, check timeout
    assert mock_conn.commit.call_count == 0  # No insert, no commit


def test_conversation_create_new_when_expired(mock_conn, mock_single_result):
    """Test creating new conversation when existing one is expired."""
    from datetime import datetime, timedelta

    last_activity = datetime.now() - timedelta(minutes=45)

    mock_existing = MagicMock()
    mock_existing.mappings.return_value.fetchone.return_value = {
        "id": 101,
        "last_activity": last_activity,
    }

    mock_timeout_check = MagicMock()
    mock_timeout_check.fetchone.return_value = [45.0]  # 45 minutes elapsed

    mock_conn.execute.side_effect = [
        mock_existing,  # Existing conversation found
        mock_timeout_check,  # Time check: 45 min > 30 min timeout
        None,  # INSERT (no return value needed)
        mock_single_result({"id": 202}),  # SELECT returns new conversation id
    ]

    conversation = Conversation(mock_conn)
    result = conversation.create(session_id=789, timeout_minutes=30)

    assert result == 202  # Returns new conversation id
    assert (
        mock_conn.execute.call_count == 4
    )  # Check existing, check timeout, INSERT, SELECT
    assert mock_conn.commit.call_count == 1  # Committed new conversation


def test_conversation_message_create(mock_conn):
    """Test creating a conversation message."""
    message = ConversationMessage(mock_conn)
    message.create(
        conversation_id=101, role="user", type="text", content="Hello, world!"
    )

    assert mock_conn.execute.call_count == 1

    # Verify INSERT query
    insert_call = mock_conn.execute.call_args_list[0]
    assert "INSERT INTO memori_conversation_message" in insert_call[0][0]

    # Verify parameters
    uuid_arg, conv_id, role, type_, content = insert_call[0][1]
    UUID(uuid_arg)  # Validate UUID
    assert conv_id == 101
    assert role == "user"
    assert type_ == "text"
    assert content == "Hello, world!"


def test_conversation_messages_read(mock_conn, mock_multiple_results):
    """Test reading conversation messages."""
    mock_conn.execute.return_value = mock_multiple_results(
        [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
    )

    messages = ConversationMessages(mock_conn)
    result = messages.read(conversation_id=101)

    assert len(result) == 2
    assert result[0] == {"content": "Hello", "role": "user"}
    assert result[1] == {"content": "Hi there!", "role": "assistant"}

    # Verify SELECT query
    select_call = mock_conn.execute.call_args_list[0]
    assert "SELECT role" in select_call[0][0]
    assert "FROM memori_conversation_message" in select_call[0][0]
    assert select_call[0][1] == (101,)


def test_conversation_messages_read_empty(mock_conn, mock_empty_result):
    """Test reading messages when none exist."""
    mock_conn.execute.return_value = mock_empty_result

    messages = ConversationMessages(mock_conn)
    result = messages.read(conversation_id=999)

    assert result == []


def test_schema_version_create(mock_conn):
    """Test creating a schema version record."""
    schema_version = SchemaVersion(mock_conn)
    schema_version.create(num=1)

    assert mock_conn.execute.call_count == 1

    # Verify INSERT query
    insert_call = mock_conn.execute.call_args_list[0]
    assert "INSERT INTO memori_schema_version" in insert_call[0][0]
    assert insert_call[0][1] == (1,)


def test_schema_version_read(mock_conn, mock_single_result):
    """Test reading the current schema version."""
    mock_conn.execute.return_value = mock_single_result({"num": 5})

    schema_version = SchemaVersion(mock_conn)
    result = schema_version.read()

    assert result == 5

    # Verify SELECT query
    select_call = mock_conn.execute.call_args_list[0]
    assert "SELECT num" in select_call[0][0]
    assert "FROM memori_schema_version" in select_call[0][0]


def test_schema_version_delete(mock_conn):
    """Test deleting schema version records."""
    schema_version = SchemaVersion(mock_conn)
    schema_version.delete()

    assert mock_conn.execute.call_count == 1

    # Verify DELETE query
    delete_call = mock_conn.execute.call_args_list[0]
    assert "DELETE FROM memori_schema_version" in delete_call[0][0]


def test_schema_initialization(mock_conn):
    """Test that Schema initializes SchemaVersion correctly."""
    schema = Schema(mock_conn)

    assert isinstance(schema.version, SchemaVersion)
    assert schema.conn == mock_conn
