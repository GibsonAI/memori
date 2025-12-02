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
                    num INTEGER NOT NULL PRIMARY KEY
                )
            """,
        },
        {
            "description": "create table memori_entity",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_entity(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    entity_id INTEGER DEFAULT NULL,
                    process_id INTEGER DEFAULT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    session_id INTEGER NOT NULL,
                    summary TEXT DEFAULT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    type TEXT DEFAULT NULL,
                    content TEXT NOT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    content_embedding BLOB NOT NULL,
                    num_times INTEGER NOT NULL,
                    date_last_time TEXT NOT NULL,
                    uniq TEXT NOT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
                    --
                    CONSTRAINT uk_memori_entity_fact_entity_id UNIQUE (entity_id, id),
                    CONSTRAINT uk_memori_entity_fact_entity_id_uniq UNIQUE (entity_id, uniq),
                    CONSTRAINT uk_memori_entity_fact_uuid UNIQUE (uuid),
                    --
                    CONSTRAINT fk_memori_ent_fact_entity
                       FOREIGN KEY (entity_id)
                        REFERENCES memori_entity (id)
                         ON DELETE CASCADE
                )
            """,
        },
        {
            "description": "create index on memori_entity_fact for frequency queries",
            "operation": """
                CREATE INDEX IF NOT EXISTS idx_memori_entity_fact_entity_id_freq
                ON memori_entity_fact (entity_id, num_times DESC, date_last_time DESC)
            """,
        },
        {
            "description": "create index on memori_entity_fact for embedding search",
            "operation": """
                CREATE INDEX IF NOT EXISTS idx_memori_entity_fact_embedding_search
                ON memori_entity_fact (entity_id, id)
            """,
        },
        {
            "description": "create table memori_process_attribute",
            "operation": """
                CREATE TABLE IF NOT EXISTS memori_process_attribute(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    process_id INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    num_times INTEGER NOT NULL,
                    date_last_time TEXT NOT NULL,
                    uniq TEXT NOT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    uniq TEXT NOT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    content TEXT NOT NULL,
                    uniq TEXT NOT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    uniq TEXT NOT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uuid TEXT NOT NULL,
                    entity_id INTEGER NOT NULL,
                    subject_id INTEGER NOT NULL,
                    predicate_id INTEGER NOT NULL,
                    object_id INTEGER NOT NULL,
                    num_times INTEGER NOT NULL,
                    date_last_time TEXT NOT NULL,
                    date_created TEXT NOT NULL DEFAULT (datetime('now')),
                    date_updated TEXT DEFAULT NULL,
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
