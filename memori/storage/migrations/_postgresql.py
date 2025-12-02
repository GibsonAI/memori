r"""
 __  __                           _
|  \/  | ___ _ __ ___   ___  _ __(_)
| |\/| |/ _ \ '_ ` _ \ / _ \| '__| |
| |  | |  __/ | | | | | (_) | |  | |
|_|  |_|\___|_| |_| |_|\___/|_|  |_|
                  perfectam memoriam
                       memorilabs.ai
"""

migrations = {
    1: [
        {
            "description": "create table memori_schema_version",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_schema_version(
                    num BIGINT NOT NULL PRIMARY KEY
                )
            """,
        },
        {
            "description": "create table memori_entity",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_entity(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    external_id VARCHAR(100) NOT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_entity_external_id UNIQUE (external_id),
                    CONSTRAINT uk_memori_entity_uuid UNIQUE (uuid)
                )
            """,
        },
        {
            "description": "create table memori_process",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_process(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    external_id VARCHAR(100) NOT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_process_external_id UNIQUE (external_id),
                    CONSTRAINT uk_memori_process_uuid UNIQUE (uuid)
                )
            """,
        },
        {
            "description": "create table memori_session",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_session(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    entity_id BIGINT DEFAULT NULL,
                    process_id BIGINT DEFAULT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_session_entity_id UNIQUE (entity_id, id),
                    CONSTRAINT uk_memori_session_process_id UNIQUE (process_id, id),
                    CONSTRAINT uk_memori_session_uuid UNIQUE (uuid),
                    --
                    CONSTRAINT fk_memori_sess_entity
                       FOREIGN KEY (entity_id)
                        REFERENCES memori_entity (id)
                         ON DELETE CASCADE,
                    CONSTRAINT fk_memori_sess_process
                       FOREIGN KEY (process_id)
                        REFERENCES memori_process (id)
                         ON DELETE CASCADE
                )
            """,
        },
        {
            "description": "create table memori_conversation",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_conversation(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    session_id BIGINT NOT NULL,
                    summary TEXT DEFAULT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_conversation_session_id UNIQUE (session_id),
                    CONSTRAINT uk_memori_conversation_uuid UNIQUE (uuid),
                    --
                    CONSTRAINT fk_memori_conv_session
                       FOREIGN KEY (session_id)
                        REFERENCES memori_session (id)
                         ON DELETE CASCADE
                )
            """,
        },
        {
            "description": "create table memori_conversation_message",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_conversation_message(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    conversation_id BIGINT NOT NULL,
                    role VARCHAR(255) NOT NULL,
                    type VARCHAR(255) DEFAULT NULL,
                    content TEXT NOT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_conversation_message_conversation_id UNIQUE (conversation_id, id),
                    CONSTRAINT uk_memori_conversation_message_uuid UNIQUE (uuid),
                    --
                    CONSTRAINT fk_memori_conv_msg_conv
                       FOREIGN KEY (conversation_id)
                        REFERENCES memori_conversation (id)
                         ON DELETE CASCADE
                )
            """,
        },
        {
            "description": "create table memori_entity_fact",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_entity_fact(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    entity_id BIGINT NOT NULL,
                    content TEXT NOT NULL,
                    content_embedding BYTEA NOT NULL,
                    num_times BIGINT NOT NULL,
                    date_last_time TIMESTAMP NOT NULL,
                    uniq CHAR(64) NOT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_entity_fact_entity_id UNIQUE (entity_id, id),
                    CONSTRAINT uk_memori_entity_fact_entity_id_uniq UNIQUE (entity_id, uniq),
                    CONSTRAINT uk_memori_entity_fact_uuid UNIQUE (uuid),
                    --
                    CONSTRAINT fk_memori_ent_fact_entity
                       FOREIGN KEY (entity_id)
                        REFERENCES memori_entity (id)
                         ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_memori_entity_fact_entity_id_freq
                ON memori_entity_fact (entity_id, num_times DESC, date_last_time DESC);
                CREATE INDEX IF NOT EXISTS idx_memori_entity_fact_embedding_search
                ON memori_entity_fact (entity_id, id)
            """,
        },
        {
            "description": "create table memori_process_attribute",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_process_attribute(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    process_id BIGINT NOT NULL,
                    content TEXT NOT NULL,
                    num_times BIGINT NOT NULL,
                    date_last_time TIMESTAMP NOT NULL,
                    uniq CHAR(64) NOT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_process_attribute_process_id UNIQUE (process_id, id),
                    CONSTRAINT uk_memori_process_attribute_process_id_uniq UNIQUE (process_id, uniq),
                    CONSTRAINT uk_memori_process_attribute_uuid UNIQUE (uuid),
                    --
                    CONSTRAINT fk_memori_proc_attribute
                       FOREIGN KEY (process_id)
                        REFERENCES memori_process (id)
                         ON DELETE CASCADE
                )
            """,
        },
        {
            "description": "create table memori_subject",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_subject(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(255) NOT NULL,
                    uniq CHAR(64) NOT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_subject_uniq UNIQUE (uniq),
                    CONSTRAINT uk_memori_subject_uuid UNIQUE (uuid)
                )
            """,
        },
        {
            "description": "create table memori_predicate",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_predicate(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    content TEXT NOT NULL,
                    uniq CHAR(64) NOT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_predicate_uniq UNIQUE (uniq),
                    CONSTRAINT uk_memori_predicate_uuid UNIQUE (uuid)
                )
            """,
        },
        {
            "description": "create table memori_object",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_object(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(255) NOT NULL,
                    uniq CHAR(64) NOT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_object_uniq UNIQUE (uniq),
                    CONSTRAINT uk_memori_object_uuid UNIQUE (uuid)
                )
            """,
        },
        {
            "description": "create table memori_knowledge_graph",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_knowledge_graph(
                    id BIGSERIAL PRIMARY KEY,
                    uuid VARCHAR(36) NOT NULL,
                    entity_id BIGINT NOT NULL,
                    subject_id BIGINT NOT NULL,
                    predicate_id BIGINT NOT NULL,
                    object_id BIGINT NOT NULL,
                    num_times BIGINT NOT NULL,
                    date_last_time TIMESTAMP NOT NULL,
                    date_created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    date_updated TIMESTAMP DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_knowledge_graph_entity_id UNIQUE (entity_id, id),
                    CONSTRAINT uk_memori_knowledge_graph_entity_subject_predicate_object UNIQUE (entity_id, subject_id, predicate_id, object_id),
                    CONSTRAINT uk_memori_knowledge_graph_object_id UNIQUE (object_id, id),
                    CONSTRAINT uk_memori_knowledge_graph_predicate_id UNIQUE (predicate_id, id),
                    CONSTRAINT uk_memori_knowledge_graph_subject_id UNIQUE (subject_id, id),
                    CONSTRAINT uk_memori_knowledge_graph_uuid UNIQUE (uuid),
                    --
                    CONSTRAINT fk_memori_know_graph_entity
                       FOREIGN KEY (entity_id)
                        REFERENCES memori_entity (id)
                         ON DELETE CASCADE,
                    CONSTRAINT fk_memori_know_graph_object
                       FOREIGN KEY (object_id)
                        REFERENCES memori_object (id)
                         ON DELETE CASCADE,
                    CONSTRAINT fk_memori_know_graph_predicate
                       FOREIGN KEY (predicate_id)
                        REFERENCES memori_predicate (id)
                         ON DELETE CASCADE,
                    CONSTRAINT fk_memori_know_graph_subject
                       FOREIGN KEY (subject_id)
                        REFERENCES memori_subject (id)
                         ON DELETE CASCADE
                )
            """,
        },
    ]
}
