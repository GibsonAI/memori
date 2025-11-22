"""
MongoDB adapter for Memori memory storage
Implements MongoDB-specific CRUD operations for memories
"""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from loguru import logger

try:
    import pymongo  # noqa: F401
    from bson import ObjectId  # noqa: F401
    from pymongo.collection import Collection  # noqa: F401
    from pymongo.errors import DuplicateKeyError, OperationFailure  # noqa: F401

    PYMONGO_AVAILABLE = True
except ImportError:
    PYMONGO_AVAILABLE = False

from ..connectors.mongodb_connector import MongoDBConnector


class MongoDBAdapter:
    """MongoDB-specific adapter for memory storage and retrieval"""

    def __init__(self, connector: MongoDBConnector):
        """Initialize MongoDB adapter"""
        if not PYMONGO_AVAILABLE:
            raise ImportError(
                "pymongo is required for MongoDB support. Install with: pip install pymongo"
            )

        self.connector = connector
        self.database = connector.get_database()

        # Collection names
        self.CHAT_HISTORY_COLLECTION = "chat_history"
        self.SHORT_TERM_MEMORY_COLLECTION = "short_term_memory"
        self.LONG_TERM_MEMORY_COLLECTION = "long_term_memory"

        # Initialize collections
        self._initialize_collections()

    def _initialize_collections(self):
        """Initialize MongoDB collections with proper indexes"""
        try:
            # Ensure collections exist
            collections = [
                self.CHAT_HISTORY_COLLECTION,
                self.SHORT_TERM_MEMORY_COLLECTION,
                self.LONG_TERM_MEMORY_COLLECTION,
            ]

            existing_collections = self.database.list_collection_names()
            for collection_name in collections:
                if collection_name not in existing_collections:
                    self.database.create_collection(collection_name)
                    logger.info(f"Created MongoDB collection: {collection_name}")

            # Create basic indexes
            self._create_indexes()

        except Exception as e:
            logger.warning(f"Failed to initialize MongoDB collections: {e}")

    def _create_indexes(self):
        """Create essential indexes for performance"""
        try:
            # Chat history indexes
            chat_collection = self.database[self.CHAT_HISTORY_COLLECTION]
            chat_collection.create_index([("chat_id", 1)], unique=True, background=True)
            chat_collection.create_index(
                [("namespace", 1), ("session_id", 1)], background=True
            )
            chat_collection.create_index([("timestamp", -1)], background=True)

            # Short-term memory indexes
            st_collection = self.database[self.SHORT_TERM_MEMORY_COLLECTION]
            st_collection.create_index([("memory_id", 1)], unique=True, background=True)
            st_collection.create_index(
                [("namespace", 1), ("category_primary", 1), ("importance_score", -1)],
                background=True,
            )
            st_collection.create_index([("expires_at", 1)], background=True)
            st_collection.create_index([("created_at", -1)], background=True)
            st_collection.create_index(
                [("searchable_content", "text"), ("summary", "text")], background=True
            )

            # Long-term memory indexes
            lt_collection = self.database[self.LONG_TERM_MEMORY_COLLECTION]
            lt_collection.create_index([("memory_id", 1)], unique=True, background=True)
            lt_collection.create_index(
                [("namespace", 1), ("category_primary", 1), ("importance_score", -1)],
                background=True,
            )
            lt_collection.create_index([("classification", 1)], background=True)
            lt_collection.create_index([("topic", 1)], background=True)
            lt_collection.create_index([("created_at", -1)], background=True)
            lt_collection.create_index(
                [("searchable_content", "text"), ("summary", "text")], background=True
            )

            logger.debug("MongoDB indexes created successfully")

        except Exception as e:
            logger.warning(f"Failed to create MongoDB indexes: {e}")

    def _convert_memory_to_document(
        self, memory_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert memory data to MongoDB document format"""
        document = memory_data.copy()

        # Ensure datetime fields are datetime objects
        datetime_fields = [
            "created_at",
            "expires_at",
            "last_accessed",
            "extraction_timestamp",
        ]
        for field in datetime_fields:
            if field in document and document[field] is not None:
                if isinstance(document[field], str):
                    try:
                        document[field] = datetime.fromisoformat(
                            document[field].replace("Z", "+00:00")
                        )
                    except (ValueError, AttributeError) as e:
                        logger.warning(
                            f"Invalid datetime in field '{field}': {document.get(field)}, "
                            f"substituting current time. Error: {e}"
                        )
                        document[field] = datetime.now(timezone.utc)
                elif not isinstance(document[field], datetime):
                    document[field] = datetime.now(timezone.utc)

        # Handle JSON fields that might be strings
        json_fields = [
            "processed_data",
            "entities_json",
            "keywords_json",
            "supersedes_json",
            "related_memories_json",
            "metadata",
        ]
        for field in json_fields:
            if field in document and isinstance(document[field], str):
                try:
                    document[field] = json.loads(document[field])
                except json.JSONDecodeError as e:
                    logger.debug(
                        f"Field '{field}' is not valid JSON, keeping as string: {e}"
                    )
                    pass  # Keep as string if not valid JSON

        # Ensure required fields have defaults
        if "created_at" not in document:
            document["created_at"] = datetime.now(timezone.utc)
        if "importance_score" not in document:
            document["importance_score"] = 0.5
        if "access_count" not in document:
            document["access_count"] = 0
        if "namespace" not in document:
            document["namespace"] = "default"

        return document

    def _convert_document_to_memory(self, document: dict[str, Any]) -> dict[str, Any]:
        """Convert MongoDB document to memory format"""
        if not document:
            return {}

        memory = document.copy()

        # Convert ObjectId to string
        if "_id" in memory:
            memory["_id"] = str(memory["_id"])

        # Convert datetime objects to ISO strings for JSON compatibility
        datetime_fields = [
            "created_at",
            "expires_at",
            "last_accessed",
            "extraction_timestamp",
            "timestamp",
        ]
        for field in datetime_fields:
            if field in memory and isinstance(memory[field], datetime):
                memory[field] = memory[field].isoformat()

        return memory

    # Chat History Operations
    def store_chat_interaction(
        self,
        chat_id: str,
        user_input: str,
        ai_output: str,
        model: str,
        session_id: str,
        namespace: str = "default",
        tokens_used: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store a chat interaction in MongoDB"""
        try:
            collection = self.database[self.CHAT_HISTORY_COLLECTION]

            document = {
                "chat_id": chat_id,
                "user_input": user_input,
                "ai_output": ai_output,
                "model": model,
                "timestamp": datetime.now(timezone.utc),
                "session_id": session_id,
                "namespace": namespace,
                "tokens_used": tokens_used,
                "metadata": metadata or {},
            }

            collection.insert_one(document)
            logger.debug(f"Stored chat interaction: {chat_id}")
            return chat_id

        except DuplicateKeyError:
            # Chat ID already exists, update instead
            return self.update_chat_interaction(
                chat_id, user_input, ai_output, model, tokens_used, metadata
            )
        except Exception as e:
            logger.error(f"Failed to store chat interaction: {e}")
            raise

    def update_chat_interaction(
        self,
        chat_id: str,
        user_input: str,
        ai_output: str,
        model: str,
        tokens_used: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Update an existing chat interaction"""
        try:
            collection = self.database[self.CHAT_HISTORY_COLLECTION]

            update_doc = {
                "$set": {
                    "user_input": user_input,
                    "ai_output": ai_output,
                    "model": model,
                    "tokens_used": tokens_used,
                    "timestamp": datetime.now(timezone.utc),
                }
            }

            if metadata:
                update_doc["$set"]["metadata"] = metadata

            result = collection.update_one({"chat_id": chat_id}, update_doc)

            if result.matched_count == 0:
                raise ValueError(f"Chat interaction not found: {chat_id}")

            logger.debug(f"Updated chat interaction: {chat_id}")
            return chat_id

        except Exception as e:
            logger.error(f"Failed to update chat interaction: {e}")
            raise

    def get_chat_history(
        self,
        namespace: str = "default",
        session_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve chat history from MongoDB"""
        try:
            collection = self.database[self.CHAT_HISTORY_COLLECTION]

            # Build filter
            filter_doc = {"namespace": namespace}
            if session_id:
                filter_doc["session_id"] = session_id

            # Execute query
            cursor = collection.find(filter_doc).sort("timestamp", -1).limit(limit)

            results = []
            for document in cursor:
                results.append(self._convert_document_to_memory(document))

            logger.debug(f"Retrieved {len(results)} chat history entries")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve chat history: {e}")
            return []

    # Short-term Memory Operations
    def store_short_term_memory(self, memory_data: dict[str, Any]) -> str:
        """Store short-term memory in MongoDB"""
        try:
            collection = self.database[self.SHORT_TERM_MEMORY_COLLECTION]

            # Generate memory ID if not provided
            if "memory_id" not in memory_data:
                memory_data["memory_id"] = str(uuid4())

            document = self._convert_memory_to_document(memory_data)

            collection.insert_one(document)
            logger.debug(f"Stored short-term memory: {memory_data['memory_id']}")
            return memory_data["memory_id"]

        except Exception as e:
            logger.error(f"Failed to store short-term memory: {e}")
            raise

    def get_short_term_memories(
        self,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        importance_threshold: float = 0.0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve short-term memories from MongoDB"""
        try:
            collection = self.database[self.SHORT_TERM_MEMORY_COLLECTION]

            # Build filter
            filter_doc: dict[str, Any] = {
                "namespace": namespace,
                "importance_score": {"$gte": importance_threshold},
            }

            if category_filter:
                filter_doc["category_primary"] = {"$in": category_filter}

            # Include only non-expired memories
            filter_doc["$or"] = [
                {"expires_at": {"$exists": False}},
                {"expires_at": None},
                {"expires_at": {"$gt": datetime.now(timezone.utc)}},
            ]

            # Execute query
            cursor = (
                collection.find(filter_doc)
                .sort([("importance_score", -1), ("created_at", -1)])
                .limit(limit)
            )

            results = []
            for document in cursor:
                results.append(self._convert_document_to_memory(document))

            logger.debug(f"Retrieved {len(results)} short-term memories")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve short-term memories: {e}")
            return []

    def update_short_term_memory(self, memory_id: str, updates: dict[str, Any]) -> bool:
        """Update a short-term memory"""
        try:
            collection = self.database[self.SHORT_TERM_MEMORY_COLLECTION]

            # Convert updates to document format
            update_doc = {"$set": self._convert_memory_to_document(updates)}

            result = collection.update_one({"memory_id": memory_id}, update_doc)

            success = result.matched_count > 0
            if success:
                logger.debug(f"Updated short-term memory: {memory_id}")
            else:
                logger.warning(f"Short-term memory not found: {memory_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to update short-term memory: {e}")
            return False

    def delete_short_term_memory(self, memory_id: str) -> bool:
        """Delete a short-term memory"""
        try:
            collection = self.database[self.SHORT_TERM_MEMORY_COLLECTION]

            result = collection.delete_one({"memory_id": memory_id})

            success = result.deleted_count > 0
            if success:
                logger.debug(f"Deleted short-term memory: {memory_id}")
            else:
                logger.warning(f"Short-term memory not found: {memory_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete short-term memory: {e}")
            return False

    # Long-term Memory Operations
    def store_long_term_memory(self, memory_data: dict[str, Any]) -> str:
        """Store long-term memory in MongoDB"""
        try:
            collection = self.database[self.LONG_TERM_MEMORY_COLLECTION]

            # Generate memory ID if not provided
            if "memory_id" not in memory_data:
                memory_data["memory_id"] = str(uuid4())

            document = self._convert_memory_to_document(memory_data)

            collection.insert_one(document)
            logger.debug(f"Stored long-term memory: {memory_data['memory_id']}")
            return memory_data["memory_id"]

        except Exception as e:
            logger.error(f"Failed to store long-term memory: {e}")
            raise

    def get_long_term_memories(
        self,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        importance_threshold: float = 0.0,
        classification_filter: list[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve long-term memories from MongoDB"""
        try:
            collection = self.database[self.LONG_TERM_MEMORY_COLLECTION]

            # Build filter
            filter_doc = {
                "namespace": namespace,
                "importance_score": {"$gte": importance_threshold},
            }

            if category_filter:
                filter_doc["category_primary"] = {"$in": category_filter}

            if classification_filter:
                filter_doc["classification"] = {"$in": classification_filter}

            # Execute query
            cursor = (
                collection.find(filter_doc)
                .sort([("importance_score", -1), ("created_at", -1)])
                .limit(limit)
            )

            results = []
            for document in cursor:
                results.append(self._convert_document_to_memory(document))

            logger.debug(f"Retrieved {len(results)} long-term memories")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve long-term memories: {e}")
            return []

    def update_long_term_memory(self, memory_id: str, updates: dict[str, Any]) -> bool:
        """Update a long-term memory"""
        try:
            collection = self.database[self.LONG_TERM_MEMORY_COLLECTION]

            # Convert updates to document format
            update_doc = {"$set": self._convert_memory_to_document(updates)}

            result = collection.update_one({"memory_id": memory_id}, update_doc)

            success = result.matched_count > 0
            if success:
                logger.debug(f"Updated long-term memory: {memory_id}")
            else:
                logger.warning(f"Long-term memory not found: {memory_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to update long-term memory: {e}")
            return False

    def delete_long_term_memory(self, memory_id: str) -> bool:
        """Delete a long-term memory"""
        try:
            collection = self.database[self.LONG_TERM_MEMORY_COLLECTION]

            result = collection.delete_one({"memory_id": memory_id})

            success = result.deleted_count > 0
            if success:
                logger.debug(f"Deleted long-term memory: {memory_id}")
            else:
                logger.warning(f"Long-term memory not found: {memory_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete long-term memory: {e}")
            return False

    # Search Operations
    def search_memories(
        self,
        query: str,
        namespace: str = "default",
        memory_types: list[str] | None = None,
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memories using MongoDB text search"""
        try:
            results = []
            collections_to_search = []

            # Determine which collections to search
            if not memory_types or "short_term" in memory_types:
                collections_to_search.append(
                    (self.SHORT_TERM_MEMORY_COLLECTION, "short_term")
                )
            if not memory_types or "long_term" in memory_types:
                collections_to_search.append(
                    (self.LONG_TERM_MEMORY_COLLECTION, "long_term")
                )

            for collection_name, memory_type in collections_to_search:
                collection = self.database[collection_name]

                # Build search filter
                search_filter: dict[str, Any] = {
                    "$text": {"$search": query},
                    "namespace": namespace,
                }

                if category_filter:
                    search_filter["category_primary"] = {"$in": category_filter}

                # For short-term memories, exclude expired ones
                if memory_type == "short_term":
                    search_filter["$or"] = [
                        {"expires_at": {"$exists": False}},
                        {"expires_at": None},
                        {"expires_at": {"$gt": datetime.now(timezone.utc)}},
                    ]

                # Execute text search
                cursor = (
                    collection.find(search_filter, {"score": {"$meta": "textScore"}})
                    .sort([("score", {"$meta": "textScore"}), ("importance_score", -1)])
                    .limit(limit)
                )

                for document in cursor:
                    memory = self._convert_document_to_memory(document)
                    memory["memory_type"] = memory_type
                    memory["search_strategy"] = "mongodb_text"
                    results.append(memory)

            # Sort all results by text score and importance
            results.sort(
                key=lambda x: (x.get("score", 0), x.get("importance_score", 0)),
                reverse=True,
            )

            logger.debug(f"MongoDB text search returned {len(results)} results")
            return results[:limit]

        except Exception as e:
            logger.error(f"MongoDB text search failed: {e}")
            return self._fallback_search(query, namespace, category_filter, limit)

    def _fallback_search(
        self,
        query: str,
        namespace: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Fallback search using regex when text search fails"""
        try:
            results = []
            collections_to_search = [
                (self.SHORT_TERM_MEMORY_COLLECTION, "short_term"),
                (self.LONG_TERM_MEMORY_COLLECTION, "long_term"),
            ]

            # Create case-insensitive regex pattern
            regex_pattern = {"$regex": query, "$options": "i"}

            for collection_name, memory_type in collections_to_search:
                collection = self.database[collection_name]

                # Build search filter using regex
                search_filter: dict[str, Any] = {
                    "$or": [
                        {"searchable_content": regex_pattern},
                        {"summary": regex_pattern},
                    ],
                    "namespace": namespace,
                }

                if category_filter:
                    search_filter["category_primary"] = {"$in": category_filter}

                # For short-term memories, exclude expired ones
                if memory_type == "short_term":
                    search_filter["$and"] = [
                        search_filter.get("$and", []),
                        {
                            "$or": [
                                {"expires_at": {"$exists": False}},
                                {"expires_at": None},
                                {"expires_at": {"$gt": datetime.now(timezone.utc)}},
                            ]
                        },
                    ]

                # Execute regex search
                cursor = (
                    collection.find(search_filter)
                    .sort([("importance_score", -1), ("created_at", -1)])
                    .limit(limit)
                )

                for document in cursor:
                    memory = self._convert_document_to_memory(document)
                    memory["memory_type"] = memory_type
                    memory["search_strategy"] = "regex_fallback"
                    results.append(memory)

            # Sort by importance score
            results.sort(key=lambda x: x.get("importance_score", 0), reverse=True)

            logger.debug(f"Regex fallback search returned {len(results)} results")
            return results[:limit]

        except Exception as e:
            logger.error(f"Fallback search failed: {e}")
            return []

    # Batch Operations
    def batch_store_memories(
        self, memories: list[dict[str, Any]], memory_type: str = "short_term"
    ) -> list[str]:
        """Store multiple memories in batch"""
        try:
            if memory_type == "short_term":
                collection = self.database[self.SHORT_TERM_MEMORY_COLLECTION]
            elif memory_type == "long_term":
                collection = self.database[self.LONG_TERM_MEMORY_COLLECTION]
            else:
                raise ValueError(f"Invalid memory type: {memory_type}")

            # Prepare documents
            documents = []
            memory_ids = []

            for memory_data in memories:
                if "memory_id" not in memory_data:
                    memory_data["memory_id"] = str(uuid4())

                memory_ids.append(memory_data["memory_id"])
                documents.append(self._convert_memory_to_document(memory_data))

            # Insert all documents
            result = collection.insert_many(documents, ordered=False)

            logger.info(
                f"Batch stored {len(result.inserted_ids)} {memory_type} memories"
            )
            return memory_ids

        except Exception as e:
            logger.error(f"Batch store failed: {e}")
            return []

    def cleanup_expired_memories(self, namespace: str = "default") -> int:
        """Remove expired short-term memories"""
        try:
            collection = self.database[self.SHORT_TERM_MEMORY_COLLECTION]

            # Delete expired memories
            result = collection.delete_many(
                {
                    "namespace": namespace,
                    "expires_at": {"$lt": datetime.now(timezone.utc)},
                }
            )

            count = result.deleted_count
            if count > 0:
                logger.info(
                    f"Cleaned up {count} expired memories from namespace: {namespace}"
                )

            return count

        except Exception as e:
            logger.error(f"Failed to cleanup expired memories: {e}")
            return 0

    def get_memory_stats(self, namespace: str = "default") -> dict[str, Any]:
        """Get memory storage statistics"""
        try:
            stats = {
                "namespace": namespace,
                "short_term_count": 0,
                "long_term_count": 0,
                "chat_history_count": 0,
                "total_size_bytes": 0,
            }

            # Count documents in each collection
            stats["short_term_count"] = self.database[
                self.SHORT_TERM_MEMORY_COLLECTION
            ].count_documents({"namespace": namespace})

            stats["long_term_count"] = self.database[
                self.LONG_TERM_MEMORY_COLLECTION
            ].count_documents({"namespace": namespace})

            stats["chat_history_count"] = self.database[
                self.CHAT_HISTORY_COLLECTION
            ].count_documents({"namespace": namespace})

            # Get database stats
            db_stats = self.database.command("dbStats")
            stats["total_size_bytes"] = db_stats.get("dataSize", 0)

            return stats

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}
