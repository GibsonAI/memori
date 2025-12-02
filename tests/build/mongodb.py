#!/usr/bin/env python3

from memori import Memori
from tests.database.core import MongoTestDBSession

client = MongoTestDBSession()
db = client["memori_test"]

# Drop existing collections
for collection_name in [
    "memori_conversation_message",
    "memori_conversation",
    "memori_session",
    "memori_entity",
    "memori_process",
    "memori_schema_version",
]:
    if collection_name in db.list_collection_names():
        db.drop_collection(collection_name)

# Executes all migrations.
mem = Memori(conn=client)
if mem.config.storage is not None:
    mem.config.storage.build()
print("-" * 50)
# Has no effect, version number is set correctly.
mem = Memori(conn=client)
if mem.config.storage is not None:
    mem.config.storage.build()
print("-" * 50)

# Drop schema version collection
if "memori_schema_version" in db.list_collection_names():
    db.drop_collection("memori_schema_version")

# Executes all migrations again.
mem = Memori(conn=client)
if mem.config.storage is not None:
    mem.config.storage.build()

# Clear schema version
db["memori_schema_version"].delete_many({})
client.admin.command("ping")
