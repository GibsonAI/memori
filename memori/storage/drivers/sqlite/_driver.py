r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

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
from memori.storage.migrations._sqlite import migrations


class Conversation(BaseConversation):
    def __init__(self, conn: BaseStorageAdapter):
        super().__init__(conn)
        self.message = ConversationMessage(conn)
        self.messages = ConversationMessages(conn)

    def create(self, session_id, timeout_minutes: int):
        existing = (
            self.conn.execute(
                """
                SELECT c.id,
                       COALESCE(MAX(m.date_created), c.date_created) as last_activity
                  FROM memori_conversation c
                  LEFT JOIN memori_conversation_message m ON m.conversation_id = c.id
                 WHERE c.session_id = ?
                 GROUP BY c.id, c.date_created
                """,
                (session_id,),
            )
            .mappings()
            .fetchone()
        )

        if existing:
            result = self.conn.execute(
                """
                SELECT (julianday('now') - julianday(?)) * 24 * 60 as minutes_since_activity
                """,
                (existing["last_activity"],),
            ).fetchone()

            if result[0] <= timeout_minutes:
                return existing["id"]

        uuid = str(uuid4())
        self.conn.execute(
            """
            INSERT OR IGNORE INTO memori_conversation(
                uuid,
                session_id
            ) VALUES (
                ?,
                ?
            )
            """,
            (uuid, session_id),
        )
        self.conn.commit()

        return (
            self.conn.execute(
                """
                SELECT id
                  FROM memori_conversation
                 WHERE session_id = ?
                """,
                (session_id,),
            )
            .mappings()
            .fetchone()
            .get("id", None)
        )

    def update(self, id: int, summary: str):
        if summary is None:
            return self

        self.conn.execute(
            """
            UPDATE memori_conversation
               SET summary = ?
             WHERE id = ?
            """,
            (
                summary,
                id,
            ),
        )
        self.conn.commit()

        return self

    def read(self, id: int) -> dict | None:
        result = (
            self.conn.execute(
                """
                SELECT id, uuid, session_id, summary, date_created, date_updated
                  FROM memori_conversation
                 WHERE id = ?
                """,
                (id,),
            )
            .mappings()
            .fetchone()
        )

        if result is None:
            return None

        return dict(result)


class ConversationMessage(BaseConversationMessage):
    def create(self, conversation_id: int, role: str, type: str, content: str):
        self.conn.execute(
            """
            INSERT INTO memori_conversation_message(
                uuid,
                conversation_id,
                role,
                type,
                content
            ) VALUES (
                ?,
                ?,
                ?,
                ?,
                ?
            )
            """,
            (
                str(uuid4()),
                conversation_id,
                role,
                type,
                content,
            ),
        )


class ConversationMessages(BaseConversationMessages):
    def read(self, conversation_id: int):
        results = (
            self.conn.execute(
                """
                SELECT role,
                       content
                  FROM memori_conversation_message
                 WHERE conversation_id = ?
                 ORDER BY id
                """,
                (conversation_id,),
            )
            .mappings()
            .fetchall()
        )

        messages = []
        for result in results:
            messages.append({"content": result["content"], "role": result["role"]})

        return messages


