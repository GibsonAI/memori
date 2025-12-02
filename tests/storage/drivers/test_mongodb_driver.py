from datetime import datetime
from unittest.mock import Mock
from uuid import UUID

from memori.storage.drivers.mongodb._driver import (
    Conversation,
    ConversationMessage,
    ConversationMessages,
    Driver,
    Entity,
    EntityFact,
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
    assert isinstance(driver.entity_fact, EntityFact)
    assert isinstance(driver.process, Process)
    assert isinstance(driver.schema, Schema)
    assert isinstance(driver.session, Session)


def test_entity_create(mock_conn):
    """Test creating a entity record."""
    # Mock the find_one to return None (no existing record)
    mock_conn.execute.side_effect = [
        None,  # find_one returns None (no existing record)
        Mock(inserted_id=123),  # insert_one returns mock result
    ]

    entity = Entity(mock_conn)
    result = entity.create("external-entity-id")

    assert result == 123
    assert mock_conn.execute.call_count == 2  # find_one, insert_one

    # Verify find_one query for existing record
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_entity"
    assert find_call[0][1] == "find_one"
    assert find_call[0][2] == {"external_id": "external-entity-id"}

    # Verify insert_one query
    insert_call = mock_conn.execute.call_args_list[1]
    assert insert_call[0][0] == "memori_entity"
    assert insert_call[0][1] == "insert_one"
    doc = insert_call[0][2]
    assert doc["external_id"] == "external-entity-id"
    assert "uuid" in doc
    assert "date_created" in doc


def test_entity_create_existing_record(mock_conn):
    """Test creating a entity record when it already exists."""
    # Mock the find_one to return existing record
    existing_record = Mock()
    existing_record.get.return_value = 456
    mock_conn.execute.return_value = existing_record

    entity = Entity(mock_conn)
    result = entity.create("external-entity-id")

    assert result == 456
    assert mock_conn.execute.call_count == 1  # Only find_one


def test_entity_generates_uuid(mock_conn):
    """Test that create generates a valid UUID."""
    mock_conn.execute.side_effect = [
        None,  # find_one returns None
        Mock(inserted_id=123),  # insert_one returns mock result
    ]

    entity = Entity(mock_conn)
    entity.create("external-entity-id")

    # Check that a UUID was generated in the insert_one
    insert_call = mock_conn.execute.call_args_list[1]
    doc = insert_call[0][2]
    uuid_str = doc["uuid"]

    # Verify it's a valid UUID string
    UUID(uuid_str)  # Will raise ValueError if invalid


def test_process_create(mock_conn):
    """Test creating a process record."""
    mock_conn.execute.side_effect = [
        None,  # find_one returns None
        Mock(inserted_id=456),  # insert_one returns mock result
    ]

    process = Process(mock_conn)
    result = process.create("external-process-id")

    assert result == 456
    assert mock_conn.execute.call_count == 2

    # Verify find_one query
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_process"
    assert find_call[0][1] == "find_one"
    assert find_call[0][2] == {"external_id": "external-process-id"}

    # Verify insert_one query
    insert_call = mock_conn.execute.call_args_list[1]
    assert insert_call[0][0] == "memori_process"
    assert insert_call[0][1] == "insert_one"
    doc = insert_call[0][2]
    assert doc["external_id"] == "external-process-id"


def test_session_create(mock_conn):
    """Test creating a session record."""
    mock_conn.execute.side_effect = [
        None,  # find_one returns None
        Mock(inserted_id=789),  # insert_one returns mock result
    ]

    session = Session(mock_conn)
    session_uuid = "test-session-uuid"
    result = session.create(session_uuid, entity_id=123, process_id=456)

    assert result == 789
    assert mock_conn.execute.call_count == 2

    # Verify find_one query
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_session"
    assert find_call[0][1] == "find_one"
    assert find_call[0][2] == {"uuid": "test-session-uuid"}

    # Verify insert_one query
    insert_call = mock_conn.execute.call_args_list[1]
    assert insert_call[0][0] == "memori_session"
    assert insert_call[0][1] == "insert_one"
    doc = insert_call[0][2]
    assert doc["uuid"] == "test-session-uuid"
    assert doc["entity_id"] == 123
    assert doc["process_id"] == 456


def test_conversation_initialization(mock_conn):
    """Test that Conversation initializes its sub-components."""
    conversation = Conversation(mock_conn)

    assert isinstance(conversation.message, ConversationMessage)
    assert isinstance(conversation.messages, ConversationMessages)
    assert conversation.conn == mock_conn


def test_conversation_create(mock_conn):
    """Test creating a conversation record when none exists."""
    mock_conn.execute.side_effect = [
        None,  # find_one returns None (no existing conversation)
        Mock(inserted_id=101),  # insert_one returns mock result
    ]

    conversation = Conversation(mock_conn)
    result = conversation.create(session_id=789, timeout_minutes=30)

    assert result == 101
    assert mock_conn.execute.call_count == 2

    # Verify find_one query
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_conversation"
    assert find_call[0][1] == "find_one"
    assert find_call[0][2] == {"session_id": 789}

    # Verify insert_one query
    insert_call = mock_conn.execute.call_args_list[1]
    assert insert_call[0][0] == "memori_conversation"
    assert insert_call[0][1] == "insert_one"
    doc = insert_call[0][2]
    assert doc["session_id"] == 789
    assert doc["summary"] is None
    assert "uuid" in doc


def test_conversation_create_returns_existing_within_timeout(mock_conn):
    """Test returning existing conversation when within timeout period."""
    from datetime import datetime, timedelta, timezone

    last_activity = datetime.now(timezone.utc) - timedelta(minutes=15)

    # Mock: existing conversation and last message
    existing_conversation = {
        "_id": 999,
        "session_id": 789,
        "date_created": datetime.now(timezone.utc) - timedelta(minutes=20),
    }
    last_message = {"date_created": last_activity}

    mock_conn.execute.side_effect = [
        existing_conversation,  # find_one for conversation
        last_message,  # find_one for last message
    ]

    conversation = Conversation(mock_conn)
    result = conversation.create(session_id=789, timeout_minutes=30)

    assert result == 999  # Returns existing conversation id
    assert mock_conn.execute.call_count == 2  # Check conversation, check last message


def test_conversation_create_new_when_expired(mock_conn):
    """Test creating new conversation when existing one is expired."""
    from datetime import datetime, timedelta, timezone

    last_activity = datetime.now(timezone.utc) - timedelta(minutes=45)

    # Mock: existing conversation but expired
    existing_conversation = {
        "_id": 999,
        "session_id": 789,
        "date_created": datetime.now(timezone.utc) - timedelta(minutes=50),
    }
    last_message = {"date_created": last_activity}

    mock_conn.execute.side_effect = [
        existing_conversation,  # find_one for conversation
        last_message,  # find_one for last message (expired)
        Mock(inserted_id=202),  # insert_one returns new conversation
    ]

    conversation = Conversation(mock_conn)
    result = conversation.create(session_id=789, timeout_minutes=30)

    assert result == 202  # Returns new conversation id
    assert (
        mock_conn.execute.call_count == 3
    )  # Check conversation, check last message, insert new  # Only find_one


def test_conversation_message_create(mock_conn):
    """Test creating a conversation message."""
    message = ConversationMessage(mock_conn)
    message.create(
        conversation_id=101, role="user", type="text", content="Hello, world!"
    )

    assert mock_conn.execute.call_count == 1

    # Verify insert_one query
    insert_call = mock_conn.execute.call_args_list[0]
    assert insert_call[0][0] == "memori_conversation_message"
    assert insert_call[0][1] == "insert_one"
    doc = insert_call[0][2]

    assert doc["conversation_id"] == 101
    assert doc["role"] == "user"
    assert doc["type"] == "text"
    assert doc["content"] == "Hello, world!"
    assert "uuid" in doc
    assert "date_created" in doc


def test_conversation_messages_read(mock_conn):
    """Test reading conversation messages."""
    # Mock the find query to return cursor with messages
    mock_cursor = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    mock_conn.execute.return_value = mock_cursor

    messages = ConversationMessages(mock_conn)
    result = messages.read(conversation_id=101)

    assert len(result) == 2
    assert result[0] == {"content": "Hello", "role": "user"}
    assert result[1] == {"content": "Hi there!", "role": "assistant"}

    # Verify find query
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_conversation_message"
    assert find_call[0][1] == "find"
    assert find_call[0][2] == {"conversation_id": 101}
    assert find_call[0][3] == {"role": 1, "content": 1, "_id": 0}


def test_conversation_messages_read_empty(mock_conn):
    """Test reading messages when none exist."""
    mock_conn.execute.return_value = []

    messages = ConversationMessages(mock_conn)
    result = messages.read(conversation_id=999)

    assert result == []


def test_schema_version_create(mock_conn):
    """Test creating a schema version record."""
    schema_version = SchemaVersion(mock_conn)
    schema_version.create(num=1)

    assert mock_conn.execute.call_count == 1

    # Verify insert_one query
    insert_call = mock_conn.execute.call_args_list[0]
    assert insert_call[0][0] == "memori_schema_version"
    assert insert_call[0][1] == "insert_one"
    doc = insert_call[0][2]
    assert doc["num"] == 1


def test_schema_version_read(mock_conn):
    """Test reading the current schema version."""
    mock_result = {"num": 5}
    mock_conn.execute.return_value = mock_result

    schema_version = SchemaVersion(mock_conn)
    result = schema_version.read()

    assert result == 5

    # Verify find_one query
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_schema_version"
    assert find_call[0][1] == "find_one"
    assert find_call[0][2] == {}
    assert find_call[0][3] == {"num": 1, "_id": 0}


def test_schema_version_read_none(mock_conn):
    """Test reading schema version when none exists."""
    mock_conn.execute.return_value = None

    schema_version = SchemaVersion(mock_conn)
    result = schema_version.read()

    assert result is None


def test_schema_version_delete(mock_conn):
    """Test deleting schema version records."""
    schema_version = SchemaVersion(mock_conn)
    schema_version.delete()

    assert mock_conn.execute.call_count == 1

    # Verify delete_many query
    delete_call = mock_conn.execute.call_args_list[0]
    assert delete_call[0][0] == "memori_schema_version"
    assert delete_call[0][1] == "delete_many"
    assert delete_call[0][2] == {}


def test_schema_initialization(mock_conn):
    """Test that Schema initializes SchemaVersion correctly."""
    schema = Schema(mock_conn)

    assert isinstance(schema.version, SchemaVersion)
    assert schema.conn == mock_conn


def test_driver_migrations_attribute():
    """Test that Driver has migrations attribute."""
    from memori.storage.drivers.mongodb._driver import Driver
    from memori.storage.migrations._mongodb import migrations

    assert Driver.migrations == migrations


def test_driver_requires_rollback_on_error_attribute():
    """Test that Driver has requires_rollback_on_error attribute."""
    from memori.storage.drivers.mongodb._driver import Driver

    assert Driver.requires_rollback_on_error is False


def test_driver_registry_registration():
    """Test that Driver is properly registered with the registry."""
    from memori.storage._registry import Registry

    registry = Registry()
    assert "mongodb" in registry._drivers


def test_mongodb_operations_with_datetime(mock_conn):
    """Test that MongoDB operations properly handle datetime fields."""
    mock_conn.execute.side_effect = [
        None,  # find_one returns None
        Mock(inserted_id=123),  # insert_one returns mock result
    ]

    entity = Entity(mock_conn)
    entity.create("external-entity-id")

    # Verify insert_one query includes date_created
    insert_call = mock_conn.execute.call_args_list[1]
    doc = insert_call[0][2]

    assert "date_created" in doc
    assert isinstance(doc["date_created"], datetime)
    assert doc["date_updated"] is None


def test_mongodb_conversation_message_with_datetime(mock_conn):
    """Test that conversation message creation includes proper datetime fields."""
    message = ConversationMessage(mock_conn)
    message.create(
        conversation_id=101, role="user", type="text", content="Test message"
    )

    # Verify insert_one query includes date_created
    insert_call = mock_conn.execute.call_args_list[0]
    doc = insert_call[0][2]

    assert "date_created" in doc
    assert isinstance(doc["date_created"], datetime)
    assert doc["date_updated"] is None


def test_mongodb_session_with_datetime(mock_conn):
    """Test that session creation includes proper datetime fields."""
    mock_conn.execute.side_effect = [
        None,  # find_one returns None
        Mock(inserted_id=789),  # insert_one returns mock result
    ]

    session = Session(mock_conn)
    session.create("test-uuid", entity_id=123, process_id=456)

    # Verify insert_one query includes date_created
    insert_call = mock_conn.execute.call_args_list[1]
    doc = insert_call[0][2]

    assert "date_created" in doc
    assert isinstance(doc["date_created"], datetime)
    assert doc["date_updated"] is None


def test_entity_fact_create_new_fact(mock_conn, mocker):
    """Test creating a new entity fact."""
    from unittest.mock import Mock

    mocker.patch("memori._utils.generate_uniq", return_value="uniq123")
    # Mock bson.Binary for MongoDB
    mock_binary = Mock()
    mock_binary.__repr__ = lambda self: "Binary(...)"
    mocker.patch(
        "memori.llm._embeddings.format_embedding_for_db",
        return_value=mock_binary,
    )

    mock_conn.execute.return_value = None  # No existing fact

    entity_fact = EntityFact(mock_conn)
    facts = ["User likes Python"]
    embeddings = [[0.1, 0.2, 0.3]]

    result = entity_fact.create(entity_id=123, facts=facts, fact_embeddings=embeddings)

    assert result == entity_fact
    assert mock_conn.execute.call_count == 2  # find_one, insert_one

    # Verify find_one query
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_entity_fact"
    assert find_call[0][1] == "find_one"
    assert find_call[0][2] == {"entity_id": 123, "uniq": "uniq123"}

    # Verify insert_one query
    insert_call = mock_conn.execute.call_args_list[1]
    assert insert_call[0][0] == "memori_entity_fact"
    assert insert_call[0][1] == "insert_one"
    doc = insert_call[0][2]
    assert doc["entity_id"] == 123
    assert doc["content"] == "User likes Python"
    # content_embedding is now a Mock object representing bson.Binary
    assert doc["content_embedding"] is not None
    assert doc["num_times"] == 1
    assert doc["uniq"] == "uniq123"
    assert "uuid" in doc
    assert "date_created" in doc
    assert isinstance(doc["date_created"], datetime)


def test_entity_fact_create_existing_fact(mock_conn, mocker):
    """Test updating an existing entity fact."""
    from unittest.mock import Mock

    mocker.patch("memori._utils.generate_uniq", return_value="uniq123")
    mock_binary = Mock()
    mocker.patch(
        "memori.llm._embeddings.format_embedding_for_db",
        return_value=mock_binary,
    )

    # Mock existing fact
    existing = {"_id": 999, "num_times": 5}
    mock_conn.execute.return_value = existing

    entity_fact = EntityFact(mock_conn)
    facts = ["User likes Python"]
    embeddings = [[0.1, 0.2, 0.3]]

    result = entity_fact.create(entity_id=123, facts=facts, fact_embeddings=embeddings)

    assert result == entity_fact
    assert mock_conn.execute.call_count == 2  # find_one, update_one

    # Verify find_one query
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_entity_fact"
    assert find_call[0][1] == "find_one"

    # Verify update_one query
    update_call = mock_conn.execute.call_args_list[1]
    assert update_call[0][0] == "memori_entity_fact"
    assert update_call[0][1] == "update_one"
    assert update_call[0][2] == {"_id": 999}
    update_doc = update_call[0][3]
    assert "$inc" in update_doc
    assert update_doc["$inc"]["num_times"] == 1
    assert "$set" in update_doc
    assert "date_last_time" in update_doc["$set"]
    assert isinstance(update_doc["$set"]["date_last_time"], datetime)


def test_entity_fact_create_empty_facts(mock_conn):
    """Test creating entity facts with empty list."""
    entity_fact = EntityFact(mock_conn)
    result = entity_fact.create(entity_id=123, facts=[], fact_embeddings=None)

    assert result == entity_fact
    assert mock_conn.execute.call_count == 0


def test_entity_fact_create_multiple_facts(mock_conn, mocker):
    """Test creating multiple entity facts."""
    from unittest.mock import Mock

    mocker.patch(
        "memori._utils.generate_uniq",
        side_effect=["uniq1", "uniq2"],
    )
    mock_binary1 = Mock()
    mock_binary2 = Mock()
    mocker.patch(
        "memori.llm._embeddings.format_embedding_for_db",
        side_effect=[mock_binary1, mock_binary2],
    )

    mock_conn.execute.side_effect = [None, None, None, None]  # No existing facts

    entity_fact = EntityFact(mock_conn)
    facts = ["Fact 1", "Fact 2"]
    embeddings = [[0.1, 0.2], [0.3, 0.4]]

    entity_fact.create(entity_id=123, facts=facts, fact_embeddings=embeddings)

    # Should be 4 calls: find_one, insert_one for each fact
    assert mock_conn.execute.call_count == 4


def test_entity_fact_create_without_embeddings(mock_conn, mocker):
    """Test creating entity facts without embeddings."""
    from unittest.mock import Mock

    mocker.patch("memori._utils.generate_uniq", return_value="uniq123")
    mock_binary = Mock()
    mocker.patch(
        "memori.llm._embeddings.format_embedding_for_db",
        return_value=mock_binary,
    )

    mock_conn.execute.return_value = None

    entity_fact = EntityFact(mock_conn)
    facts = ["User likes Python"]

    entity_fact.create(entity_id=123, facts=facts, fact_embeddings=None)

    # Verify embedding was formatted (as Mock object representing bson.Binary)
    insert_call = mock_conn.execute.call_args_list[1]
    doc = insert_call[0][2]
    assert doc["content_embedding"] is not None


def test_entity_fact_get_embeddings(mock_conn):
    """Test retrieving embeddings for an entity."""
    mock_cursor = [
        {"_id": 1, "content_embedding": b"\x00\x01\x02\x03"},
        {"_id": 2, "content_embedding": b"\x04\x05\x06\x07"},
    ]
    mock_conn.execute.return_value = mock_cursor

    entity_fact = EntityFact(mock_conn)
    result = entity_fact.get_embeddings(entity_id=123, limit=100)

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["content_embedding"] == b"\x00\x01\x02\x03"
    assert result[1]["id"] == 2
    assert result[1]["content_embedding"] == b"\x04\x05\x06\x07"

    # Verify find query
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_entity_fact"
    assert find_call[0][1] == "find"
    assert find_call[0][2] == {"entity_id": 123}
    assert find_call[0][3] == {"_id": 1, "content_embedding": 1}


def test_entity_fact_get_embeddings_with_limit(mock_conn):
    """Test retrieving embeddings respects the limit."""
    # Return more results than the limit
    mock_cursor = [{"_id": i, "content_embedding": bytes([i])} for i in range(1, 11)]
    mock_conn.execute.return_value = mock_cursor

    entity_fact = EntityFact(mock_conn)
    result = entity_fact.get_embeddings(entity_id=123, limit=5)

    # Should only return first 5 results
    assert len(result) == 5
    assert result[0]["id"] == 1
    assert result[4]["id"] == 5


def test_entity_fact_get_embeddings_default_limit(mock_conn):
    """Test retrieving embeddings with default limit."""
    mock_conn.execute.return_value = []

    entity_fact = EntityFact(mock_conn)
    entity_fact.get_embeddings(entity_id=123)

    # Verify default limit is used in slicing (1000)
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_entity_fact"


def test_entity_fact_get_facts_by_ids(mock_conn):
    """Test retrieving fact content by IDs."""
    mock_cursor = [
        {"_id": 1, "content": "User likes Python"},
        {"_id": 2, "content": "User works as engineer"},
    ]
    mock_conn.execute.return_value = mock_cursor

    entity_fact = EntityFact(mock_conn)
    result = entity_fact.get_facts_by_ids([1, 2])

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["content"] == "User likes Python"
    assert result[1]["id"] == 2
    assert result[1]["content"] == "User works as engineer"

    # Verify find query
    find_call = mock_conn.execute.call_args_list[0]
    assert find_call[0][0] == "memori_entity_fact"
    assert find_call[0][1] == "find"
    assert find_call[0][2] == {"_id": {"$in": [1, 2]}}
    assert find_call[0][3] == {"_id": 1, "content": 1}


def test_entity_fact_get_facts_by_ids_empty(mock_conn):
    """Test retrieving facts with empty IDs list."""
    entity_fact = EntityFact(mock_conn)
    result = entity_fact.get_facts_by_ids([])

    assert result == []
    assert mock_conn.execute.call_count == 0
