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
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_schema_version(
                            num NUMBER(19) NOT NULL PRIMARY KEY
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_entity",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_entity(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            external_id VARCHAR2(100) NOT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_entity_external_id UNIQUE (external_id),
                            CONSTRAINT uk_memori_entity_uuid UNIQUE (uuid)
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_process",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_process(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            external_id VARCHAR2(100) NOT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_process_external_id UNIQUE (external_id),
                            CONSTRAINT uk_memori_process_uuid UNIQUE (uuid)
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_session",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_session(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            entity_id NUMBER(19) DEFAULT NULL,
                            process_id NUMBER(19) DEFAULT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_session_entity_id UNIQUE (entity_id, id),
                            CONSTRAINT uk_memori_session_process_id UNIQUE (process_id, id),
                            CONSTRAINT uk_memori_session_uuid UNIQUE (uuid),
                            CONSTRAINT fk_memori_sess_entity
                               FOREIGN KEY (entity_id)
                                REFERENCES memori_entity (id)
                                 ON DELETE CASCADE,
                            CONSTRAINT fk_memori_sess_process
                               FOREIGN KEY (process_id)
                                REFERENCES memori_process (id)
                                 ON DELETE CASCADE
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_conversation",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_conversation(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            session_id NUMBER(19) NOT NULL,
                            summary CLOB DEFAULT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_conversation_session_id UNIQUE (session_id),
                            CONSTRAINT uk_memori_conversation_uuid UNIQUE (uuid),
                            CONSTRAINT fk_memori_conv_session
                               FOREIGN KEY (session_id)
                                REFERENCES memori_session (id)
                                 ON DELETE CASCADE
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_conversation_message",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_conversation_message(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            conversation_id NUMBER(19) NOT NULL,
                            role VARCHAR2(255) NOT NULL,
                            type VARCHAR2(255) DEFAULT NULL,
                            content CLOB NOT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_conversation_message_conversation_id UNIQUE (conversation_id, id),
                            CONSTRAINT uk_memori_conversation_message_uuid UNIQUE (uuid),
                            CONSTRAINT fk_memori_conv_msg_conv
                               FOREIGN KEY (conversation_id)
                                REFERENCES memori_conversation (id)
                                 ON DELETE CASCADE
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_entity_fact",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_entity_fact(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            entity_id NUMBER(19) NOT NULL,
                            content CLOB NOT NULL,
                            content_embedding BLOB NOT NULL,
                            num_times NUMBER(19) NOT NULL,
                            date_last_time TIMESTAMP NOT NULL,
                            uniq CHAR(64) NOT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_entity_fact_entity_id UNIQUE (entity_id, id),
                            CONSTRAINT uk_memori_entity_fact_entity_id_uniq UNIQUE (entity_id, uniq),
                            CONSTRAINT uk_memori_entity_fact_uuid UNIQUE (uuid),
                            CONSTRAINT fk_memori_ent_fact_entity
                               FOREIGN KEY (entity_id)
                                REFERENCES memori_entity (id)
                                 ON DELETE CASCADE
                        )
                    ';
                    EXECUTE IMMEDIATE '
                        CREATE INDEX idx_memori_entity_fact_entity_id_freq
                        ON memori_entity_fact (entity_id, num_times DESC, date_last_time DESC)
                    ';
                    EXECUTE IMMEDIATE '
                        CREATE INDEX idx_memori_entity_fact_embedding_search
                        ON memori_entity_fact (entity_id, id)
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 OR SQLCODE = -1408 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_process_attribute",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_process_attribute(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            process_id NUMBER(19) NOT NULL,
                            content CLOB NOT NULL,
                            num_times NUMBER(19) NOT NULL,
                            date_last_time TIMESTAMP NOT NULL,
                            uniq CHAR(64) NOT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_process_attribute_process_id UNIQUE (process_id, id),
                            CONSTRAINT uk_memori_process_attribute_process_id_uniq UNIQUE (process_id, uniq),
                            CONSTRAINT uk_memori_process_attribute_uuid UNIQUE (uuid),
                            CONSTRAINT fk_memori_proc_attribute
                               FOREIGN KEY (process_id)
                                REFERENCES memori_process (id)
                                 ON DELETE CASCADE
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_subject",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_subject(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            name VARCHAR2(255) NOT NULL,
                            type VARCHAR2(255) NOT NULL,
                            uniq CHAR(64) NOT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_subject_uniq UNIQUE (uniq),
                            CONSTRAINT uk_memori_subject_uuid UNIQUE (uuid)
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_predicate",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_predicate(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            content CLOB NOT NULL,
                            uniq CHAR(64) NOT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_predicate_uniq UNIQUE (uniq),
                            CONSTRAINT uk_memori_predicate_uuid UNIQUE (uuid)
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_object",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_object(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            name VARCHAR2(255) NOT NULL,
                            type VARCHAR2(255) NOT NULL,
                            uniq CHAR(64) NOT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_object_uniq UNIQUE (uniq),
                            CONSTRAINT uk_memori_object_uuid UNIQUE (uuid)
                        )
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
        {
            "description": "create table memori_knowledge_graph",
            "operation": """
                BEGIN
                    EXECUTE IMMEDIATE '
                        CREATE TABLE memori_knowledge_graph(
                            id NUMBER(19) GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                            uuid VARCHAR2(36) NOT NULL,
                            entity_id NUMBER(19) NOT NULL,
                            subject_id NUMBER(19) NOT NULL,
                            predicate_id NUMBER(19) NOT NULL,
                            object_id NUMBER(19) NOT NULL,
                            num_times NUMBER(19) NOT NULL,
                            date_last_time TIMESTAMP NOT NULL,
                            date_created TIMESTAMP DEFAULT SYSTIMESTAMP NOT NULL,
                            date_updated TIMESTAMP DEFAULT NULL,
                            CONSTRAINT uk_memori_knowledge_graph_entity_id UNIQUE (entity_id, id),
                            CONSTRAINT uk_memori_knowledge_graph_entity_subject_predicate_object UNIQUE (entity_id, subject_id, predicate_id, object_id),
                            CONSTRAINT uk_memori_knowledge_graph_object_id UNIQUE (object_id, id),
                            CONSTRAINT uk_memori_knowledge_graph_predicate_id UNIQUE (predicate_id, id),
                            CONSTRAINT uk_memori_knowledge_graph_subject_id UNIQUE (subject_id, id),
                            CONSTRAINT uk_memori_knowledge_graph_uuid UNIQUE (uuid),
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
                    ';
                EXCEPTION
                    WHEN OTHERS THEN
                        IF SQLCODE = -955 THEN NULL;
                        ELSE RAISE;
                        END IF;
                END;
            """,
        },
    ]
}
