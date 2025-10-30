"""
Couchbase-based database manager for Memori v2.0
Provides Couchbase support parallel to SQLAlchemy with same interface
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
from uuid import uuid4

from loguru import logger

if TYPE_CHECKING:
    from couchbase.cluster import Cluster
    from couchbase.collection import Collection
    from couchbase.scope import Scope

try:
    from couchbase.cluster import Cluster as _Cluster
    from couchbase.options import ClusterOptions
    from couchbase.auth import PasswordAuthenticator
    from couchbase.exceptions import CouchbaseException  # noqa: F401

    COUCHBASE_AVAILABLE = True
    Cluster = _Cluster  # type: ignore
except ImportError:
    COUCHBASE_AVAILABLE = False
    Cluster = None  # type: ignore
    logger.warning("couchbase not available - Couchbase support disabled")

from ..utils.exceptions import DatabaseError
from ..utils.pydantic_models import ProcessedLongTermMemory


class CouchbaseDatabaseManager:
    """Couchbase-based database manager with interface compatible with SQLAlchemy manager"""

    # Constants for collection names
    CHAT_HISTORY_COLLECTION = "chat_history"
    SHORT_TERM_MEMORY_COLLECTION = "short_term_memory"
    LONG_TERM_MEMORY_COLLECTION = "long_term_memory"

    # Database type identifier for database-agnostic code
    database_type = "couchbase"

    def __init__(
        self, database_connect: str, template: str = "basic", schema_init: bool = True
    ):
        if not COUCHBASE_AVAILABLE:
            raise DatabaseError(
                "Couchbase support requires couchbase. Install with: pip install couchbase"
            )

        self.database_connect = database_connect
        self.template = template
        self.schema_init = schema_init

        # Parse Couchbase connection string
        self._parse_connection_string()

        # Initialize Couchbase connection
        self.cluster = None
        self.bucket = None
        self.scope = None
        self.database_type = "couchbase"

        # Collections cache
        self._collections = {}

        logger.info(f"Initialized Couchbase database manager for {self.bucket_name}")

    def _parse_connection_string(self):
        """Parse Couchbase connection string to extract components"""
        try:
            # Handle couchbase:// scheme
            if self.database_connect.startswith("couchbase://"):
                connection_part = self.database_connect.replace("couchbase://", "")

                # Parse connection components
                if "@" in connection_part:
                    # Format: couchbase://user:pass@host:port/bucket
                    auth_part, host_part = connection_part.split("@", 1)
                    if ":" in auth_part:
                        self.username, self.password = auth_part.split(":", 1)
                    else:
                        self.username = auth_part
                        self.password = ""
                else:
                    host_part = connection_part
                    self.username = "Administrator"
                    self.password = "password"

                # Parse host and bucket
                if "/" in host_part:
                    host_str, bucket_path = host_part.split("/", 1)
                    parts = bucket_path.split("/")
                    self.bucket_name = parts[0]
                    self.scope_name = parts[1] if len(parts) > 1 else "_default"
                    self.collection_name = parts[2] if len(parts) > 2 else "_default"
                else:
                    self.bucket_name = "memori"
                    self.scope_name = "_default"
                    self.collection_name = "_default"

                # Parse host and port
                if ":" in host_str:
                    self.host, port_str = host_str.split(":", 1)
                    try:
                        self.port = int(port_str)
                    except ValueError:
                        self.port = 8091
                else:
                    self.host = host_str
                    self.port = 8091

            else:
                raise ValueError(f"Invalid Couchbase connection string: {self.database_connect}")

        except Exception as e:
            logger.error(f"Failed to parse Couchbase connection string: {e}")
            raise DatabaseError(f"Invalid Couchbase connection string: {e}")

    def _get_cluster(self) -> Cluster:
        """Get Couchbase cluster connection"""
        if self.cluster is None:
            try:
                # Create cluster options
                auth = PasswordAuthenticator(self.username, self.password)
                cluster_options = ClusterOptions(auth)

                # Connect to cluster
                connection_string = f"{self.host}:{self.port}"
                self.cluster = Cluster(
                    f"couchbase://{connection_string}", cluster_options
                )

                # Get bucket
                self.bucket = self.cluster.bucket(self.bucket_name)

                # Get scope
                self.scope = self.bucket.scope(self.scope_name)

                logger.info(
                    f"Connected to Couchbase at {self.host}:{self.port}, bucket: {self.bucket_name}"
                )

            except Exception as e:
                raise DatabaseError(f"Failed to connect to Couchbase: {e}")

        return self.cluster

    def get_collection(self, collection_name: str) -> Collection:
        """Get Couchbase collection with caching"""
        if collection_name not in self._collections:
            if self.scope is None:
                self._get_cluster()
            self._collections[collection_name] = self.scope.collection(collection_name)
        return self._collections[collection_name]

    def initialize_schema(self):
        """Initialize Couchbase schema - collections should exist in Couchbase"""
        try:
            logger.info("Couchbase schema initialization - collections should already exist")
            logger.info(
                "Please create collections via Couchbase Admin UI or REST API if they don't exist"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Couchbase schema: {e}")

    # Simplified store and retrieve methods for compatibility

    def store_memory(self, memory_data: dict[str, Any], memory_type: str = "short_term") -> str:
        """Store a memory in Couchbase"""
        try:
            # Generate memory ID if not provided
            if "memory_id" not in memory_data:
                memory_data["memory_id"] = str(uuid4())

            # Determine collection based on memory type
            if memory_type == "short_term":
                collection = self.get_collection(self.SHORT_TERM_MEMORY_COLLECTION)
            elif memory_type == "long_term":
                collection = self.get_collection(self.LONG_TERM_MEMORY_COLLECTION)
            else:
                raise ValueError(f"Invalid memory type: {memory_type}")

            # Ensure datetime fields
            if "created_at" not in memory_data:
                memory_data["created_at"] = datetime.now(timezone.utc)

            # Store document
            collection.upsert(memory_data["memory_id"], memory_data)

            logger.debug(f"Stored {memory_type} memory: {memory_data['memory_id']}")
            return memory_data["memory_id"]

        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            raise

    def get_memories(
        self, namespace: str = "default", memory_type: str = "short_term", limit: int = 100
    ) -> list[dict[str, Any]]:
        """Retrieve memories from Couchbase using N1QL"""
        try:
            cluster = self._get_cluster()

            # Determine collection based on memory type
            if memory_type == "short_term":
                collection_name = self.SHORT_TERM_MEMORY_COLLECTION
            elif memory_type == "long_term":
                collection_name = self.LONG_TERM_MEMORY_COLLECTION
            else:
                raise ValueError(f"Invalid memory type: {memory_type}")

            # Build N1QL query
            query = f"""
            SELECT META().id, *
            FROM `{self.bucket_name}`.`{self.scope_name}`.`{collection_name}`
            WHERE namespace = $namespace
            ORDER BY importance_score DESC, created_at DESC
            LIMIT $limit
            """

            result = cluster.query(query, named_parameters={"namespace": namespace, "limit": limit})

            results = []
            for row in result:
                results.append(row)

            logger.debug(f"Retrieved {len(results)} {memory_type} memories")
            return results

        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []

    def search_memories(
        self, query: str, namespace: str = "default", limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search memories in Couchbase using N1QL"""
        try:
            cluster = self._get_cluster()

            # Build search query for both memory types
            search_query = f"""
            SELECT META().id, *
            FROM `{self.bucket_name}`.`{self.scope_name}`.`{self.SHORT_TERM_MEMORY_COLLECTION}`
            WHERE namespace = $namespace
            AND (LOWER(searchable_content) LIKE LOWER($search_pattern)
                 OR LOWER(summary) LIKE LOWER($search_pattern))
            ORDER BY importance_score DESC
            LIMIT $limit
            UNION ALL
            SELECT META().id, *
            FROM `{self.bucket_name}`.`{self.scope_name}`.`{self.LONG_TERM_MEMORY_COLLECTION}`
            WHERE namespace = $namespace
            AND (LOWER(searchable_content) LIKE LOWER($search_pattern)
                 OR LOWER(summary) LIKE LOWER($search_pattern))
            ORDER BY importance_score DESC
            LIMIT $limit
            """

            params = {
                "namespace": namespace,
                "search_pattern": f"%{query}%",
                "limit": limit,
            }

            result = cluster.query(search_query, named_parameters=params)

            results = []
            for row in result:
                results.append(row)

            logger.debug(f"Couchbase search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def store_chat_history(
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
        """Store chat history in Couchbase"""
        try:
            collection = self.get_collection(self.CHAT_HISTORY_COLLECTION)

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
            logger.debug(f"Stored chat history: {chat_id}")
            return chat_id

        except Exception as e:
            logger.error(f"Failed to store chat history: {e}")
            raise

    def get_database_info(self) -> dict[str, Any]:
        """Get Couchbase database information"""
        try:
            return {
                "database_type": "couchbase",
                "host": self.host,
                "port": self.port,
                "bucket": self.bucket_name,
                "scope": self.scope_name,
                "collection": self.collection_name,
            }
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return {"error": str(e)}

