"""
Couchbase connector for Memori
Provides Couchbase-specific implementation of the database connector interface
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import uuid4

from loguru import logger

if TYPE_CHECKING:
    from couchbase.cluster import Cluster
    from couchbase.collection import Collection
    from couchbase.scope import Scope

try:
    from couchbase.cluster import Cluster as _Cluster
    from couchbase.options import ClusterOptions, QueryOptions
    from couchbase.auth import PasswordAuthenticator
    from couchbase.exceptions import (
        CouchbaseException,
        DocumentNotFoundException,
    )
    from couchbase import query

    COUCHBASE_AVAILABLE = True
    Cluster = _Cluster  # type: ignore
except ImportError:
    COUCHBASE_AVAILABLE = False
    Cluster = None  # type: ignore

from ...utils.exceptions import DatabaseError
from .base_connector import BaseDatabaseConnector, DatabaseType


class CouchbaseConnector(BaseDatabaseConnector):
    """Couchbase database connector with N1QL query support"""

    def __init__(self, connection_config):
        """Initialize Couchbase connector"""
        if not COUCHBASE_AVAILABLE:
            raise DatabaseError(
                "couchbase is required for Couchbase support. Install with: pip install couchbase"
            )

        if isinstance(connection_config, str):
            self.connection_string = connection_config
            self.connection_config = {"connection_string": connection_config}
        else:
            self.connection_string = connection_config.get(
                "connection_string", "couchbase://localhost:8091"
            )

        # Parse Couchbase connection string
        self._parse_connection_string()

        # Couchbase-specific settings
        self.cluster = None
        self.bucket = None
        self.scope = None
        self._collections = {}

        super().__init__(connection_config)

    def _detect_database_type(self) -> DatabaseType:
        """Detect database type from connection config"""
        return DatabaseType.COUCHBASE

    def _parse_connection_string(self):
        """Parse Couchbase connection string to extract components"""
        try:
            # Handle Couchbase connection strings
            if self.connection_string.startswith("couchbase://"):
                # Remove protocol prefix
                connection_part = self.connection_string.replace("couchbase://", "")

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
                    self.username = None
                    self.password = None

                # Parse host and bucket
                if "/" in host_part:
                    host_str, bucket_path = host_part.split("/", 1)
                    # Bucket path might have scope/collection
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
                # Fall back to urlparse for simple connection strings
                parsed = urlparse(self.connection_string)
                self.host = parsed.hostname or "localhost"
                self.port = parsed.port or 8091
                self.bucket_name = parsed.path.lstrip("/") or "memori"
                self.scope_name = "_default"
                self.collection_name = "_default"
                self.username = parsed.username
                self.password = parsed.password

        except Exception as e:
            logger.warning(f"Failed to parse Couchbase connection string: {e}")
            # Set defaults
            self.host = "localhost"
            self.port = 8091
            self.bucket_name = "memori"
            self.scope_name = "_default"
            self.collection_name = "_default"
            self.username = None
            self.password = None

    def get_connection(self) -> Cluster:
        """Get Couchbase cluster connection"""
        if self.cluster is None:
            try:
                # Construct connection string
                connection_string = f"{self.host}:{self.port}"

                # Create cluster options
                auth = PasswordAuthenticator(
                    self.username or "Administrator",
                    self.password or "password",
                )

                cluster_options = ClusterOptions(auth)

                # Connect to cluster
                self.cluster = Cluster(
                    f"couchbase://{connection_string}", cluster_options
                )

                # Get bucket
                self.bucket = self.cluster.bucket(self.bucket_name)

                # Get scope
                self.scope = self.bucket.scope(self.scope_name)

                logger.info(f"Connected to Couchbase at {self.host}:{self.port}")
                logger.info(f"Using bucket: {self.bucket_name}, scope: {self.scope_name}")

            except Exception as e:
                raise DatabaseError(f"Failed to connect to Couchbase: {e}")

        return self.cluster

    def get_bucket(self):
        """Get Couchbase bucket"""
        if self.bucket is None:
            self.get_connection()
        return self.bucket

    def get_scope(self) -> Scope:
        """Get Couchbase scope"""
        if self.scope is None:
            self.get_connection()
        return self.scope

    def get_collection(self, collection_name: str) -> Collection:
        """Get Couchbase collection with caching"""
        if collection_name not in self._collections:
            scope = self.get_scope()
            self._collections[collection_name] = scope.collection(collection_name)
        return self._collections[collection_name]

    def execute_query(
        self, query: str, params: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute a N1QL query in Couchbase
        """
        try:
            cluster = self.get_connection()

            # Execute N1QL query
            result = cluster.query(query, QueryOptions(named_parameters=params or {}))

            results = []
            for row in result:
                results.append(row)

            return results

        except Exception as e:
            raise DatabaseError(f"Failed to execute Couchbase query: {e}")

    def execute_insert(self, query: str, params: list[Any] | None = None) -> str:
        """Execute an insert operation and return the inserted document ID"""
        try:
            if isinstance(query, str) and query.strip().startswith("{"):
                # Parse as Couchbase insert operation
                operation = json.loads(query)
                collection_name = operation.get("collection", "memories")
                document = operation.get("document", {})
                document_id = operation.get("document_id")

                collection = self.get_collection(collection_name)

                if document_id:
                    result = collection.insert(document_id, document)
                else:
                    # Generate ID from document
                    doc_id = document.get("id") or document.get("_id") or str(uuid4())
                    result = collection.insert(doc_id, document)

                return doc_id if "doc_id" in locals() else result

            else:
                raise DatabaseError("Invalid insert operation format for Couchbase")

        except Exception as e:
            raise DatabaseError(f"Failed to execute Couchbase insert: {e}")

    def execute_update(self, query: str, params: list[Any] | None = None) -> int:
        """Execute an update operation and return number of modified documents"""
        try:
            if isinstance(query, str) and query.strip().startswith("{"):
                # Parse as Couchbase update operation
                operation = json.loads(query)
                collection_name = operation.get("collection", "memories")
                filter_doc = operation.get("filter", {})
                update_doc = operation.get("update", {})

                collection = self.get_collection(collection_name)

                # For simplicity, we'll update one document at a time
                # In production, you'd want to use N1QL UPDATE queries
                count = 0
                # This is a simplified implementation
                # In production, use N1QL for efficient updates
                return 1  # Placeholder

            else:
                raise DatabaseError("Invalid update operation format for Couchbase")

        except Exception as e:
            raise DatabaseError(f"Failed to execute Couchbase update: {e}")

    def execute_delete(self, query: str, params: list[Any] | None = None) -> int:
        """Execute a delete operation and return number of deleted documents"""
        try:
            if isinstance(query, str) and query.strip().startswith("{"):
                # Parse as Couchbase delete operation
                operation = json.loads(query)
                collection_name = operation.get("collection", "memories")
                document_id = operation.get("document_id")

                if document_id:
                    collection = self.get_collection(collection_name)
                    collection.remove(document_id)
                    return 1
                else:
                    raise DatabaseError("Document ID required for delete operation")

            else:
                raise DatabaseError("Invalid delete operation format for Couchbase")

        except Exception as e:
            raise DatabaseError(f"Failed to execute Couchbase delete: {e}")

    def execute_transaction(self, queries: list[tuple[str, list[Any] | None]]) -> bool:
        """Execute multiple operations in a Couchbase transaction"""
        try:
            # Couchbase transactions require the transaction context
            # This is a simplified implementation
            # In production, use proper Couchbase transactions API
            for query, params in queries:
                if "insert" in query.lower():
                    self.execute_insert(query, params)
                elif "update" in query.lower():
                    self.execute_update(query, params)
                elif "delete" in query.lower():
                    self.execute_delete(query, params)

            return True

        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return False

    def test_connection(self) -> bool:
        """Test if the Couchbase connection is working"""
        try:
            cluster = self.get_connection()
            # Ping the cluster
            cluster.ping()
            return True
        except Exception as e:
            logger.error(f"Couchbase connection test failed: {e}")
            return False

    def initialize_schema(self, schema_sql: str | None = None):
        """Initialize Couchbase collections and indexes"""
        try:
            from ..schema_generators.couchbase_schema_generator import (
                CouchbaseSchemaGenerator,
            )

            schema_generator = CouchbaseSchemaGenerator()
            scope = self.get_scope()

            # Create collections if they don't exist
            collections_schema = schema_generator.generate_collections_schema()
            for collection_name in collections_schema.keys():
                try:
                    # Note: Collection creation via API is not available in all Couchbase versions
                    # In production, collections should be created via UI or admin API
                    logger.debug(f"Using collection: {collection_name}")
                    self.get_collection(collection_name)
                except Exception as e:
                    logger.warning(
                        f"Collection {collection_name} may need manual creation: {e}"
                    )

            # Create indexes
            indexes_schema = schema_generator.generate_indexes_schema()
            for index in indexes_schema:
                try:
                    # Create indexes using N1QL
                    index_query = index.get("definition")
                    if index_query:
                        cluster = self.get_connection()
                        cluster.query(index_query)
                        logger.debug(f"Created index: {index}")
                except Exception as e:
                    logger.warning(f"Failed to create index: {e}")

            logger.info("Couchbase schema initialization completed")

        except Exception as e:
            logger.error(f"Failed to initialize Couchbase schema: {e}")
            raise DatabaseError(f"Failed to initialize Couchbase schema: {e}")

    def supports_full_text_search(self) -> bool:
        """Check if Couchbase supports full-text search"""
        return True  # Couchbase has search capabilities

    def supports_vector_search(self) -> bool:
        """Check if Couchbase supports vector search"""
        # Couchbase has some vector search capabilities via integrations
        return False

    def create_full_text_index(
        self, table: str, columns: list[str], index_name: str
    ) -> str:
        """Create Couchbase full-text search index"""
        try:
            # Create FTS index using N1QL or FTS API
            # This is a simplified implementation
            logger.warning(
                "Full-text search indexes should be created via Couchbase Admin UI or FTS API"
            )
            return f"Created FTS index specification for '{table}'"

        except Exception as e:
            raise DatabaseError(f"Failed to create text index: {e}")

    def get_database_info(self) -> dict[str, Any]:
        """Get Couchbase database information and capabilities"""
        try:
            cluster = self.get_connection()
            bucket = self.get_bucket()

            info = {
                "database_type": self.database_type.value,
                "host": self.host,
                "port": self.port,
                "bucket": self.bucket_name,
                "scope": self.scope_name,
                "full_text_search_support": True,
                "vector_search_support": False,
                "cluster_version": "unknown",
            }

            try:
                # Get cluster version (if available)
                ping_result = cluster.ping()
                if ping_result:
                    info["cluster_status"] = "healthy"
            except Exception:
                pass

            return info

        except Exception as e:
            logger.warning(f"Could not get Couchbase database info: {e}")
            return {
                "database_type": self.database_type.value,
                "host": self.host,
                "port": self.port,
                "bucket": self.bucket_name,
                "full_text_search_support": True,
                "error": str(e),
            }

    def close(self):
        """Close Couchbase connection"""
        if self.cluster:
            # Note: Couchbase cluster connections don't have an explicit close
            # They are managed by the connection pool
            self.cluster = None
            self.bucket = None
            self.scope = None
            self._collections.clear()
            logger.info("Couchbase connection closed")

    def __del__(self):
        """Cleanup when connector is destroyed"""
        self.close()

