"""
MongoDB-based database manager for Memori v2.0
Provides MongoDB support parallel to SQLAlchemy with same interface
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from loguru import logger

if TYPE_CHECKING:
    from pymongo import MongoClient
    from pymongo.collection import Collection
    from pymongo.database import Database

try:
    import pymongo  # noqa: F401
    from bson import ObjectId  # noqa: F401
    from pymongo import MongoClient as _MongoClient
    from pymongo.collection import Collection as _Collection
    from pymongo.database import Database as _Database
    from pymongo.errors import (  # noqa: F401
        ConnectionFailure,
        DuplicateKeyError,
        OperationFailure,
    )

    PYMONGO_AVAILABLE = True
    MongoClient = _MongoClient  # type: ignore
    Collection = _Collection  # type: ignore
    Database = _Database  # type: ignore
except ImportError:
    PYMONGO_AVAILABLE = False
    MongoClient = None  # type: ignore
    Collection = None  # type: ignore
    Database = None  # type: ignore
    logger.warning("pymongo not available - MongoDB support disabled")

from ..utils.exceptions import DatabaseError
from ..utils.pydantic_models import ProcessedLongTermMemory


class MongoDBDatabaseManager:
    """MongoDB-based database manager with interface compatible with SQLAlchemy manager"""

    # Constants for collection names
    CHAT_HISTORY_COLLECTION = "chat_history"
    SHORT_TERM_MEMORY_COLLECTION = "short_term_memory"
    LONG_TERM_MEMORY_COLLECTION = "long_term_memory"

    # Database type identifier for database-agnostic code
    database_type = "mongodb"

    def __init__(
        self, database_connect: str, template: str = "basic", schema_init: bool = True
    ):
        if not PYMONGO_AVAILABLE:
            raise DatabaseError(
                "MongoDB support requires pymongo. Install with: pip install pymongo"
            )

        self.database_connect = database_connect
        self.template = template
        self.schema_init = schema_init

        # Parse MongoDB connection string
        self._parse_connection_string()

        # Initialize MongoDB connection
        self.client = None
        self.database = None
        self.database_type = "mongodb"

        # Collection names (matching SQLAlchemy table names)
        self.CHAT_HISTORY_COLLECTION = "chat_history"
        self.SHORT_TERM_MEMORY_COLLECTION = "short_term_memory"
        self.LONG_TERM_MEMORY_COLLECTION = "long_term_memory"

        # Collections cache
        self._collections = {}

        logger.info(f"Initialized MongoDB database manager for {self.database_name}")

    def _parse_connection_string(self):
        """Parse MongoDB connection string to extract components"""
        try:
            # Handle both mongodb:// and mongodb+srv:// schemes
            parsed = urlparse(self.database_connect)

            # Extract host - handle SRV URIs differently
            hostname = parsed.hostname
            is_srv_uri = self.database_connect.startswith("mongodb+srv://")

            if hostname and hostname != "localhost":
                if is_srv_uri:
                    # For SRV URIs, don't try to resolve hostname directly
                    # PyMongo will handle SRV resolution internally
                    self.host = hostname
                else:
                    # For regular mongodb:// URIs, check hostname resolution
                    import socket

                    try:
                        socket.gethostbyname(hostname)
                        self.host = hostname
                    except socket.gaierror:
                        logger.warning(
                            f"Cannot resolve hostname '{hostname}', falling back to localhost"
                        )
                        self.host = "localhost"
            else:
                self.host = hostname or "localhost"

            self.port = parsed.port or 27017
            self.database_name = parsed.path.lstrip("/") or "memori"
            self.username = parsed.username
            self.password = parsed.password

            # Extract query parameters
            self.options = {}
            if parsed.query:
                params = parsed.query.split("&")
                for param in params:
                    if "=" in param:
                        key, value = param.split("=", 1)
                        self.options[key] = value

            logger.debug(
                f"Parsed MongoDB connection: {self.host}:{self.port}/{self.database_name}"
            )

        except Exception as e:
            logger.warning(f"Failed to parse MongoDB connection string: {e}")
            # Set defaults
            self.host = "localhost"
            self.port = 27017
            self.database_name = "memori"
            self.username = None
            self.password = None
            self.options = {}

    def _get_client(self) -> MongoClient:
        """Get MongoDB client connection with support for mongodb+srv DNS seedlist"""
        if self.client is None:
            try:
                # Create MongoDB client with appropriate options
                client_options = {
                    "serverSelectionTimeoutMS": 5000,  # 5 second timeout
                    "connectTimeoutMS": 10000,  # 10 second connect timeout
                    "socketTimeoutMS": 10000,  # 10 second socket timeout
                    "maxPoolSize": 50,  # Connection pool size
                    "retryWrites": True,  # Enable retryable writes
                }

                # Check if this is a mongodb+srv URI for DNS seedlist discovery
                is_srv_uri = self.database_connect.startswith("mongodb+srv://")

                if is_srv_uri:
                    logger.info(
                        "Using MongoDB Atlas DNS seedlist discovery (mongodb+srv)"
                    )

                    # Add modern SRV-specific options for 2025
                    srv_options = {
                        "srvMaxHosts": 0,  # No limit on SRV hosts (default)
                        "srvServiceName": "mongodb",  # Default service name
                    }
                    client_options.update(srv_options)

                    # For SRV URIs, don't use fallback - they handle discovery automatically
                    # Add any additional options from connection string (these override defaults)
                    client_options.update(self.options)

                    # Never set directConnection for SRV URIs
                    client_options.pop("directConnection", None)

                    logger.debug(f"MongoDB+SRV connection options: {client_options}")
                    self.client = MongoClient(self.database_connect, **client_options)

                    # Test connection
                    self.client.admin.command("ping")

                    # Get server info and DNS-resolved hosts for better logging
                    try:
                        server_info = self.client.server_info()
                        version = server_info.get("version", "unknown")
                        logger.info(f"Connected to MongoDB Atlas {version}")

                        # Log DNS-resolved hosts for SRV connections
                        try:
                            topology = self.client.topology_description
                            hosts = []
                            for server in topology.server_descriptions():
                                try:
                                    if hasattr(server, "address") and server.address:
                                        if (
                                            isinstance(server.address, tuple)
                                            and len(server.address) >= 2
                                        ):
                                            hosts.append(
                                                f"{server.address[0]}:{server.address[1]}"
                                            )
                                        else:
                                            hosts.append(str(server.address))
                                except AttributeError:
                                    # Some server descriptions might not have address attribute
                                    continue

                            if hosts:
                                logger.info(
                                    f"DNS resolved MongoDB Atlas hosts: {', '.join(hosts)}"
                                )
                            else:
                                logger.info(
                                    "MongoDB Atlas DNS seedlist discovery completed successfully"
                                )
                        except Exception as e:
                            logger.debug(
                                f"Could not get Atlas server topology info: {e}"
                            )
                    except Exception as e:
                        logger.warning(f"Could not get Atlas server info: {e}")
                        logger.info("Connected to MongoDB Atlas successfully")

                else:
                    # Legacy mongodb:// URI handling with fallbacks
                    # Add any additional options from connection string
                    client_options.update(self.options)

                    # Try original connection string first
                    try:
                        self.client = MongoClient(
                            self.database_connect, **client_options
                        )
                        # Test connection
                        self.client.admin.command("ping")
                        logger.info(
                            "Connected to MongoDB using original connection string"
                        )
                    except Exception as original_error:
                        logger.warning(f"Original connection failed: {original_error}")

                        # Try fallback with explicit host:port (only for non-SRV URIs)
                        fallback_uri = (
                            f"mongodb://{self.host}:{self.port}/{self.database_name}"
                        )
                        logger.info(f"Trying fallback connection: {fallback_uri}")

                        self.client = MongoClient(fallback_uri, **client_options)
                        # Test connection
                        self.client.admin.command("ping")
                        logger.info(
                            f"Connected to MongoDB at {self.host}:{self.port}/{self.database_name}"
                        )

            except Exception as e:
                error_msg = f"Failed to connect to MongoDB: {e}"
                logger.error(error_msg)
                logger.error("Please check that:")
                logger.error("1. MongoDB is running")
                logger.error("2. Connection string is correct")
                logger.error("3. Network connectivity is available")
                raise DatabaseError(error_msg)

        return self.client

    def _get_database(self) -> Database:
        """Get MongoDB database with caching and creation if needed"""
        if self.database is None:
            client = self._get_client()
            self.database = client[self.database_name]

            # Ensure database exists by creating a dummy collection if needed
            try:
                # Try to get database stats - this will fail if DB doesn't exist
                self.database.command("dbstats")
            except Exception:
                # Database doesn't exist, create it by creating a dummy collection
                logger.info(f"Creating MongoDB database: {self.database_name}")
                self.database.create_collection("_init")
                # Remove the dummy collection
                self.database.drop_collection("_init")
                logger.info(f"Database {self.database_name} created successfully")

        return self.database

    def _get_collection(self, collection_name: str) -> Collection:
        """Get MongoDB collection with caching"""
        if collection_name not in self._collections:
            database = self._get_database()
            self._collections[collection_name] = database[collection_name]
        return self._collections[collection_name]

    def _convert_datetime_fields(self, document: dict[str, Any]) -> dict[str, Any]:
        """Convert datetime strings to datetime objects"""
        datetime_fields = [
            "created_at",
            "expires_at",
            "last_accessed",
            "extraction_timestamp",
            "timestamp",
        ]

        for field in datetime_fields:
            if field in document and document[field] is not None:
                if isinstance(document[field], str):
                    try:
                        # Handle various ISO format variations
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

        # Add created_at if missing
        if "created_at" not in document:
            document["created_at"] = datetime.now(timezone.utc)

        return document

    def _convert_to_dict(self, document: dict[str, Any]) -> dict[str, Any]:
        """Convert MongoDB document to dictionary format compatible with SQLAlchemy results"""
        if not document:
            return {}

        result = document.copy()

        # Convert ObjectId to string
        if "_id" in result:
            result["_id"] = str(result["_id"])

        # Convert datetime objects to ISO strings for compatibility
        datetime_fields = [
            "created_at",
            "expires_at",
            "last_accessed",
            "extraction_timestamp",
            "timestamp",
        ]
        for field in datetime_fields:
            if field in result and isinstance(result[field], datetime):
                result[field] = result[field].isoformat()

        # Ensure JSON fields are properly handled
        json_fields = [
            "processed_data",
            "entities_json",
            "keywords_json",
            "supersedes_json",
            "related_memories_json",
            "metadata_json",
        ]
        for field in json_fields:
            if field in result and isinstance(result[field], str):
                try:
                    result[field] = json.loads(result[field])
                except json.JSONDecodeError as e:
                    logger.debug(
                        f"Field '{field}' is not valid JSON, keeping as string: {e}"
                    )
                    pass  # Keep as string if not valid JSON

        return result

    def initialize_schema(self):
        """Initialize MongoDB collections and indexes"""
        if not self.schema_init:
            logger.info("Schema initialization disabled (schema_init=False)")
            return

        try:
            database = self._get_database()
            existing_collections = database.list_collection_names()

            # Create collections if they don't exist
            collections = [
                self.CHAT_HISTORY_COLLECTION,
                self.SHORT_TERM_MEMORY_COLLECTION,
                self.LONG_TERM_MEMORY_COLLECTION,
            ]

            for collection_name in collections:
                if collection_name not in existing_collections:
                    database.create_collection(collection_name)
                    logger.info(f"Created MongoDB collection: {collection_name}")

            # Create indexes for performance
            self._create_indexes()

            logger.info("MongoDB schema initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MongoDB schema: {e}")
            raise DatabaseError(f"Failed to initialize MongoDB schema: {e}")

    def _create_indexes(self):
        """Create essential indexes for performance"""
        try:
            # Chat history indexes
            chat_collection = self._get_collection(self.CHAT_HISTORY_COLLECTION)
            chat_collection.create_index([("chat_id", 1)], unique=True, background=True)
            chat_collection.create_index(
                [("user_id", 1), ("assistant_id", 1), ("session_id", 1)],
                background=True,
            )
            chat_collection.create_index([("timestamp", -1)], background=True)
            chat_collection.create_index([("model", 1)], background=True)

            # Short-term memory indexes
            st_collection = self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION)
            st_collection.create_index([("memory_id", 1)], unique=True, background=True)
            st_collection.create_index(
                [
                    ("user_id", 1),
                    ("assistant_id", 1),
                    ("category_primary", 1),
                    ("importance_score", -1),
                ],
                background=True,
            )
            st_collection.create_index([("expires_at", 1)], background=True)
            st_collection.create_index([("created_at", -1)], background=True)
            st_collection.create_index([("is_permanent_context", 1)], background=True)

            # Enhanced text search index for short-term memory with weights
            try:
                # Check if text index already exists
                existing_indexes = st_collection.list_indexes()
                text_index_exists = any(
                    idx.get("name") == "text_search_index" for idx in existing_indexes
                )

                if not text_index_exists:
                    st_collection.create_index(
                        [
                            ("searchable_content", "text"),
                            ("summary", "text"),
                            ("topic", "text"),
                        ],
                        background=True,  # Use background=True for non-blocking
                        weights={
                            "searchable_content": 10,  # Highest weight for main content
                            "summary": 5,  # Medium weight for summary
                            "topic": 3,  # Lower weight for topic
                        },
                        name="text_search_index",
                    )
                    logger.info(
                        "Created enhanced text search index for short-term memory with weights"
                    )
                else:
                    logger.debug(
                        "Text search index already exists for short-term memory"
                    )
            except Exception as e:
                logger.warning(f"Text index creation failed for short-term memory: {e}")

            # Long-term memory indexes
            lt_collection = self._get_collection(self.LONG_TERM_MEMORY_COLLECTION)
            lt_collection.create_index([("memory_id", 1)], unique=True, background=True)
            lt_collection.create_index(
                [
                    ("user_id", 1),
                    ("assistant_id", 1),
                    ("category_primary", 1),
                    ("importance_score", -1),
                ],
                background=True,
            )
            lt_collection.create_index([("classification", 1)], background=True)
            lt_collection.create_index([("topic", 1)], background=True)
            lt_collection.create_index([("created_at", -1)], background=True)
            lt_collection.create_index([("conscious_processed", 1)], background=True)
            lt_collection.create_index(
                [("processed_for_duplicates", 1)], background=True
            )
            lt_collection.create_index([("promotion_eligible", 1)], background=True)

            # Enhanced text search index for long-term memory with weights
            try:
                # Check if text index already exists
                existing_indexes = lt_collection.list_indexes()
                text_index_exists = any(
                    idx.get("name") == "text_search_index" for idx in existing_indexes
                )

                if not text_index_exists:
                    lt_collection.create_index(
                        [
                            ("searchable_content", "text"),
                            ("summary", "text"),
                            ("topic", "text"),
                            ("classification_reason", "text"),
                        ],
                        background=True,  # Use background=True for non-blocking
                        weights={
                            "searchable_content": 10,  # Highest weight for main content
                            "summary": 8,  # High weight for summary
                            "topic": 5,  # Medium weight for topic
                            "classification_reason": 2,  # Lower weight for reasoning
                        },
                        name="text_search_index",
                    )
                    logger.info(
                        "Created enhanced text search index for long-term memory with weights"
                    )
                else:
                    logger.debug(
                        "Text search index already exists for long-term memory"
                    )
            except Exception as e:
                logger.warning(f"Text index creation failed for long-term memory: {e}")

            # Verify text indexes are functional
            self._verify_text_indexes()

            logger.debug("MongoDB indexes created successfully")

        except Exception as e:
            logger.warning(f"Failed to create some MongoDB indexes: {e}")

    def _verify_text_indexes(self):
        """Verify that text indexes are functional by performing test searches"""
        try:
            # Test short-term memory text index
            st_collection = self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION)
            try:
                # Perform a simple text search to verify index works
                _ = st_collection.find_one({"$text": {"$search": "test"}})
                logger.debug("Short-term memory text index verification successful")
            except Exception as e:
                logger.warning(
                    f"Short-term memory text index may not be functional: {e}"
                )

            # Test long-term memory text index
            lt_collection = self._get_collection(self.LONG_TERM_MEMORY_COLLECTION)
            try:
                # Perform a simple text search to verify index works
                _ = lt_collection.find_one({"$text": {"$search": "test"}})
                logger.debug("Long-term memory text index verification successful")
            except Exception as e:
                logger.warning(
                    f"Long-term memory text index may not be functional: {e}"
                )

            # Check if text indexes exist
            st_indexes = list(st_collection.list_indexes())
            lt_indexes = list(lt_collection.list_indexes())

            st_has_text_index = any(
                "text" in idx.get("key", {}).values() for idx in st_indexes
            )
            lt_has_text_index = any(
                "text" in idx.get("key", {}).values() for idx in lt_indexes
            )

            if st_has_text_index:
                logger.info("Short-term memory collection has text index")
            else:
                logger.warning("Short-term memory collection missing text index")

            if lt_has_text_index:
                logger.info("Long-term memory collection has text index")
            else:
                logger.warning("Long-term memory collection missing text index")

        except Exception as e:
            logger.error(f"Text index verification failed: {e}")

    def store_chat_history(
        self,
        chat_id: str,
        user_input: str,
        ai_output: str,
        model: str,
        timestamp: datetime,
        session_id: str,
        user_id: str = "default",
        assistant_id: str | None = None,
        tokens_used: int = 0,
        metadata: dict[str, Any] | None = None,
    ):
        """Store chat history in MongoDB"""
        try:
            collection = self._get_collection(self.CHAT_HISTORY_COLLECTION)

            document = {
                "chat_id": chat_id,
                "user_input": user_input,
                "ai_output": ai_output,
                "model": model,
                "timestamp": timestamp,
                "session_id": session_id,
                "user_id": user_id,
                "assistant_id": assistant_id,
                "tokens_used": tokens_used,
                "metadata_json": metadata or {},
            }

            # Convert datetime fields
            document = self._convert_datetime_fields(document)

            # Use upsert (insert or update) for compatibility with SQLAlchemy behavior
            collection.replace_one({"chat_id": chat_id}, document, upsert=True)

            logger.debug(f"Stored chat history: {chat_id}")

        except Exception as e:
            logger.error(f"Failed to store chat history: {e}")
            raise DatabaseError(f"Failed to store chat history: {e}")

    def get_chat_history(
        self,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get chat history from MongoDB"""
        try:
            collection = self._get_collection(self.CHAT_HISTORY_COLLECTION)

            # Build filter
            filter_doc = {"user_id": user_id}
            if assistant_id:
                filter_doc["assistant_id"] = assistant_id
            if session_id:
                filter_doc["session_id"] = session_id

            # Execute query
            cursor = collection.find(filter_doc).sort("timestamp", -1).limit(limit)

            results = []
            for document in cursor:
                results.append(self._convert_to_dict(document))

            logger.debug(f"Retrieved {len(results)} chat history entries")
            return results

        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            return []

    def store_short_term_memory(
        self,
        memory_id: str,
        processed_data: str,
        importance_score: float,
        category_primary: str,
        retention_type: str,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
        expires_at: datetime | None = None,
        searchable_content: str = "",
        summary: str = "",
        is_permanent_context: bool = False,
        metadata: dict[str, Any] | None = None,
    ):
        """Store short-term memory in MongoDB"""
        try:
            collection = self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION)

            document = {
                "memory_id": memory_id,
                "processed_data": processed_data,
                "importance_score": importance_score,
                "category_primary": category_primary,
                "retention_type": retention_type,
                "user_id": user_id,
                "assistant_id": assistant_id,
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc),
                "expires_at": expires_at,
                "searchable_content": searchable_content,
                "summary": summary,
                "is_permanent_context": is_permanent_context,
                "metadata_json": metadata or {},
                "access_count": 0,
                "last_accessed": datetime.now(timezone.utc),
            }

            # Convert datetime fields
            document = self._convert_datetime_fields(document)

            # Use upsert (insert or update) for compatibility with SQLAlchemy behavior
            collection.replace_one({"memory_id": memory_id}, document, upsert=True)

            logger.debug(f"Stored short-term memory: {memory_id}")

        except Exception as e:
            logger.error(f"Failed to store short-term memory: {e}")
            raise DatabaseError(f"Failed to store short-term memory: {e}")

    def find_short_term_memory_by_id(
        self,
        memory_id: str,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
    ) -> dict[str, Any] | None:
        """Find a specific short-term memory by memory_id"""
        try:
            collection = self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION)

            # Find memory by memory_id and namespace
            document = collection.find_one({"memory_id": memory_id, "user_id": user_id})

            if document:
                return self._convert_to_dict(document)
            return None

        except Exception as e:
            logger.error(f"Failed to find short-term memory by ID {memory_id}: {e}")
            return None

    def get_short_term_memory(
        self,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
        category_filter: str | None = None,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[dict[str, Any]]:
        """Get short-term memory from MongoDB"""
        try:
            collection = self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION)

            # Build filter
            filter_doc = {
                "user_id": user_id,
                "assistant_id": assistant_id,
                "session_id": session_id,
            }

            if category_filter:
                filter_doc["category_primary"] = category_filter

            if not include_expired:
                current_time = datetime.now(timezone.utc)
                filter_doc["$or"] = [
                    {"expires_at": {"$exists": False}},
                    {"expires_at": None},
                    {"expires_at": {"$gt": current_time}},
                ]

            # Execute query
            cursor = (
                collection.find(filter_doc)
                .sort([("importance_score", -1), ("created_at", -1)])
                .limit(limit)
            )

            results = []
            for document in cursor:
                results.append(self._convert_to_dict(document))

            logger.debug(f"Retrieved {len(results)} short-term memory entries")
            return results

        except Exception as e:
            logger.error(f"Failed to get short-term memory: {e}")
            return []

    def search_short_term_memory(
        self,
        query: str,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search short-term memory using MongoDB text search"""
        try:
            # Clean the query to remove common prefixes that interfere with search
            cleaned_query = query.strip()

            # Remove "User query:" prefix if present (this was causing search failures)
            if cleaned_query.lower().startswith("user query:"):
                cleaned_query = cleaned_query[11:].strip()
                logger.debug(
                    f"Cleaned short-term search query from '{query}' to '{cleaned_query}'"
                )

            if not cleaned_query:
                logger.debug(
                    "Empty query provided for short-term search, returning all short-term memories"
                )
                return self.get_short_term_memory(user_id=user_id, limit=limit)

            collection = self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION)

            current_time = datetime.now(timezone.utc)
            search_filter = {
                "$and": [
                    {"$text": {"$search": cleaned_query}},  # Use cleaned query
                    {
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    },
                    {
                        "$or": [
                            {"expires_at": {"$exists": False}},
                            {"expires_at": None},
                            {"expires_at": {"$gt": current_time}},
                        ]
                    },
                ]
            }

            logger.debug(
                f"Executing short-term MongoDB text search with cleaned query '{cleaned_query}' and filter: {search_filter}"
            )

            # Execute MongoDB text search with text score projection
            cursor = (
                collection.find(search_filter, {"score": {"$meta": "textScore"}})
                .sort(
                    [
                        ("score", {"$meta": "textScore"}),
                        ("importance_score", -1),
                        ("created_at", -1),
                    ]
                )
                .limit(limit)
            )

            results = []
            for document in cursor:
                memory = self._convert_to_dict(document)
                memory["memory_type"] = "short_term"
                memory["search_strategy"] = "mongodb_text"
                # Preserve text search score
                if "score" in document:
                    memory["text_score"] = document["score"]
                results.append(memory)

            logger.debug(
                f"Short-term memory search returned {len(results)} results for query: '{query}'"
            )
            return results

        except Exception as e:
            logger.error(f"Short-term memory search failed: {e}")
            return []

    def update_short_term_memory_access(self, memory_id: str, user_id: str = "default"):
        """Update access count and last accessed time for short-term memory"""
        try:
            collection = self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION)

            collection.update_one(
                {"memory_id": memory_id, "user_id": user_id},
                {
                    "$inc": {"access_count": 1},
                    "$set": {"last_accessed": datetime.now(timezone.utc)},
                },
            )

        except Exception as e:
            logger.debug(f"Failed to update short-term memory access: {e}")

    def get_conscious_memories(
        self,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
        processed_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Get conscious-info labeled memories from long-term memory"""
        try:
            collection = self._get_collection(self.LONG_TERM_MEMORY_COLLECTION)

            # Build filter for conscious-info classification
            filter_doc = {
                "user_id": user_id,
                "assistant_id": assistant_id,
                "session_id": session_id,
                "classification": "conscious-info",
            }

            if processed_only:
                # Get only processed memories
                filter_doc["conscious_processed"] = True
            else:
                # Get ALL conscious-info memories regardless of processed status
                # This is the correct behavior for initial conscious ingestion
                pass  # No additional filter needed

            # Execute query
            cursor = collection.find(filter_doc).sort(
                [("importance_score", -1), ("created_at", -1)]
            )

            results = []
            for document in cursor:
                results.append(self._convert_to_dict(document))

            logger.debug(f"Retrieved {len(results)} conscious memories")
            return results

        except Exception as e:
            logger.error(f"Failed to get conscious memories: {e}")
            return []

    def get_unprocessed_conscious_memories(
        self,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
    ) -> list[dict[str, Any]]:
        """Get unprocessed conscious-info labeled memories from long-term memory"""
        try:
            collection = self._get_collection(self.LONG_TERM_MEMORY_COLLECTION)

            # Build filter for unprocessed conscious-info memories
            filter_doc = {
                "user_id": user_id,
                "assistant_id": assistant_id,
                "session_id": session_id,
                "classification": "conscious-info",
                "$or": [
                    {"conscious_processed": False},
                    {"conscious_processed": {"$exists": False}},
                    {"conscious_processed": None},
                ],
            }

            # Execute query
            cursor = collection.find(filter_doc).sort(
                [("importance_score", -1), ("created_at", -1)]
            )

            results = []
            for document in cursor:
                results.append(self._convert_to_dict(document))

            logger.debug(f"Retrieved {len(results)} unprocessed conscious memories")
            return results

        except Exception as e:
            logger.error(f"Failed to get unprocessed conscious memories: {e}")
            return []

    def mark_conscious_memories_processed(
        self, memory_ids: list[str], user_id: str = "default"
    ):
        """Mark conscious memories as processed"""
        try:
            collection = self._get_collection(self.LONG_TERM_MEMORY_COLLECTION)

            # Update all memories in the list
            result = collection.update_many(
                {"memory_id": {"$in": memory_ids}, "user_id": user_id},
                {"$set": {"conscious_processed": True}},
            )

            logger.debug(
                f"Marked {result.modified_count} memories as conscious processed"
            )

        except Exception as e:
            logger.error(f"Failed to mark conscious memories processed: {e}")

    def store_long_term_memory_enhanced(
        self,
        memory: ProcessedLongTermMemory,
        chat_id: str,
        user_id: str = "default",
        assistant_id: str = None,
        session_id: str = "default",
    ) -> str:
        """Store a ProcessedLongTermMemory in MongoDB with enhanced schema"""
        memory_id = str(uuid.uuid4())

        try:
            collection = self._get_collection(self.LONG_TERM_MEMORY_COLLECTION)

            # Enrich searchable content with keywords and entities for better search
            enriched_content_parts = [memory.content]

            # Add summary for richer search content
            if memory.summary and memory.summary.strip():
                enriched_content_parts.append(memory.summary)

            # Add keywords to searchable content
            if memory.keywords:
                keyword_text = " ".join(memory.keywords)
                enriched_content_parts.append(keyword_text)

            # Add entities to searchable content
            if memory.entities:
                entity_text = " ".join(memory.entities)
                enriched_content_parts.append(entity_text)

            # Create enriched searchable content
            enriched_searchable_content = " ".join(enriched_content_parts)

            # Convert Pydantic model to MongoDB document
            document = {
                "memory_id": memory_id,
                "original_chat_id": chat_id,
                "processed_data": memory.model_dump(mode="json"),
                "importance_score": memory.importance_score,
                "category_primary": memory.classification.value,
                "retention_type": "long_term",
                "user_id": user_id,
                "assistant_id": assistant_id,
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc),
                "searchable_content": enriched_searchable_content,
                "summary": memory.summary,
                "novelty_score": 0.5,
                "relevance_score": 0.5,
                "actionability_score": 0.5,
                "classification": memory.classification.value,
                "memory_importance": memory.importance.value,
                "topic": memory.topic,
                "entities_json": memory.entities,
                "keywords_json": memory.keywords,
                "is_user_context": memory.is_user_context,
                "is_preference": memory.is_preference,
                "is_skill_knowledge": memory.is_skill_knowledge,
                "is_current_project": memory.is_current_project,
                "promotion_eligible": memory.promotion_eligible,
                "duplicate_of": memory.duplicate_of,
                "supersedes_json": memory.supersedes,
                "related_memories_json": memory.related_memories,
                "confidence_score": memory.confidence_score,
                "extraction_timestamp": memory.extraction_timestamp,
                "classification_reason": memory.classification_reason,
                "processed_for_duplicates": False,
                "conscious_processed": False,  # Ensure new memories start as unprocessed
                "access_count": 0,
            }

            # Convert datetime fields
            document = self._convert_datetime_fields(document)

            # Insert document
            collection.insert_one(document)

            logger.debug(f"Stored enhanced long-term memory {memory_id}")
            return memory_id

        except Exception as e:
            logger.error(f"Failed to store enhanced long-term memory: {e}")
            raise DatabaseError(f"Failed to store enhanced long-term memory: {e}")

    def search_memories(
        self,
        query: str,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
        category_filter: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search memories using MongoDB text search with SQL-compatible interface"""
        try:
            logger.debug(
                f"MongoDB search_memories called: query='{query}', user_id='{user_id}', limit={limit}"
            )

            # Handle empty queries consistently with SQL
            if not query or not query.strip():
                logger.debug(
                    "Empty query provided, returning empty results for consistency"
                )
                return []

            # Clean query (remove common problematic prefixes)
            cleaned_query = query.strip()
            if cleaned_query.lower().startswith("user query:"):
                cleaned_query = cleaned_query[11:].strip()
                logger.debug(f"Cleaned query from '{query}' to '{cleaned_query}'")

            if not cleaned_query:
                return []

            results = []
            collections_to_search = [
                (self.SHORT_TERM_MEMORY_COLLECTION, "short_term"),
                (self.LONG_TERM_MEMORY_COLLECTION, "long_term"),
            ]

            # Search each collection
            for collection_name, memory_type in collections_to_search:
                collection = self._get_collection(collection_name)

                try:
                    # Build search filter
                    search_filter: dict[str, Any] = {
                        "$text": {"$search": cleaned_query},
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    }

                    # Add category filter if specified
                    if category_filter:
                        search_filter["category_primary"] = {"$in": category_filter}

                    # For short-term memories, exclude expired ones
                    if memory_type == "short_term":
                        current_time = datetime.now(timezone.utc)
                        search_filter = {
                            "$and": [
                                {"$text": {"$search": cleaned_query}},
                                {
                                    "user_id": user_id,
                                    "assistant_id": assistant_id,
                                    "session_id": session_id,
                                },
                                {
                                    "$or": [
                                        {"expires_at": {"$exists": False}},
                                        {"expires_at": None},
                                        {"expires_at": {"$gt": current_time}},
                                    ]
                                },
                            ]
                        }
                        if category_filter:
                            search_filter["$and"].append(
                                {"category_primary": {"$in": category_filter}}
                            )

                    # Execute search with standardized projection
                    cursor = (
                        collection.find(
                            search_filter, {"score": {"$meta": "textScore"}}
                        )
                        .sort(
                            [
                                ("score", {"$meta": "textScore"}),
                                ("importance_score", -1),
                                ("created_at", -1),
                            ]
                        )
                        .limit(limit)
                    )

                    for document in cursor:
                        memory = self._convert_to_dict(document)

                        # Standardize fields for SQL compatibility
                        memory["memory_type"] = memory_type
                        memory["search_strategy"] = "mongodb_text"
                        memory["search_score"] = document.get(
                            "score", 0.8
                        )  # MongoDB text score

                        # Ensure all required fields are present
                        if "importance_score" not in memory:
                            memory["importance_score"] = 0.5
                        if "created_at" not in memory:
                            memory["created_at"] = datetime.now(
                                timezone.utc
                            ).isoformat()

                        results.append(memory)

                except Exception as search_error:
                    logger.error(
                        f"MongoDB search failed for {collection_name}: {search_error}"
                    )
                    continue

            # Sort results by search score for consistency
            results.sort(
                key=lambda x: (x.get("search_score", 0), x.get("importance_score", 0)),
                reverse=True,
            )

            logger.debug(f"MongoDB search returned {len(results)} results")
            return results[:limit]

        except Exception as e:
            logger.error(f"MongoDB search_memories failed: {e}")
            # Return empty list to maintain compatibility with SQL manager
            return []

    def get_memory_stats(
        self,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
    ) -> dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            database = self._get_database()

            stats = {}

            # Basic counts
            stats["chat_history_count"] = self._get_collection(
                self.CHAT_HISTORY_COLLECTION
            ).count_documents(
                {
                    "user_id": user_id,
                    "assistant_id": assistant_id,
                    "session_id": session_id,
                }
            )

            stats["short_term_count"] = self._get_collection(
                self.SHORT_TERM_MEMORY_COLLECTION
            ).count_documents(
                {
                    "user_id": user_id,
                    "assistant_id": assistant_id,
                    "session_id": session_id,
                }
            )

            stats["long_term_count"] = self._get_collection(
                self.LONG_TERM_MEMORY_COLLECTION
            ).count_documents(
                {
                    "user_id": user_id,
                    "assistant_id": assistant_id,
                    "session_id": session_id,
                }
            )

            # Category breakdown for short-term memories
            short_categories = self._get_collection(
                self.SHORT_TERM_MEMORY_COLLECTION
            ).aggregate(
                [
                    {
                        "$match": {
                            "user_id": user_id,
                            "assistant_id": assistant_id,
                            "session_id": session_id,
                        }
                    },
                    {"$group": {"_id": "$category_primary", "count": {"$sum": 1}}},
                ]
            )

            categories = {}
            for doc in short_categories:
                categories[doc["_id"]] = doc["count"]

            # Category breakdown for long-term memories
            long_categories = self._get_collection(
                self.LONG_TERM_MEMORY_COLLECTION
            ).aggregate(
                [
                    {
                        "$match": {
                            "user_id": user_id,
                            "assistant_id": assistant_id,
                            "session_id": session_id,
                        }
                    },
                    {"$group": {"_id": "$category_primary", "count": {"$sum": 1}}},
                ]
            )

            for doc in long_categories:
                categories[doc.get("_id", "unknown")] = (
                    categories.get(doc.get("_id", "unknown"), 0) + doc["count"]
                )

            stats["memories_by_category"] = categories

            # Average importance scores
            short_avg_pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_importance": {"$avg": "$importance_score"},
                    }
                },
            ]
            short_avg_result = list(
                self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION).aggregate(
                    short_avg_pipeline
                )
            )
            short_avg = short_avg_result[0]["avg_importance"] if short_avg_result else 0

            long_avg_pipeline = [
                {
                    "$match": {
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_importance": {"$avg": "$importance_score"},
                    }
                },
            ]
            long_avg_result = list(
                self._get_collection(self.LONG_TERM_MEMORY_COLLECTION).aggregate(
                    long_avg_pipeline
                )
            )
            long_avg = long_avg_result[0]["avg_importance"] if long_avg_result else 0

            total_memories = stats["short_term_count"] + stats["long_term_count"]
            if total_memories > 0:
                # Weight averages by count
                total_avg = (
                    (short_avg * stats["short_term_count"])
                    + (long_avg * stats["long_term_count"])
                ) / total_memories
                stats["average_importance"] = float(total_avg) if total_avg else 0.0
            else:
                stats["average_importance"] = 0.0

            # Database info
            stats["database_type"] = self.database_type
            stats["database_url"] = (
                self.database_connect.split("@")[-1]
                if "@" in self.database_connect
                else self.database_connect
            )

            # MongoDB-specific stats
            try:
                db_stats = database.command("dbStats")
                stats["storage_size"] = db_stats.get("storageSize", 0)
                stats["data_size"] = db_stats.get("dataSize", 0)
                stats["index_size"] = db_stats.get("indexSize", 0)
                stats["collections"] = db_stats.get("collections", 0)
            except Exception as e:
                logger.debug(f"Could not get database stats: {e}")

            return stats

        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}

    def clear_memory(
        self,
        user_id: str = "default",
        assistant_id: str | None = None,
        session_id: str = "default",
        memory_type: str | None = None,
    ):
        """Clear memory data"""
        try:
            if memory_type == "short_term":
                self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION).delete_many(
                    {
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    }
                )
            elif memory_type == "long_term":
                self._get_collection(self.LONG_TERM_MEMORY_COLLECTION).delete_many(
                    {
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    }
                )
            elif memory_type == "chat_history":
                self._get_collection(self.CHAT_HISTORY_COLLECTION).delete_many(
                    {
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    }
                )
            else:  # Clear all
                self._get_collection(self.SHORT_TERM_MEMORY_COLLECTION).delete_many(
                    {
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    }
                )
                self._get_collection(self.LONG_TERM_MEMORY_COLLECTION).delete_many(
                    {
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    }
                )
                self._get_collection(self.CHAT_HISTORY_COLLECTION).delete_many(
                    {
                        "user_id": user_id,
                        "assistant_id": assistant_id,
                        "session_id": session_id,
                    }
                )

            logger.info(f"Cleared {memory_type or 'all'} memory for user_id: {user_id}")

        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
            raise DatabaseError(f"Failed to clear memory: {e}")

    def _get_connection(self):
        """
        Compatibility method for legacy code that expects raw database connections.
        Returns a MongoDB-compatible connection wrapper.
        """
        from contextlib import contextmanager

        @contextmanager
        def connection_context():
            class MongoDBConnection:
                """Wrapper that provides SQLAlchemy-like interface for MongoDB"""

                def __init__(self, manager):
                    self.manager = manager
                    self.database = manager._get_database()

                def execute(self, query, parameters=None):
                    """Execute query with parameter substitution"""
                    try:
                        # This is a compatibility shim for raw SQL-like queries
                        # Convert basic queries to MongoDB operations
                        if isinstance(query, str):
                            # Handle common SQL-like patterns and convert to MongoDB
                            if "SELECT" in query.upper():
                                return self._handle_select_query(query, parameters)
                            elif "INSERT" in query.upper():
                                return self._handle_insert_query(query, parameters)
                            elif "UPDATE" in query.upper():
                                return self._handle_update_query(query, parameters)
                            elif "DELETE" in query.upper():
                                return self._handle_delete_query(query, parameters)

                        # Fallback for direct MongoDB operations
                        return MockQueryResult([])

                    except Exception as e:
                        logger.warning(f"Query execution failed: {e}")
                        return MockQueryResult([])

                def _handle_select_query(self, query, parameters):
                    """Handle SELECT-like queries"""
                    # Simple pattern matching for common queries
                    if "short_term_memory" in query:
                        collection = self.manager._get_collection(
                            self.manager.SHORT_TERM_MEMORY_COLLECTION
                        )
                        filter_doc = {}
                        if parameters:
                            # Basic parameter substitution
                            if "namespace" in parameters:
                                filter_doc["namespace"] = parameters["namespace"]

                        cursor = (
                            collection.find(filter_doc)
                            .sort("created_at", -1)
                            .limit(100)
                        )
                        results = [self.manager._convert_to_dict(doc) for doc in cursor]
                        return MockQueryResult(results)

                    return MockQueryResult([])

                def _handle_insert_query(self, _query, _parameters):
                    """Handle INSERT-like queries"""
                    # This is a compatibility shim - not fully implemented
                    return MockQueryResult([])

                def _handle_update_query(self, _query, _parameters):
                    """Handle UPDATE-like queries"""
                    # This is a compatibility shim - not fully implemented
                    return MockQueryResult([])

                def _handle_delete_query(self, _query, _parameters):
                    """Handle DELETE-like queries"""
                    # This is a compatibility shim - not fully implemented
                    return MockQueryResult([])

                def commit(self):
                    """Commit transaction (no-op for MongoDB single operations)"""
                    pass

                def rollback(self):
                    """Rollback transaction (no-op for MongoDB single operations)"""
                    pass

                def close(self):
                    """Close connection (no-op, connection pooling handled by client)"""
                    pass

                def scalar(self):
                    """Compatibility method"""
                    return None

                def fetchall(self):
                    """Compatibility method"""
                    return []

            yield MongoDBConnection(self)

        return connection_context()

    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            self.client = None
            self.database = None
            self._collections.clear()
            logger.info("MongoDB connection closed")

    def get_database_info(self) -> dict[str, Any]:
        """Get MongoDB database information and capabilities"""
        try:
            client = self._get_client()
            database = self._get_database()

            info = {
                "database_type": self.database_type,
                "database_name": self.database_name,
                "connection_string": (
                    self.database_connect.replace(
                        f"{self.username}:{self.password}@", "***:***@"
                    )
                    if self.username and self.password
                    else self.database_connect
                ),
            }

            # Server information
            try:
                server_info = client.server_info()
                info["version"] = server_info.get("version", "unknown")
                info["driver"] = "pymongo"
            except Exception:
                info["version"] = "unknown"
                info["driver"] = "pymongo"

            # Database stats
            try:
                stats = database.command("dbStats")
                info["collections_count"] = stats.get("collections", 0)
                info["data_size"] = stats.get("dataSize", 0)
                info["storage_size"] = stats.get("storageSize", 0)
                info["indexes_count"] = stats.get("indexes", 0)
            except Exception:
                pass

            # Capabilities
            info["supports_fulltext"] = True
            info["auto_creation_enabled"] = (
                True  # MongoDB creates collections automatically
            )

            return info

        except Exception as e:
            logger.warning(f"Could not get MongoDB database info: {e}")
            return {
                "database_type": self.database_type,
                "version": "unknown",
                "supports_fulltext": True,
                "error": str(e),
            }


class MockQueryResult:
    """Mock query result for compatibility with SQLAlchemy-style code"""

    def __init__(self, results):
        self.results = results
        self._index = 0

    def fetchall(self):
        """Return all results"""
        return self.results

    def fetchone(self):
        """Return one result"""
        if self._index < len(self.results):
            result = self.results[self._index]
            self._index += 1
            return result
        return None

    def scalar(self):
        """Return scalar value"""
        if self.results:
            first_result = self.results[0]
            if isinstance(first_result, dict):
                # Return first value from dict
                return next(iter(first_result.values()))
            return first_result
        return None

    def __iter__(self):
        """Make iterable"""
        return iter(self.results)