class Entity(BaseEntity):
    def create(self, external_id: str):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO memori_entity(
                uuid,
                external_id
            ) VALUES (
                ?,
                ?
            )
            """,
            (str(uuid4()), external_id),
        )
        self.conn.commit()

        return (
            self.conn.execute(
                """
                SELECT id
                  FROM memori_entity
                 WHERE external_id = ?
                """,
                (external_id,),
            )
            .mappings()
            .fetchone()
            .get("id", None)
        )


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
            embedding_formatted = format_embedding_for_db(embedding, "sqlite")
            uniq = generate_uniq([fact])

            self.conn.execute(
                """
                INSERT INTO memori_entity_fact(
                    uuid,
                    entity_id,
                    content,
                    content_embedding,
                    num_times,
                    date_last_time,
                    uniq
                ) VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    datetime('now'),
                    ?
                )
                ON CONFLICT(entity_id, uniq) DO UPDATE SET
                    num_times = num_times + 1,
                    date_last_time = datetime('now')
                """,
                (
                    str(uuid4()),
                    entity_id,
                    fact,
                    embedding_formatted,
                    1,
                    uniq,
                ),
            )

        self.conn.commit()

        return self

    def get_embeddings(self, entity_id: int, limit: int = 1000):
        return (
            self.conn.execute(
                """
                SELECT id,
                       content_embedding
                  FROM memori_entity_fact
                 WHERE entity_id = ?
                 LIMIT ?
                """,
                (entity_id, limit),
            )
            .mappings()
            .fetchall()
        )

    def get_facts_by_ids(self, fact_ids: list[int]):
        if not fact_ids:
            return []
        placeholders = ",".join(["?"] * len(fact_ids))

        query = f"""
                SELECT id,
                       content
                  FROM memori_entity_fact
                 WHERE id IN ({placeholders})
                """  # nosec B608: Safe - only interpolating placeholder count, actual values parameterized
        return self.conn.execute(query, tuple(fact_ids)).mappings().fetchall()


class KnowledgeGraph(BaseKnowledgeGraph):
    def create(self, entity_id: int, semantic_triples: list):
        if semantic_triples is None or len(semantic_triples) == 0:
            return self

        from memori._utils import generate_uniq

        for semantic_triple in semantic_triples:
            # Insert or get subject
            subject_uniq = generate_uniq(
                [semantic_triple.subject_name, semantic_triple.subject_type]
            )

            self.conn.execute(
                """
                INSERT OR IGNORE INTO memori_subject(
                    uuid,
                    name,
                    type,
                    uniq
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    semantic_triple.subject_name,
                    semantic_triple.subject_type,
                    subject_uniq,
                ),
            )
            self.conn.commit()

            subject_id = (
                self.conn.execute(
                    "SELECT id FROM memori_subject WHERE uniq = ?",
                    (subject_uniq,),
                )
                .mappings()
                .fetchone()
                .get("id", None)
            )

            # Insert or get predicate
            predicate_uniq = generate_uniq([semantic_triple.predicate])

            self.conn.execute(
                """
                INSERT OR IGNORE INTO memori_predicate(
                    uuid,
                    content,
                    uniq
                ) VALUES (?, ?, ?)
                """,
                (
                    str(uuid4()),
                    semantic_triple.predicate,
                    predicate_uniq,
                ),
            )
            self.conn.commit()

            predicate_id = (
                self.conn.execute(
                    "SELECT id FROM memori_predicate WHERE uniq = ?",
                    (predicate_uniq,),
                )
                .mappings()
                .fetchone()
                .get("id", None)
            )

            # Insert or get object
            object_uniq = generate_uniq(
                [semantic_triple.object_name, semantic_triple.object_type]
            )

            self.conn.execute(
                """
                INSERT OR IGNORE INTO memori_object(
                    uuid,
                    name,
                    type,
                    uniq
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    str(uuid4()),
                    semantic_triple.object_name,
                    semantic_triple.object_type,
                    object_uniq,
                ),
            )
            self.conn.commit()

            object_id = (
                self.conn.execute(
                    "SELECT id FROM memori_object WHERE uniq = ?",
                    (object_uniq,),
                )
                .mappings()
                .fetchone()
                .get("id", None)
            )

            # Insert or update knowledge graph entry
            if (
                entity_id is not None
                and subject_id is not None
                and predicate_id is not None
                and object_id is not None
            ):
                self.conn.execute(
                    """
                    INSERT INTO memori_knowledge_graph(
                        uuid,
                        entity_id,
                        subject_id,
                        predicate_id,
                        object_id,
                        num_times,
                        date_last_time
                    ) VALUES (?, ?, ?, ?, ?, 1, datetime('now'))
                    ON CONFLICT(entity_id, subject_id, predicate_id, object_id) DO UPDATE SET
                        num_times = num_times + 1,
                        date_last_time = datetime('now')
                    """,
                    (str(uuid4()), entity_id, subject_id, predicate_id, object_id),
                )
                self.conn.commit()

        return self


class Process(BaseProcess):
    def create(self, external_id: str):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO memori_process(
                uuid,
                external_id
            ) VALUES (
                ?,
                ?
            )
            """,
            (str(uuid4()), external_id),
        )
        self.conn.commit()

        return (
            self.conn.execute(
                """
                SELECT id
                  FROM memori_process
                 WHERE external_id = ?
                """,
                (external_id,),
            )
            .mappings()
            .fetchone()
            .get("id", None)
        )


class ProcessAttribute(BaseProcessAttribute):
    def create(self, process_id: int, attributes: list):
        if attributes is None or len(attributes) == 0:
            return self

        from memori._utils import generate_uniq

        for attribute in attributes:
            uniq = generate_uniq([attribute])

            self.conn.execute(
                """
                INSERT INTO memori_process_attribute(
                    uuid,
                    process_id,
                    content,
                    num_times,
                    date_last_time,
                    uniq
                ) VALUES (?, ?, ?, 1, datetime('now'), ?)
                ON CONFLICT(process_id, uniq) DO UPDATE SET
                    num_times = num_times + 1,
                    date_last_time = datetime('now')
                """,
                (str(uuid4()), process_id, attribute, uniq),
            )

        self.conn.commit()
        return self


class Session(BaseSession):
    def create(self, uuid: str, entity_id: int, process_id: int):
        self.conn.execute(
            """
            INSERT OR IGNORE INTO memori_session(
                uuid,
                entity_id,
                process_id
            ) VALUES (
                ?,
                ?,
                ?
            )
            """,
            (str(uuid), entity_id, process_id),
        )
        self.conn.commit()

        return (
            self.conn.execute(
                """
                SELECT id
                  FROM memori_session
                 WHERE uuid = ?
                """,
                (str(uuid),),
            )
            .mappings()
            .fetchone()
            .get("id", None)
        )


class Schema(BaseSchema):
    def __init__(self, conn: BaseStorageAdapter):
        super().__init__(conn)
        self.version = SchemaVersion(conn)


class SchemaVersion(BaseSchemaVersion):
    def create(self, num: int):
        self.conn.execute(
            """
            INSERT INTO memori_schema_version(
                num
            ) VALUES (
                ?
            )
            """,
            (num,),
        )

    def delete(self):
        self.conn.execute(
            """
            DELETE FROM memori_schema_version
            """
        )

    def read(self):
        return (
            self.conn.execute(
                """
                SELECT num
                  FROM memori_schema_version
                """
            )
            .mappings()
            .fetchone()
            .get("num", None)
        )


@Registry.register_driver("sqlite")
class Driver:
    """SQLite storage driver.

    Attributes:
        migrations: Database schema migrations for SQLite.
        requires_rollback_on_error: SQLite does not abort transactions on query
            errors, so no rollback is needed to continue executing queries.
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
