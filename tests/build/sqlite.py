#!/usr/bin/env python3

from memori import Memori
from tests.database.core import SQLiteTestDBSession

session = SQLiteTestDBSession()

for table_name in [
    "memori_conversation_message",
    "memori_conversation",
    "memori_session",
    "memori_entity",
    "memori_process",
    "memori_schema_version",
]:
    session.connection().exec_driver_sql(f"DROP TABLE IF EXISTS {table_name}")

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
    DROP TABLE IF EXISTS memori_schema_version
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
