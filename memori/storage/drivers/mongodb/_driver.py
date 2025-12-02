r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

from datetime import datetime, timezone
from uuid import uuid4

from memori.storage._base import (
    BaseConversation,
    BaseConversationMessage,
    BaseConversationMessages,
    BaseEntity,
    BaseEntityFact,
    BaseKnowledgeGraph,
    BaseProcess,
    BaseProcessAttribute,
    BaseSchema,
    BaseSchemaVersion,
    BaseSession,
    BaseStorageAdapter,
)
from memori.storage._registry import Registry
from memori.storage.migrations._mongodb import migrations


class Conversation(BaseConversation):
    def __init__(self, conn: BaseStorageAdapter):
        super().__init__(conn)
        self.message = ConversationMessage(conn)
        self.messages = ConversationMessages(conn)

    def create(self, session_id, timeout_minutes: int):
        existing = self.conn.execute(
            "memori_conversation", "find_one", {"session_id": session_id}
        )

        if existing:
            last_message = self.conn.execute(
                "memori_conversation_message",
                "find_one",
                {"conversation_id": existing["_id"]},
                sort=[("date_created", -1)],
            )

            last_activity = (
                last_message["date_created"]
                if last_message
                else existing["date_created"]
            )

            now = datetime.now(timezone.utc)
            minutes_elapsed = (now - last_activity).total_seconds() / 60

            if minutes_elapsed <= timeout_minutes:
                return existing.get("_id")

        conversation_uuid = str(uuid4())
        conversation_doc = {
            "uuid": conversation_uuid,
            "session_id": session_id,
            "summary": None,
            "date_created": datetime.now(timezone.utc),
            "date_updated": None,
        }

        result = self.conn.execute(
            "memori_conversation", "insert_one", conversation_doc
        )

        return result.inserted_id

    def update(self, id: int, summary: str):
        if summary is None:
            return self

        self.conn.execute(
            "memori_conversation",
            "update_one",
            {"_id": id},
            {"$set": {"summary": summary}},
        )

        return self

    def read(self, id: int) -> dict | None:
        result = self.conn.execute(
            "memori_conversation",
            "find_one",
            {"_id": id},
        )

        if result is None:
            return None

        # Convert MongoDB result to dict, excluding _id or converting it to id
        conversation = dict(result)
        if "_id" in conversation:
            conversation["id"] = conversation.pop("_id")

        return conversation


class ConversationMessage(BaseConversationMessage):
    def create(self, conversation_id: int, role: str, type: str, content: str):
        message_doc = {
            "uuid": str(uuid4()),
            "conversation_id": conversation_id,
            "role": role,
            "type": type,
            "content": content,
            "date_created": datetime.now(timezone.utc),
            "date_updated": None,
        }

        self.conn.execute("memori_conversation_message", "insert_one", message_doc)


class ConversationMessages(BaseConversationMessages):
    def read(self, conversation_id: int):
        results = self.conn.execute(
            "memori_conversation_message",
            "find",
            {"conversation_id": conversation_id},
            {"role": 1, "content": 1, "_id": 0},
        )

        messages = []
        for result in results:
            messages.append({"content": result["content"], "role": result["role"]})

        return messages


class Entity(BaseEntity):
    def create(self, external_id: str):
        # Check if entity already exists
        existing = self.conn.execute(
            "memori_entity", "find_one", {"external_id": external_id}
        )

        if existing:
            return existing.get("_id")

        # Create new entity
        entity_doc = {
            "uuid": str(uuid4()),
            "external_id": external_id,
            "date_created": datetime.now(timezone.utc),
            "date_updated": None,
        }

        result = self.conn.execute("memori_entity", "insert_one", entity_doc)

        return result.inserted_id


