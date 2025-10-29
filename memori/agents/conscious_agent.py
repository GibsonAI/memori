"""
Conscious Agent for User Context Management

This agent copies conscious-info labeled memories from long-term memory
directly to short-term memory for immediate context availability.

Supports both SQL and MongoDB database backends.
"""

import json
from datetime import datetime

from loguru import logger


class ConsciouscAgent:
    """
    Agent that copies conscious-info labeled memories from long-term memory
    directly to short-term memory for immediate context availability.

    Runs once at program startup when conscious_ingest=True.
    """

    def __init__(self):
        """Initialize the conscious agent"""
        self.context_initialized = False
        self._database_type = None  # Will be detected from db_manager

    def _detect_database_type(self, db_manager):
        """Detect database type from db_manager with fallback detection"""
        if self._database_type is None:
            # Try multiple detection methods
            if hasattr(db_manager, "database_type"):
                self._database_type = db_manager.database_type
            elif hasattr(db_manager, "__class__"):
                class_name = db_manager.__class__.__name__
                if "MongoDB" in class_name:
                    self._database_type = "mongodb"
                elif "SQLAlchemy" in class_name:
                    self._database_type = "sql"
                else:
                    # Fallback detection by checking for MongoDB-specific methods
                    if hasattr(db_manager, "_get_collection"):
                        self._database_type = "mongodb"
                    else:
                        self._database_type = "sql"
            else:
                # Ultimate fallback
                self._database_type = "sql"

            logger.debug(
                f"ConsciouscAgent: Detected database type: {self._database_type}"
            )
        return self._database_type

    async def run_conscious_ingest(self, db_manager, user_id: str = "default") -> bool:
        """
        Run conscious context ingestion once at program startup

        Copies all conscious-info labeled memories from long-term memory
        directly to short-term memory as permanent context

        Args:
            db_manager: Database manager instance (SQL or MongoDB)
            user_id: User identifier for multi-tenant isolation

        Returns:
            True if memories were copied, False otherwise
        """
        try:
            db_type = self._detect_database_type(db_manager)

            # Get all conscious-info labeled memories
            conscious_memories = await self._get_conscious_memories(db_manager, user_id)

            if not conscious_memories:
                logger.info("ConsciouscAgent: No conscious-info memories found")
                return False

            # Copy each conscious-info memory directly to short-term memory
            copied_count = 0
            for memory_data in conscious_memories:
                success = await self._copy_memory_to_short_term(
                    db_manager, user_id, memory_data
                )
                if success:
                    copied_count += 1

            # Mark memories as processed
            if db_type == "mongodb":
                memory_ids = [
                    mem.get("memory_id")
                    for mem in conscious_memories
                    if isinstance(mem, dict) and mem.get("memory_id")
                ]
            else:
                memory_ids = [
                    row[0] for row in conscious_memories
                ]  # memory_id is first column for SQL

            await self._mark_memories_processed(db_manager, memory_ids, user_id)

            self.context_initialized = True
            logger.info(
                f"ConsciouscAgent: Copied {copied_count} conscious-info memories to short-term memory"
            )

            return copied_count > 0

        except Exception as e:
            logger.error(f"ConsciouscAgent: Conscious ingest failed: {e}")
            return False

    async def initialize_existing_conscious_memories(
        self, db_manager, user_id: str = "default", limit: int = 10
    ) -> bool:
        """
        Initialize by copying ALL existing conscious-info memories to short-term memory
        This is called when both auto_ingest=True and conscious_ingest=True
        to ensure essential conscious information is immediately available

        Args:
            db_manager: Database manager instance
            user_id: User identifier for multi-tenant isolation

        Returns:
            True if memories were processed, False otherwise
        """
        try:
            db_type = self._detect_database_type(db_manager)

            if db_type == "mongodb":
                # Use MongoDB-specific method to get ALL conscious memories
                existing_conscious_memories = db_manager.get_conscious_memories(
                    user_id=user_id
                )
            else:
                # Use SQL method
                from sqlalchemy import text

                with db_manager._get_connection() as connection:
                    # Get top conscious-info labeled memories from long-term memory (limited for performance)
                    cursor = connection.execute(
                        text(
                            """SELECT memory_id, processed_data, summary, searchable_content,
                                  importance_score, created_at
                           FROM long_term_memory
                           WHERE user_id = :user_id AND classification = 'conscious-info'
                           ORDER BY importance_score DESC, created_at DESC
                           LIMIT :limit"""
                        ),
                        {"user_id": user_id, "limit": limit},
                    )
                    existing_conscious_memories = cursor.fetchall()

            if not existing_conscious_memories:
                logger.info(
                    "ConsciouscAgent: No existing conscious-info memories found for initialization"
                )
                return False

            logger.info(
                f"ConsciouscAgent: Found {len(existing_conscious_memories)} conscious-info memories to initialize"
            )

            copied_count = 0
            for memory_data in existing_conscious_memories:
                success = await self._copy_memory_to_short_term(
                    db_manager, user_id, memory_data
                )
                if success:
                    copied_count += 1

            if copied_count > 0:
                logger.info(
                    f"ConsciouscAgent: Initialized {copied_count} existing conscious-info memories to short-term memory"
                )
                return True
            else:
                logger.info(
                    "ConsciouscAgent: No new conscious memories to initialize (all were duplicates)"
                )
                return False

        except Exception as e:
            logger.error(
                f"ConsciouscAgent: Failed to initialize existing conscious memories: {e}"
            )
            return False

    async def check_for_context_updates(
        self, db_manager, user_id: str = "default"
    ) -> bool:
        """
        Check for new conscious-info memories and copy them to short-term memory

        Args:
            db_manager: Database manager instance
            user_id: User identifier for multi-tenant isolation

        Returns:
            True if new memories were copied, False otherwise
        """
        try:
            # Get unprocessed conscious memories
            new_memories = await self._get_unprocessed_conscious_memories(
                db_manager, user_id
            )

            if not new_memories:
                return False

            # Copy each new memory directly to short-term memory
            copied_count = 0
            for memory_row in new_memories:
                success = await self._copy_memory_to_short_term(
                    db_manager, user_id, memory_row
                )
                if success:
                    copied_count += 1

            # Mark new memories as processed
            db_type = self._detect_database_type(db_manager)
            if db_type == "mongodb":
                memory_ids = [
                    mem.get("memory_id")
                    for mem in new_memories
                    if isinstance(mem, dict) and mem.get("memory_id")
                ]
            else:
                memory_ids = [
                    row[0] for row in new_memories
                ]  # memory_id is first column for SQL

            if memory_ids:
                await self._mark_memories_processed(db_manager, memory_ids, user_id)
            else:
                logger.warning(
                    "ConsciouscAgent: No valid memory IDs found to mark as processed"
                )

            logger.info(
                f"ConsciouscAgent: Copied {copied_count} new conscious-info memories to short-term memory"
            )
            return copied_count > 0

        except Exception as e:
            logger.error(
                f"ConsciouscAgent: Context update failed with exception: {type(e).__name__}: {e}"
            )
            import traceback

            logger.error(
                f"ConsciouscAgent: Full error traceback: {traceback.format_exc()}"
            )
            return False

    async def _get_conscious_memories(self, db_manager, user_id: str) -> list:
        """Get all conscious-info labeled memories from long-term memory (database-agnostic)"""
        try:
            db_type = self._detect_database_type(db_manager)

            if db_type == "mongodb":
                # Use MongoDB-specific method
                memories = db_manager.get_conscious_memories(user_id=user_id)
                return memories
            else:
                # Use SQL method
                from sqlalchemy import text

                with db_manager._get_connection() as connection:
                    cursor = connection.execute(
                        text(
                            """SELECT memory_id, processed_data, summary, searchable_content,
                                  importance_score, created_at
                           FROM long_term_memory
                           WHERE user_id = :user_id AND classification = 'conscious-info'
                           ORDER BY importance_score DESC, created_at DESC"""
                        ),
                        {"user_id": user_id},
                    )
                    return cursor.fetchall()

        except Exception as e:
            logger.error(f"ConsciouscAgent: Failed to get conscious memories: {e}")
            return []

    async def _get_unprocessed_conscious_memories(
        self, db_manager, user_id: str
    ) -> list:
        """Get unprocessed conscious-info labeled memories from long-term memory (database-agnostic)"""
        try:
            db_type = self._detect_database_type(db_manager)

            if db_type == "mongodb":
                # Use MongoDB-specific method
                memories = db_manager.get_unprocessed_conscious_memories(
                    user_id=user_id
                )
                return memories
            else:
                # Use SQL method
                from sqlalchemy import text

                with db_manager._get_connection() as connection:
                    cursor = connection.execute(
                        text(
                            """SELECT memory_id, processed_data, summary, searchable_content,
                                  importance_score, created_at
                           FROM long_term_memory
                           WHERE user_id = :user_id AND classification = 'conscious-info'
                           AND conscious_processed = :conscious_processed
                           ORDER BY importance_score DESC, created_at DESC"""
                        ),
                        {"user_id": user_id, "conscious_processed": False},
                    )
                    return cursor.fetchall()

        except Exception as e:
            logger.error(f"ConsciouscAgent: Failed to get unprocessed memories: {e}")
            return []

    async def _copy_memory_to_short_term(
        self, db_manager, user_id: str, memory_data
    ) -> bool:
        """Copy a conscious memory directly to short-term memory with duplicate filtering (database-agnostic)"""
        try:
            db_type = self._detect_database_type(db_manager)

            if db_type == "mongodb":
                return await self._copy_memory_to_short_term_mongodb(
                    db_manager, user_id, memory_data
                )
            else:
                return await self._copy_memory_to_short_term_sql(
                    db_manager, user_id, memory_data
                )

        except Exception as e:
            memory_id = (
                memory_data.get("memory_id")
                if isinstance(memory_data, dict)
                else memory_data[0]
            )
            logger.error(
                f"ConsciouscAgent: Failed to copy memory {memory_id} to short-term: {e}"
            )
            return False

    async def _copy_memory_to_short_term_sql(
        self, db_manager, user_id: str, memory_row: tuple
    ) -> bool:
        """Copy a conscious memory to short-term memory (SQL version)"""
        try:
            (
                memory_id,
                processed_data,
                summary,
                searchable_content,
                importance_score,
                _,
            ) = memory_row

            from sqlalchemy import text

            with db_manager._get_connection() as connection:
                # Check if similar content already exists in short-term memory
                existing_check = connection.execute(
                    text(
                        """SELECT COUNT(*) FROM short_term_memory
                           WHERE user_id = :user_id
                           AND category_primary = 'conscious_context'
                           AND (searchable_content = :searchable_content
                                OR summary = :summary)"""
                    ),
                    {
                        "user_id": user_id,
                        "searchable_content": searchable_content,
                        "summary": summary,
                    },
                )

                existing_count = existing_check.scalar()
                if existing_count > 0:
                    logger.debug(
                        f"ConsciouscAgent: Skipping duplicate memory {memory_id} - similar content already exists in short-term memory"
                    )
                    return False

                # Create short-term memory ID
                short_term_id = (
                    f"conscious_{memory_id}_{int(datetime.now().timestamp())}"
                )

                # Use database utilities for type detection and JSON handling
                from memori.utils.database import (
                    detect_database_type,
                    get_insert_statement,
                    serialize_json_for_db,
                )

                db_type = detect_database_type(connection)
                processed_data_json = serialize_json_for_db(processed_data, db_type)

                # Build database-agnostic INSERT statement with proper JSON casting
                columns = [
                    "memory_id",
                    "processed_data",
                    "importance_score",
                    "category_primary",
                    "retention_type",
                    "user_id",
                    "session_id",
                    "created_at",
                    "expires_at",
                    "searchable_content",
                    "summary",
                    "is_permanent_context",
                ]

                insert_stmt = get_insert_statement(
                    "short_term_memory",
                    columns,
                    db_type,
                    json_columns=["processed_data"],
                )

                # Execute INSERT with proper parameters
                connection.execute(
                    text(insert_stmt),
                    {
                        "memory_id": short_term_id,
                        "processed_data": processed_data_json,
                        "importance_score": importance_score,
                        "category_primary": "conscious_context",
                        "retention_type": "permanent",
                        "user_id": user_id,
                        "session_id": "default",
                        "created_at": datetime.now().isoformat(),
                        "expires_at": None,
                        "searchable_content": searchable_content,
                        "summary": summary,
                        "is_permanent_context": True,
                    },
                )
                connection.commit()

            logger.debug(
                f"ConsciouscAgent: Copied memory {memory_id} to short-term as {short_term_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"ConsciouscAgent: Failed to copy SQL memory {memory_row[0]} to short-term: {e}"
            )
            return False

    async def _copy_memory_to_short_term_mongodb(
        self, db_manager, user_id: str, memory_data: dict
    ) -> bool:
        """Copy a conscious memory to short-term memory (MongoDB version)"""
        try:
            memory_id = memory_data.get("memory_id")
            processed_data = memory_data.get("processed_data", "{}")
            summary = memory_data.get("summary", "")
            searchable_content = memory_data.get("searchable_content", "")
            importance_score = memory_data.get("importance_score", 0.5)

            logger.debug(
                f"ConsciouscAgent: Processing MongoDB memory {memory_id} for short-term promotion"
            )
            logger.debug(f"  Content: {searchable_content[:100]}...")
            logger.debug(f"  Summary: {summary[:100]}...")

            # Check if similar content already exists in short-term memory
            existing_memories = db_manager.search_short_term_memory(
                query=searchable_content or summary, user_id=user_id, limit=1
            )

            # Check for exact duplicates
            for existing in existing_memories:
                if (
                    existing.get("searchable_content") == searchable_content
                    or existing.get("summary") == summary
                ):
                    logger.debug(
                        f"ConsciouscAgent: Skipping duplicate memory {memory_id} - similar content already exists in short-term memory"
                    )
                    return False

            # Create short-term memory ID
            short_term_id = f"conscious_{memory_id}_{int(datetime.now().timestamp())}"

            # Store in short-term memory using MongoDB-specific method
            db_manager.store_short_term_memory(
                memory_id=short_term_id,
                processed_data=(
                    processed_data
                    if isinstance(processed_data, str)
                    else json.dumps(processed_data)
                ),
                importance_score=importance_score,
                category_primary="conscious_context",
                retention_type="permanent",
                user_id=user_id,
                expires_at=None,  # No expiration (permanent)
                searchable_content=searchable_content,
                summary=summary,
                is_permanent_context=True,
            )

            # Verify the memory was actually stored by directly finding it by memory_id
            # Use direct lookup instead of text search since memory_id is not in text search index
            verification_result = db_manager.find_short_term_memory_by_id(
                memory_id=short_term_id, user_id=user_id
            )

            if not verification_result:
                logger.error(
                    f"ConsciouscAgent: VERIFICATION FAILED - Memory {short_term_id} not found in short-term memory after storage"
                )
                return False

            logger.info(
                f"ConsciouscAgent: Successfully copied memory {memory_id} to short-term as {short_term_id} (MongoDB) ✓ VERIFIED"
            )
            return True

        except Exception as e:
            logger.error(
                f"ConsciouscAgent: Failed to copy MongoDB memory {memory_data.get('memory_id')} to short-term: {e}"
            )
            import traceback

            logger.error(
                f"ConsciouscAgent: Full error traceback: {traceback.format_exc()}"
            )
            return False

    async def _mark_memories_processed(
        self, db_manager, memory_ids: list[str], user_id: str
    ):
        """Mark memories as processed for conscious context (database-agnostic)"""
        try:
            if not memory_ids:
                return

            db_type = self._detect_database_type(db_manager)

            if db_type == "mongodb":
                # Use MongoDB-specific method
                db_manager.mark_conscious_memories_processed(memory_ids, user_id)
            else:
                # Use SQL method
                from sqlalchemy import text

                with db_manager._get_connection() as connection:
                    for memory_id in memory_ids:
                        connection.execute(
                            text(
                                """UPDATE long_term_memory
                               SET conscious_processed = :conscious_processed
                               WHERE memory_id = :memory_id AND user_id = :user_id"""
                            ),
                            {
                                "memory_id": memory_id,
                                "user_id": user_id,
                                "conscious_processed": True,
                            },
                        )
                    connection.commit()

        except Exception as e:
            logger.error(f"ConsciouscAgent: Failed to mark memories processed: {e}")
