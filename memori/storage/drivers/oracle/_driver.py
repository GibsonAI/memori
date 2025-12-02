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
from memori.storage.migrations._oracle import migrations


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
                 WHERE c.session_id = :1
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
                SELECT ROUND((CAST(SYSTIMESTAMP AS DATE) - CAST(:1 AS DATE)) * 24 * 60) as minutes_since_activity
                  FROM DUAL
                """,
                (existing["last_activity"],),
            ).fetchone()

            if result and result[0] is not None and result[0] <= timeout_minutes:
                return existing["id"]

        uuid = str(uuid4())
        self.conn.execute(
            """
            MERGE INTO memori_conversation dst
            USING (SELECT :1 AS uuid, :2 AS session_id FROM DUAL) src
            ON (dst.session_id = src.session_id)
            WHEN NOT MATCHED THEN
                INSERT (uuid, session_id)
                VALUES (src.uuid, src.session_id)
            """,
            (
                uuid,
                session_id,
            ),
        )
        self.conn.commit()

        return (
            self.conn.execute(
                """
                SELECT id
                  FROM memori_conversation
                 WHERE session_id = :1
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
               SET summary = :1
             WHERE id = :2
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
                 WHERE id = :1
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
                :1,
                :2,
                :3,
                :4,
                :5
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
                 WHERE conversation_id = :1
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
            MERGE INTO memori_entity dst
            USING (SELECT :1 AS uuid, :2 AS external_id FROM DUAL) src
            ON (dst.external_id = src.external_id)
            WHEN NOT MATCHED THEN
                INSERT (uuid, external_id)
                VALUES (src.uuid, src.external_id)
            """,
            (str(uuid4()), external_id),
        )
        self.conn.commit()

        return (
            self.conn.execute(
                """
                SELECT id
                  FROM memori_entity
                 WHERE external_id = :1
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

        dialect = self.conn.get_dialect()

        for i, fact in enumerate(facts):
            embedding = (
                fact_embeddings[i]
                if fact_embeddings and i < len(fact_embeddings)
                else []
            )
            embedding_formatted = format_embedding_for_db(embedding, dialect)
            uniq = generate_uniq([fact])

            self.conn.execute(
                """
                MERGE INTO memori_entity_fact dst
                USING (SELECT :1 AS uuid, :2 AS entity_id, :3 AS content,
                              :4 AS content_embedding, :5 AS uniq FROM DUAL) src
                ON (dst.entity_id = src.entity_id AND dst.uniq = src.uniq)
                WHEN MATCHED THEN
                    UPDATE SET num_times = dst.num_times + 1,
                               date_last_time = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (uuid, entity_id, content, content_embedding,
                            num_times, date_last_time, uniq)
                    VALUES (src.uuid, src.entity_id, src.content, src.content_embedding,
                            1, SYSTIMESTAMP, src.uniq)
                """,
                (
                    str(uuid4()),
                    entity_id,
                    fact,
                    embedding_formatted,
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
                 WHERE entity_id = :1
                   AND ROWNUM <= :2
                """,
                (entity_id, limit),
            )
            .mappings()
            .fetchall()
        )

    def get_facts_by_ids(self, fact_ids: list[int]):
        if not fact_ids:
            return []

        # Oracle doesn't support ANY, so we need to use IN with placeholders
        placeholders = ",".join([f":{i + 1}" for i in range(len(fact_ids))])
        query = f"""
            SELECT id,
                   content
              FROM memori_entity_fact
             WHERE id IN ({placeholders})
        """

        return self.conn.execute(query, tuple(fact_ids)).mappings().fetchall()


class KnowledgeGraph(BaseKnowledgeGraph):
    def create(self, entity_id: int, semantic_triples: list):
        if semantic_triples is None or len(semantic_triples) == 0:
            return self

        from memori._utils import generate_uniq

        for semantic_triple in semantic_triples:
            uniq = generate_uniq(
                [semantic_triple.subject_name, semantic_triple.subject_type]
            )

            self.conn.execute(
                """
                MERGE INTO memori_subject dst
                USING (SELECT :1 AS uuid, :2 AS name, :3 AS type, :4 AS uniq FROM DUAL) src
                ON (dst.uniq = src.uniq)
                WHEN NOT MATCHED THEN
                    INSERT (uuid, name, type, uniq)
                    VALUES (src.uuid, src.name, src.type, src.uniq)
                """,
                (
                    str(uuid4()),
                    semantic_triple.subject_name,
                    semantic_triple.subject_type,
                    uniq,
                ),
            )
            self.conn.commit()

            subject_id = (
                self.conn.execute(
                    """
                    SELECT id
                      FROM memori_subject
                     WHERE uniq = :1
                    """,
                    (uniq,),
                )
                .mappings()
                .fetchone()
                .get("id", None)
            )

            uniq = generate_uniq([semantic_triple.predicate])

            self.conn.execute(
                """
                MERGE INTO memori_predicate dst
                USING (SELECT :1 AS uuid, :2 AS content, :3 AS uniq FROM DUAL) src
                ON (dst.uniq = src.uniq)
                WHEN NOT MATCHED THEN
                    INSERT (uuid, content, uniq)
                    VALUES (src.uuid, src.content, src.uniq)
                """,
                (
                    str(uuid4()),
                    semantic_triple.predicate,
                    uniq,
                ),
            )
            self.conn.commit()

            predicate_id = (
                self.conn.execute(
                    """
                    SELECT id
                      FROM memori_predicate
                     WHERE uniq = :1
                    """,
                    (uniq,),
                )
                .mappings()
                .fetchone()
                .get("id", None)
            )

            uniq = generate_uniq(
                [semantic_triple.object_name, semantic_triple.object_type]
            )

            self.conn.execute(
                """
                MERGE INTO memori_object dst
                USING (SELECT :1 AS uuid, :2 AS name, :3 AS type, :4 AS uniq FROM DUAL) src
                ON (dst.uniq = src.uniq)
                WHEN NOT MATCHED THEN
                    INSERT (uuid, name, type, uniq)
                    VALUES (src.uuid, src.name, src.type, src.uniq)
                """,
                (
                    str(uuid4()),
                    semantic_triple.object_name,
                    semantic_triple.object_type,
                    uniq,
                ),
            )
            self.conn.commit()

            object_id = (
                self.conn.execute(
                    """
                    SELECT id
                      FROM memori_object
                     WHERE uniq = :1
                    """,
                    (uniq,),
                )
                .mappings()
                .fetchone()
                .get("id", None)
            )

            if (
                entity_id is not None
                and subject_id is not None
                and predicate_id is not None
                and object_id is not None
            ):
                self.conn.execute(
                    """
                    MERGE INTO memori_knowledge_graph dst
                    USING (SELECT :1 AS uuid, :2 AS entity_id, :3 AS subject_id,
                                  :4 AS predicate_id, :5 AS object_id FROM DUAL) src
                    ON (dst.entity_id = src.entity_id AND dst.subject_id = src.subject_id
                        AND dst.predicate_id = src.predicate_id AND dst.object_id = src.object_id)
                    WHEN MATCHED THEN
                        UPDATE SET num_times = dst.num_times + 1,
                                   date_last_time = SYSTIMESTAMP
                    WHEN NOT MATCHED THEN
                        INSERT (uuid, entity_id, subject_id, predicate_id, object_id,
                                num_times, date_last_time)
                        VALUES (src.uuid, src.entity_id, src.subject_id, src.predicate_id,
                                src.object_id, 1, SYSTIMESTAMP)
                    """,
                    (str(uuid4()), entity_id, subject_id, predicate_id, object_id),
                )
                self.conn.commit()

        return self


class Process(BaseProcess):
    def create(self, external_id: str):
        self.conn.execute(
            """
            MERGE INTO memori_process dst
            USING (SELECT :1 AS uuid, :2 AS external_id FROM DUAL) src
            ON (dst.external_id = src.external_id)
            WHEN NOT MATCHED THEN
                INSERT (uuid, external_id)
                VALUES (src.uuid, src.external_id)
            """,
            (str(uuid4()), external_id),
        )
        self.conn.commit()

        return (
            self.conn.execute(
                """
                SELECT id
                  FROM memori_process
                 WHERE external_id = :1
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
                MERGE INTO memori_process_attribute dst
                USING (SELECT :1 AS uuid, :2 AS process_id, :3 AS content, :4 AS uniq FROM DUAL) src
                ON (dst.process_id = src.process_id AND dst.uniq = src.uniq)
                WHEN MATCHED THEN
                    UPDATE SET num_times = dst.num_times + 1,
                               date_last_time = SYSTIMESTAMP
                WHEN NOT MATCHED THEN
                    INSERT (uuid, process_id, content, num_times, date_last_time, uniq)
                    VALUES (src.uuid, src.process_id, src.content, 1, SYSTIMESTAMP, src.uniq)
                """,
                (
                    str(uuid4()),
                    process_id,
                    attribute,
                    uniq,
                ),
            )

        self.conn.commit()
        return self


class Session(BaseSession):
    def create(self, uuid: str, entity_id: int, process_id: int):
        self.conn.execute(
            """
            MERGE INTO memori_session dst
            USING (SELECT :1 AS uuid, :2 AS entity_id, :3 AS process_id FROM DUAL) src
            ON (dst.uuid = src.uuid)
            WHEN NOT MATCHED THEN
                INSERT (uuid, entity_id, process_id)
                VALUES (src.uuid, src.entity_id, src.process_id)
            """,
            (str(uuid), entity_id, process_id),
        )
        self.conn.commit()

        return (
            self.conn.execute(
                """
                SELECT id
                  FROM memori_session
                 WHERE uuid = :1
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
                :1
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


@Registry.register_driver("oracle")
class Driver:
    """Oracle storage driver.

    Attributes:
        migrations: Database schema migrations for Oracle.
        requires_rollback_on_error: Oracle aborts transactions when a query
            fails and requires an explicit ROLLBACK before executing new queries.
    """

    migrations = migrations
    requires_rollback_on_error = True

    def __init__(self, conn: BaseStorageAdapter):
        self.conversation = Conversation(conn)
        self.entity = Entity(conn)
        self.entity_fact = EntityFact(conn)
        self.knowledge_graph = KnowledgeGraph(conn)
        self.process = Process(conn)
        self.process_attribute = ProcessAttribute(conn)
        self.schema = Schema(conn)
        self.session = Session(conn)
