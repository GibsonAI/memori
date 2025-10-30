"""
Couchbase adapter for Memori memory storage
Implements Couchbase-specific CRUD operations for memories
"""

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from loguru import logger

try:
    from couchbase.collection import Collection  # noqa: F401
    from couchbase.exceptions import CouchbaseException  # noqa: F401

    COUCHBASE_AVAILABLE = True
except ImportError:
    COUCHBASE_AVAILABLE = False

from ..connectors.couchbase_connector import CouchbaseConnector


class CouchbaseAdapter:
    """Couchbase-specific adapter for memory storage and retrieval"""

    def __init__(self, connector: CouchbaseConnector):
        """Initialize Couchbase adapter"""
        if not COUCHBASE_AVAILABLE:
            raise ImportError(
                "couchbase is required for Couchbase support. Install with: pip install couchbase"
            )

        self.connector = connector
        self.scope = connector.get_scope()

        # Collection names
        self.CHAT_HISTORY_COLLECTION = "chat_history"
        self.SHORT_TERM_MEMORY_COLLECTION = "short_term_memory"
        self.LONG_TERM_MEMORY_COLLECTION = "long_term_memory"

        # Initialize collections
        self._initialize_collections()

    def _initialize_collections(self):
        """Initialize Couchbase collections with proper indexes"""
        try:
            # Get references to collections
            # Note: Collections should exist in Couchbase, they're created via UI or admin API
            collections = [
                self.CHAT_HISTORY_COLLECTION,
                self.SHORT_TERM_MEMORY_COLLECTION,
                self.LONG_TERM_MEMORY_COLLECTION,
            ]

            for collection_name in collections:
                try:
                    _ = self.connector.get_collection(collection_name)
                    logger.debug(f"Initialized Couchbase collection: {collection_name}")
                except Exception as e:
                    logger.warning(
                        f"Collection {collection_name} may not exist yet: {e}"
                    )

            # Create indexes (simplified implementation)
            self._create_indexes()

        except Exception as e:
            logger.warning(f"Failed to initialize Couchbase collections: {e}")

    def _create_indexes(self):
        """Create essential indexes for performance"""
        try:
            # Note: In production, indexes should be created via N1QL or admin API
            # This is a placeholder implementation
            logger.debug("Couchbase indexes should be created via N1QL or admin API")
        except Exception as e:
            logger.warning(f"Failed to create Couchbase indexes: {e}")

    def _convert_memory_to_document(
        self, memory_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert memory data to Couchbase document format"""
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
                    except:
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
                except:
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
        """Convert Couchbase document to memory format"""
        if not document:
            return {}

        memory = document.copy()

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
        """Store a chat interaction in Couchbase"""
        try:
            collection = self.connector.get_collection(self.CHAT_HISTORY_COLLECTION)

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

            collection.upsert(chat_id, document)
            logger.debug(f"Stored chat interaction: {chat_id}")
            return chat_id

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
            collection = self.connector.get_collection(self.CHAT_HISTORY_COLLECTION)

            # Fetch existing document
            result = collection.get(chat_id)
            existing_doc = result.content_as[dict]

            # Update fields
            existing_doc["user_input"] = user_input
            existing_doc["ai_output"] = ai_output
            existing_doc["model"] = model
            existing_doc["tokens_used"] = tokens_used
            existing_doc["timestamp"] = datetime.now(timezone.utc)

            if metadata:
                existing_doc["metadata"] = metadata

            collection.upsert(chat_id, existing_doc)
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
        """Retrieve chat history from Couchbase using N1QL"""
        try:
            cluster = self.connector.get_connection()
            bucket_name = self.connector.bucket_name

            # Build N1QL query
            query = f"""
            SELECT META().id, *
            FROM `{bucket_name}`.{self.scope._name}.{self.CHAT_HISTORY_COLLECTION}
            WHERE namespace = $namespace
            """
            if session_id:
                query += " AND session_id = $session_id"
            query += " ORDER BY timestamp DESC LIMIT $limit"

            result = cluster.query(query, named_parameters={
                "namespace": namespace,
                "session_id": session_id or "",
                "limit": limit
            })

            results = []
            for row in result:
                results.append(self._convert_document_to_memory(row))

            logger.debug(f"Retrieved {len(results)} chat history entries")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve chat history: {e}")
            return []

    # Short-term Memory Operations
    def store_short_term_memory(self, memory_data: dict[str, Any]) -> str:
        """Store short-term memory in Couchbase"""
        try:
            collection = self.connector.get_collection(
                self.SHORT_TERM_MEMORY_COLLECTION
            )

            # Generate memory ID if not provided
            if "memory_id" not in memory_data:
                memory_data["memory_id"] = str(uuid4())

            document = self._convert_memory_to_document(memory_data)

            collection.upsert(memory_data["memory_id"], document)
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
        """Retrieve short-term memories from Couchbase using N1QL"""
        try:
            cluster = self.connector.get_connection()
            bucket_name = self.connector.bucket_name

            # Build N1QL query
            query = f"""
            SELECT META().id, *
            FROM `{bucket_name}`.{self.scope._name}.{self.SHORT_TERM_MEMORY_COLLECTION}
            WHERE namespace = $namespace
            AND importance_score >= $importance_threshold
            AND (expires_at IS NULL OR expires_at > NOW())
            """

            if category_filter:
                query += " AND category_primary IN $category_filter"

            query += " ORDER BY importance_score DESC, created_at DESC LIMIT $limit"

            params = {
                "namespace": namespace,
                "importance_threshold": importance_threshold,
                "category_filter": category_filter or [],
                "limit": limit,
            }

            result = cluster.query(query, named_parameters=params)

            results = []
            for row in result:
                results.append(self._convert_document_to_memory(row))

            logger.debug(f"Retrieved {len(results)} short-term memories")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve short-term memories: {e}")
            return []

    def update_short_term_memory(self, memory_id: str, updates: dict[str, Any]) -> bool:
        """Update a short-term memory"""
        try:
            collection = self.connector.get_collection(
                self.SHORT_TERM_MEMORY_COLLECTION
            )

            # Fetch existing document
            result = collection.get(memory_id)
            existing_doc = result.content_as[dict]

            # Apply updates
            existing_doc.update(self._convert_memory_to_document(updates))

            collection.upsert(memory_id, existing_doc)
            logger.debug(f"Updated short-term memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update short-term memory: {e}")
            return False

    def delete_short_term_memory(self, memory_id: str) -> bool:
        """Delete a short-term memory"""
        try:
            collection = self.connector.get_collection(
                self.SHORT_TERM_MEMORY_COLLECTION
            )

            collection.remove(memory_id)
            logger.debug(f"Deleted short-term memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete short-term memory: {e}")
            return False

    # Long-term Memory Operations
    def store_long_term_memory(self, memory_data: dict[str, Any]) -> str:
        """Store long-term memory in Couchbase"""
        try:
            collection = self.connector.get_collection(
                self.LONG_TERM_MEMORY_COLLECTION
            )

            # Generate memory ID if not provided
            if "memory_id" not in memory_data:
                memory_data["memory_id"] = str(uuid4())

            document = self._convert_memory_to_document(memory_data)

            collection.upsert(memory_data["memory_id"], document)
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
        """Retrieve long-term memories from Couchbase using N1QL"""
        try:
            cluster = self.connector.get_connection()
            bucket_name = self.connector.bucket_name

            # Build N1QL query
            query = f"""
            SELECT META().id, *
            FROM `{bucket_name}`.{self.scope._name}.{self.LONG_TERM_MEMORY_COLLECTION}
            WHERE namespace = $namespace
            AND importance_score >= $importance_threshold
            """

            if category_filter:
                query += " AND category_primary IN $category_filter"

            if classification_filter:
                query += " AND classification IN $classification_filter"

            query += " ORDER BY importance_score DESC, created_at DESC LIMIT $limit"

            params = {
                "namespace": namespace,
                "importance_threshold": importance_threshold,
                "category_filter": category_filter or [],
                "classification_filter": classification_filter or [],
                "limit": limit,
            }

            result = cluster.query(query, named_parameters=params)

            results = []
            for row in result:
                results.append(self._convert_document_to_memory(row))

            logger.debug(f"Retrieved {len(results)} long-term memories")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve long-term memories: {e}")
            return []

    def update_long_term_memory(self, memory_id: str, updates: dict[str, Any]) -> bool:
        """Update a long-term memory"""
        try:
            collection = self.connector.get_collection(
                self.LONG_TERM_MEMORY_COLLECTION
            )

            # Fetch existing document
            result = collection.get(memory_id)
            existing_doc = result.content_as[dict]

            # Apply updates
            existing_doc.update(self._convert_memory_to_document(updates))

            collection.upsert(memory_id, existing_doc)
            logger.debug(f"Updated long-term memory: {memory_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update long-term memory: {e}")
            return False

    def delete_long_term_memory(self, memory_id: str) -> bool:
        """Delete a long-term memory"""
        try:
            collection = self.connector.get_collection(
                self.LONG_TERM_MEMORY_COLLECTION
            )

            collection.remove(memory_id)
            logger.debug(f"Deleted long-term memory: {memory_id}")
            return True

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
        """Search memories using Couchbase N1QL"""
        try:
            cluster = self.connector.get_connection()
            bucket_name = self.connector.bucket_name

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
                # Build N1QL search query
                search_query = f"""
                SELECT META().id, *
                FROM `{bucket_name}`.{self.scope._name}.{collection_name}
                WHERE namespace = $namespace
                AND (LOWER(searchable_content) LIKE LOWER($search_pattern)
                     OR LOWER(summary) LIKE LOWER($search_pattern))
                """

                if category_filter:
                    search_query += " AND category_primary IN $category_filter"

                # For short-term memories, exclude expired ones
                if memory_type == "short_term":
                    search_query += " AND (expires_at IS NULL OR expires_at > NOW())"

                search_query += " ORDER BY importance_score DESC LIMIT $limit"

                params = {
                    "namespace": namespace,
                    "search_pattern": f"%{query}%",
                    "category_filter": category_filter or [],
                    "limit": limit,
                }

                result = cluster.query(search_query, named_parameters=params)

                for row in result:
                    memory = self._convert_document_to_memory(row)
                    memory["memory_type"] = memory_type
                    memory["search_strategy"] = "n1ql_pattern"
                    results.append(memory)

            # Sort all results by importance
            results.sort(key=lambda x: x.get("importance_score", 0), reverse=True)

            logger.debug(f"Couchbase search returned {len(results)} results")
            return results[:limit]

        except Exception as e:
            logger.error(f"Couchbase search failed: {e}")
            return []

    # Batch Operations
    def batch_store_memories(
        self, memories: list[dict[str, Any]], memory_type: str = "short_term"
    ) -> list[str]:
        """Store multiple memories in batch"""
        try:
            if memory_type == "short_term":
                collection = self.connector.get_collection(
                    self.SHORT_TERM_MEMORY_COLLECTION
                )
            elif memory_type == "long_term":
                collection = self.connector.get_collection(
                    self.LONG_TERM_MEMORY_COLLECTION
                )
            else:
                raise ValueError(f"Invalid memory type: {memory_type}")

            memory_ids = []
            for memory_data in memories:
                if "memory_id" not in memory_data:
                    memory_data["memory_id"] = str(uuid4())

                memory_ids.append(memory_data["memory_id"])
                collection.upsert(
                    memory_data["memory_id"], self._convert_memory_to_document(memory_data)
                )

            logger.info(f"Batch stored {len(memory_ids)} {memory_type} memories")
            return memory_ids

        except Exception as e:
            logger.error(f"Batch store failed: {e}")
            return []

    def cleanup_expired_memories(self, namespace: str = "default") -> int:
        """Remove expired short-term memories"""
        try:
            cluster = self.connector.get_connection()
            bucket_name = self.connector.bucket_name

            # Build delete query
            query = f"""
            DELETE FROM `{bucket_name}`.{self.scope._name}.{self.SHORT_TERM_MEMORY_COLLECTION}
            WHERE namespace = $namespace
            AND expires_at < NOW()
            """

            result = cluster.query(query, named_parameters={"namespace": namespace})

            # Count deleted documents
            count = 0
            for _ in result:
                count += 1

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
            cluster = self.connector.get_connection()
            bucket_name = self.connector.bucket_name

            stats = {
                "namespace": namespace,
                "short_term_count": 0,
                "long_term_count": 0,
                "chat_history_count": 0,
                "total_size_bytes": 0,
            }

            # Count documents in each collection using N1QL
            for collection_name, stat_key in [
                (self.SHORT_TERM_MEMORY_COLLECTION, "short_term_count"),
                (self.LONG_TERM_MEMORY_COLLECTION, "long_term_count"),
                (self.CHAT_HISTORY_COLLECTION, "chat_history_count"),
            ]:
                query = f"""
                SELECT COUNT(*) as count
                FROM `{bucket_name}`.{self.scope._name}.{collection_name}
                WHERE namespace = $namespace
                """
                result = cluster.query(
                    query, named_parameters={"namespace": namespace}
                )
                for row in result:
                    stats[stat_key] = row.get("count", 0)

            return stats

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

