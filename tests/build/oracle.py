#!/usr/bin/env python3

from memori import Memori
from tests.database.core import OracleTestDBSession

session = OracleTestDBSession()

# Drop tables in reverse order of dependencies (Oracle doesn't support DROP TABLE IF EXISTS)
# Using PL/SQL to handle "table does not exist" errors gracefully
for table_name in [
    "memori_conversation_message",
    "memori_conversation",
    "memori_knowledge_graph",
    "memori_entity_fact",
    "memori_process_attribute",
    "memori_session",
    "memori_subject",
    "memori_predicate",
    "memori_object",
    "memori_entity",
    "memori_process",
    "memori_schema_version",
]:
    session.connection().exec_driver_sql(
        f"""
        BEGIN
            EXECUTE IMMEDIATE 'DROP TABLE {table_name} CASCADE CONSTRAINTS';
        EXCEPTION
            WHEN OTHERS THEN
                IF SQLCODE != -942 THEN
                    RAISE;
                END IF;
        END;
        """
    )

# Executes all migrations.
mem = Memori(conn=session)
if mem.config.storage is not None:
    mem.config.storage.build()
print("-" * 50)
# Has no effect, version number is set correctly.
mem = Memori(conn=session)
if mem.config.storage is not None:
    mem.config.storage.build()
print("-" * 50)

session.connection().exec_driver_sql(
    """
    BEGIN
        EXECUTE IMMEDIATE 'DROP TABLE memori_schema_version CASCADE CONSTRAINTS';
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE != -942 THEN
                RAISE;
            END IF;
    END;
    """
)
session.commit()

# Executes all migrations again.
mem = Memori(conn=session)
if mem.config.storage is not None:
    mem.config.storage.build()

session.connection().exec_driver_sql(
    """
    DELETE FROM memori_schema_version
    """
)
session.commit()