class EntityFact(BaseEntityFact):
    def create(self, entity_id: int, facts: list, fact_embeddings: list | None = None):
        if facts is None or len(facts) == 0:
            return self

        from memori._utils import generate_uniq
        from memori.llm._embeddings import format_embedding_for_db

        for i, fact in enumerate(facts):
            embedding = (
                fact_embeddings[i]
                if fact_embeddings and i < len(fact_embeddings)
                else []
            )
            embedding_formatted = format_embedding_for_db(embedding, "mongodb")
            uniq = generate_uniq([fact])

            # Check if fact already exists
            existing = self.conn.execute(
                "memori_entity_fact",
                "find_one",
                {"entity_id": entity_id, "uniq": uniq},
            )

            if existing:
                # Update existing fact
                self.conn.execute(
                    "memori_entity_fact",
                    "update_one",
                    {"_id": existing["_id"]},
                    {
                        "$inc": {"num_times": 1},
                        "$set": {"date_last_time": datetime.now(timezone.utc)},
                    },
                )
            else:
                # Insert new fact
                fact_doc = {
                    "uuid": str(uuid4()),
                    "entity_id": entity_id,
                    "content": fact,
                    "content_embedding": embedding_formatted,
                    "num_times": 1,
                    "date_last_time": datetime.now(timezone.utc),
                    "uniq": uniq,
                    "date_created": datetime.now(timezone.utc),
                    "date_updated": None,
                }

                self.conn.execute("memori_entity_fact", "insert_one", fact_doc)

        return self

    def get_embeddings(self, entity_id: int, limit: int = 1000):
        results = self.conn.execute(
            "memori_entity_fact",
            "find",
            {"entity_id": entity_id},
            {"_id": 1, "content_embedding": 1},
        )

        embeddings = []
        for result in list(results)[:limit]:
            embeddings.append(
                {"id": result["_id"], "content_embedding": result["content_embedding"]}
            )

        return embeddings

    def get_facts_by_ids(self, fact_ids: list[int]):
        if not fact_ids:
            return []

        results = self.conn.execute(
            "memori_entity_fact",
            "find",
            {"_id": {"$in": fact_ids}},
            {"_id": 1, "content": 1},
        )

        facts = []
        for result in results:
            facts.append({"id": result["_id"], "content": result["content"]})

        return facts


class KnowledgeGraph(BaseKnowledgeGraph):
    def create(self, entity_id: int, semantic_triples: list):
        if semantic_triples is None or len(semantic_triples) == 0:
            return self

        from datetime import datetime, timezone

        from memori._utils import generate_uniq

        for semantic_triple in semantic_triples:
            # Insert or get subject
            subject_uniq = generate_uniq(
                [semantic_triple.subject_name, semantic_triple.subject_type]
            )
            existing_subject = self.conn.execute(
                "memori_subject", "find_one", {"uniq": subject_uniq}
            )

            if existing_subject:
                subject_id = existing_subject["_id"]
            else:
                subject_doc = {
                    "uuid": str(uuid4()),
                    "name": semantic_triple.subject_name,
                    "type": semantic_triple.subject_type,
                    "uniq": subject_uniq,
                    "date_created": datetime.now(timezone.utc),
                    "date_updated": None,
                }
                result = self.conn.execute("memori_subject", "insert_one", subject_doc)
                subject_id = result.inserted_id

            # Insert or get predicate
            predicate_uniq = generate_uniq([semantic_triple.predicate])
            existing_predicate = self.conn.execute(
                "memori_predicate", "find_one", {"uniq": predicate_uniq}
            )

            if existing_predicate:
                predicate_id = existing_predicate["_id"]
            else:
                predicate_doc = {
                    "uuid": str(uuid4()),
                    "content": semantic_triple.predicate,
                    "uniq": predicate_uniq,
                    "date_created": datetime.now(timezone.utc),
                    "date_updated": None,
                }
                result = self.conn.execute(
                    "memori_predicate", "insert_one", predicate_doc
                )
                predicate_id = result.inserted_id

            # Insert or get object
            object_uniq = generate_uniq(
                [semantic_triple.object_name, semantic_triple.object_type]
            )
            existing_object = self.conn.execute(
                "memori_object", "find_one", {"uniq": object_uniq}
            )

            if existing_object:
                object_id = existing_object["_id"]
            else:
                object_doc = {
                    "uuid": str(uuid4()),
                    "name": semantic_triple.object_name,
                    "type": semantic_triple.object_type,
                    "uniq": object_uniq,
                    "date_created": datetime.now(timezone.utc),
                    "date_updated": None,
                }
                result = self.conn.execute("memori_object", "insert_one", object_doc)
                object_id = result.inserted_id

            # Insert or update knowledge graph entry
            if (
                entity_id is not None
                and subject_id is not None
                and predicate_id is not None
                and object_id is not None
            ):
                existing_kg = self.conn.execute(
                    "memori_knowledge_graph",
                    "find_one",
                    {
                        "entity_id": entity_id,
                        "subject_id": subject_id,
                        "predicate_id": predicate_id,
                        "object_id": object_id,
                    },
                )

                if existing_kg:
                    self.conn.execute(
                        "memori_knowledge_graph",
                        "update_one",
                        {"_id": existing_kg["_id"]},
                        {
                            "$inc": {"num_times": 1},
                            "$set": {"date_last_time": datetime.now(timezone.utc)},
                        },
                    )
                else:
                    kg_doc = {
                        "uuid": str(uuid4()),
                        "entity_id": entity_id,
                        "subject_id": subject_id,
                        "predicate_id": predicate_id,
                        "object_id": object_id,
                        "num_times": 1,
                        "date_last_time": datetime.now(timezone.utc),
                        "date_created": datetime.now(timezone.utc),
                        "date_updated": None,
                    }
                    self.conn.execute("memori_knowledge_graph", "insert_one", kg_doc)

        return self


class Process(BaseProcess):
    def create(self, external_id: str):
        # Check if process already exists
        existing = self.conn.execute(
            "memori_process", "find_one", {"external_id": external_id}
        )

        if existing:
            return existing.get("_id")

        # Create new process
        process_doc = {
            "uuid": str(uuid4()),
            "external_id": external_id,
            "date_created": datetime.now(timezone.utc),
            "date_updated": None,
        }

        result = self.conn.execute("memori_process", "insert_one", process_doc)

        return result.inserted_id


class ProcessAttribute(BaseProcessAttribute):
    def create(self, process_id: int, attributes: list):
        if attributes is None or len(attributes) == 0:
            return self

        from datetime import datetime, timezone

        from memori._utils import generate_uniq

        for attribute in attributes:
            uniq = generate_uniq([attribute])
            existing = self.conn.execute(
                "memori_process_attribute",
                "find_one",
                {"process_id": process_id, "uniq": uniq},
            )

            if existing:
                self.conn.execute(
                    "memori_process_attribute",
                    "update_one",
                    {"_id": existing["_id"]},
                    {
                        "$inc": {"num_times": 1},
                        "$set": {"date_last_time": datetime.now(timezone.utc)},
                    },
                )
            else:
                attribute_doc = {
                    "uuid": str(uuid4()),
                    "process_id": process_id,
                    "content": attribute,
                    "num_times": 1,
                    "date_last_time": datetime.now(timezone.utc),
                    "uniq": uniq,
                    "date_created": datetime.now(timezone.utc),
                    "date_updated": None,
                }
                self.conn.execute(
                    "memori_process_attribute", "insert_one", attribute_doc
                )

        return self


class Session(BaseSession):
    def create(self, uuid: str, entity_id: int, process_id: int):
        # Check if session already exists
        existing = self.conn.execute("memori_session", "find_one", {"uuid": str(uuid)})

        if existing:
            return existing.get("_id")

        # Create new session
        session_doc = {
            "uuid": str(uuid),
            "entity_id": entity_id,
            "process_id": process_id,
            "date_created": datetime.now(timezone.utc),
            "date_updated": None,
        }

        result = self.conn.execute("memori_session", "insert_one", session_doc)

        return result.inserted_id


class Schema(BaseSchema):
    def __init__(self, conn: BaseStorageAdapter):
        super().__init__(conn)
        self.version = SchemaVersion(conn)


class SchemaVersion(BaseSchemaVersion):
    def create(self, num: int):
        schema_doc = {"num": num}

        self.conn.execute("memori_schema_version", "insert_one", schema_doc)

    def delete(self):
        self.conn.execute("memori_schema_version", "delete_many", {})

    def read(self):
        result = self.conn.execute(
            "memori_schema_version", "find_one", {}, {"num": 1, "_id": 0}
        )

        if not result:
            return None

        return result.get("num")


@Registry.register_driver("mongodb")
class Driver:
    """MongoDB storage driver.

    Attributes:
        migrations: Database schema migrations for MongoDB.
        requires_rollback_on_error: MongoDB does not abort transactions on query
            errors by default, so no rollback is needed to continue executing queries.
    """

    migrations = migrations
    requires_rollback_on_error = False

    def __init__(self, conn: BaseStorageAdapter):
        self.conversation = Conversation(conn)
        self.entity = Entity(conn)
        self.entity_fact = EntityFact(conn)
        self.knowledge_graph = KnowledgeGraph(conn)
        self.process = Process(conn)
        self.process_attribute = ProcessAttribute(conn)
        self.schema = Schema(conn)
        self.session = Session(conn)
