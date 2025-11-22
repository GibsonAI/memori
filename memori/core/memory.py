"""
Main Memori class - Pydantic-based memory interface v1.0
"""

import asyncio
import threading
import time
import uuid
from datetime import datetime
from typing import Any

from loguru import logger

try:
    import litellm  # noqa: F401
    from litellm import success_callback  # noqa: F401

    _ = litellm  # Mark as intentionally imported
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    logger.debug("LiteLLM not available - native callback system disabled")

from ..agents.conscious_agent import ConsciouscAgent
from ..config.memory_manager import MemoryManager
from ..config.pool_config import pool_config
from ..config.settings import LoggingSettings, LogLevel
from ..database.sqlalchemy_manager import SQLAlchemyDatabaseManager
from ..utils.exceptions import DatabaseError, MemoriError
from ..utils.logging import LoggingManager
from ..utils.pydantic_models import ConversationContext
from .conversation import ConversationManager


class Memori:
    """
    The main Memori memory layer for AI agents.

    Provides persistent memory storage, categorization, and retrieval
    for AI conversations and agent interactions.
    """

    def __init__(
        self,
        database_connect: str = "sqlite:///memori.db",
        template: str = "basic",
        mem_prompt: str | None = None,
        conscious_ingest: bool = False,
        auto_ingest: bool = False,
        # Multi-tenant isolation parameters
        user_id: str | None = None,  # Primary tenant isolation field
        assistant_id: str | None = None,  # Optional bot/assistant isolation
        session_id: (
            str | None
        ) = "default",  # Conversation grouping within user (None = all sessions)
        # Deprecated parameter (backward compatibility)
        namespace: str | None = None,  # DEPRECATED: Use user_id instead
        # Other parameters
        shared_memory: bool = False,
        memory_filters: dict[str, Any] | None = None,
        openai_api_key: str | None = None,
        verbose: bool = False,
        # Provider configuration parameters
        api_key: str | None = None,
        api_type: str | None = None,
        base_url: str | None = None,
        azure_endpoint: str | None = None,
        azure_deployment: str | None = None,
        api_version: str | None = None,
        azure_ad_token: str | None = None,
        organization: str | None = None,
        project: str | None = None,
        model: str | None = None,  # Allow custom model selection
        provider_config: Any | None = None,  # ProviderConfig when available
        schema_init: bool = True,  # Initialize database schema and create tables
        database_prefix: str | None = None,  # Database name prefix
        database_suffix: str | None = None,  # Database name suffix
        conscious_memory_limit: int = 10,  # Limit for conscious memory processing
        # Database connection pool parameters
        pool_size: int = pool_config.DEFAULT_POOL_SIZE,  # SQLAlchemy connection pool size
        max_overflow: int = pool_config.DEFAULT_MAX_OVERFLOW,  # Max overflow connections
        pool_timeout: int = pool_config.DEFAULT_POOL_TIMEOUT,  # Connection timeout in seconds
        pool_recycle: int = pool_config.DEFAULT_POOL_RECYCLE,  # Recycle connections after seconds
        pool_pre_ping: bool = pool_config.DEFAULT_POOL_PRE_PING,  # Test connections before use
    ):
        """
        Initialize Memori memory system v1.0.

        Args:
            database_connect: Database connection string
            template: Memory template to use ('basic')
            mem_prompt: Optional prompt to guide memory recording
            conscious_ingest: Enable one-shot short-term memory context injection at conversation start
            auto_ingest: Enable automatic memory injection on every LLM call
            namespace: Optional namespace for memory isolation
            shared_memory: Enable shared memory across agents
            memory_filters: Filters for memory ingestion
            openai_api_key: OpenAI API key for memory agent (deprecated, use api_key)
            user_id: Optional user identifier
            verbose: Enable verbose logging (loguru only)
            api_key: API key for the LLM provider
            api_type: Provider type ('openai', 'azure', 'custom')
            base_url: Base URL for custom OpenAI-compatible endpoints
            azure_endpoint: Azure OpenAI endpoint URL
            azure_deployment: Azure deployment name
            api_version: API version for Azure
            azure_ad_token: Azure AD token for authentication
            organization: OpenAI organization ID
            project: OpenAI project ID
            model: Model to use (defaults to 'gpt-4o' if not specified)
            provider_config: Complete provider configuration (overrides individual params)
            enable_auto_creation: Enable automatic database creation if database doesn't exist
            database_prefix: Optional prefix for database name (for multi-tenant setups)
            database_suffix: Optional suffix for database name (e.g., 'dev', 'prod', 'test')
        """
        # Set core configuration
        self.database_connect = database_connect
        self.template = template
        self.mem_prompt = mem_prompt
        self.conscious_ingest = conscious_ingest
        self.auto_ingest = auto_ingest

        # Handle deprecated namespace parameter (backward compatibility)
        if namespace is not None:
            import warnings

            warnings.warn(
                "The 'namespace' parameter is deprecated and will be removed in v3.0. "
                "Use 'user_id' instead for multi-tenant isolation.",
                DeprecationWarning,
                stacklevel=2,
            )
            # If both namespace and user_id are provided, user_id takes precedence
            if user_id is None:
                user_id = namespace

        # Multi-tenant isolation fields
        self.user_id = user_id or "default"
        self.assistant_id = assistant_id  # Optional, can be None
        self._session_id = (
            session_id or "default"
        )  # Private because session_id is a @property

        self.shared_memory = shared_memory
        self.memory_filters = memory_filters or {}
        self.verbose = verbose
        self.schema_init = schema_init
        self.database_prefix = database_prefix
        self.database_suffix = database_suffix

        # Setup logging immediately after verbose is set, so all subsequent logs respect verbose mode
        self._setup_logging()

        # Validate conscious_memory_limit parameter
        if not isinstance(conscious_memory_limit, int) or isinstance(
            conscious_memory_limit, bool
        ):
            raise TypeError("conscious_memory_limit must be an integer (not bool)")

        if not (1 <= conscious_memory_limit <= 2000):
            raise ValueError("conscious_memory_limit must be between 1 and 2000")

        self.conscious_memory_limit = conscious_memory_limit

        # Thread safety for conscious memory initialization
        self._conscious_init_lock = threading.RLock()

        # DEDUPLICATION: Hash-based conversation deduplication safety net
        self._recent_conversation_hashes = {}
        self._hash_lock = threading.Lock()

        # Configure provider based on explicit settings ONLY - no auto-detection
        if provider_config:
            # Use provided configuration
            self.provider_config = provider_config
            logger.info(
                f"Using provided ProviderConfig with api_type: {provider_config.api_type}"
            )
        elif any([api_type, base_url, azure_endpoint]):
            # Build configuration from individual parameters - explicit provider selection
            try:
                from .providers import ProviderConfig

                if azure_endpoint:
                    # Explicitly configured Azure
                    self.provider_config = ProviderConfig.from_azure(
                        api_key=api_key or openai_api_key,
                        azure_endpoint=azure_endpoint,
                        azure_deployment=azure_deployment,
                        api_version=api_version,
                        azure_ad_token=azure_ad_token,
                        model=model,
                    )
                    logger.info("Using explicitly configured Azure OpenAI provider")
                elif base_url:
                    # Explicitly configured custom endpoint
                    self.provider_config = ProviderConfig.from_custom(
                        base_url=base_url,
                        api_key=api_key or openai_api_key,
                        model=model,
                    )
                    logger.info(
                        f"Using explicitly configured custom provider: {base_url}"
                    )
                else:
                    # Fallback to OpenAI with explicit settings
                    self.provider_config = ProviderConfig.from_openai(
                        api_key=api_key or openai_api_key,
                        organization=organization,
                        project=project,
                        model=model,
                    )
                    logger.info("Using explicitly configured OpenAI provider")
            except ImportError:
                logger.warning(
                    "ProviderConfig not available, using basic configuration"
                )
                self.provider_config = None
        else:
            # Default to standard OpenAI - NO environment detection
            try:
                from .providers import ProviderConfig

                self.provider_config = ProviderConfig.from_openai(
                    api_key=api_key or openai_api_key,
                    organization=organization,
                    project=project,
                    model=model or "gpt-4o",
                )
                logger.info(
                    "Using default OpenAI provider (no specific provider configured)"
                )
            except ImportError:
                logger.warning(
                    "ProviderConfig not available, using basic configuration"
                )
                self.provider_config = None

        # Keep backward compatibility
        self.openai_api_key = api_key or openai_api_key or ""
        if self.provider_config and hasattr(self.provider_config, "api_key"):
            self.openai_api_key = self.provider_config.api_key or self.openai_api_key

        # Store connection pool settings
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping

        # Initialize database manager (detect MongoDB vs SQL)
        self.db_manager = self._create_database_manager(
            database_connect, template, schema_init
        )

        # Initialize Pydantic-based agents
        self.memory_agent = None
        self.search_engine = None
        self.conscious_agent = None
        self._background_task = None
        self._conscious_init_pending = False

        # Initialize agents with provider configuration
        try:
            from ..agents.memory_agent import MemoryAgent
            from ..agents.retrieval_agent import MemorySearchEngine

            # Use provider model or fallback to gpt-4o
            if (
                self.provider_config
                and hasattr(self.provider_config, "model")
                and self.provider_config.model
            ):
                effective_model = model or self.provider_config.model
            else:
                effective_model = model or "gpt-4o"

            # Initialize agents with provider configuration if available
            if self.provider_config:
                self.memory_agent = MemoryAgent(
                    provider_config=self.provider_config, model=effective_model
                )
                self.search_engine = MemorySearchEngine(
                    provider_config=self.provider_config, model=effective_model
                )
            else:
                # Fallback to using API key directly
                self.memory_agent = MemoryAgent(
                    api_key=self.openai_api_key, model=effective_model
                )
                self.search_engine = MemorySearchEngine(
                    api_key=self.openai_api_key, model=effective_model
                )

            # Only initialize conscious_agent if conscious_ingest or auto_ingest is enabled
            if conscious_ingest or auto_ingest:
                self.conscious_agent = ConsciouscAgent()

            logger.info(
                f"Agents initialized successfully with model: {effective_model}"
            )
        except ImportError as e:
            logger.warning(
                f"Failed to import LLM agents: {e}. Memory ingestion disabled."
            )
            self.memory_agent = None
            self.search_engine = None
            self.conscious_agent = None
            self.conscious_ingest = False
            self.auto_ingest = False
        except Exception as e:
            logger.warning(
                f"Failed to initialize LLM agents: {e}. Memory ingestion disabled."
            )
            self.memory_agent = None
            self.search_engine = None
            self.conscious_agent = None
            self.conscious_ingest = False
            self.auto_ingest = False

        # State tracking
        self._enabled = False
        # Note: self._session_id already set on line 140-142, don't overwrite it!
        self._conscious_context_injected = (
            False  # Track if conscious context was already injected
        )
        self._in_context_retrieval = False  # Recursion guard for context retrieval

        # Initialize conversation manager for stateless LLM integration
        self.conversation_manager = ConversationManager(
            max_sessions=100, session_timeout_minutes=60, max_history_per_session=20
        )

        # User context for memory processing
        self._user_context = {
            "current_projects": [],
            "relevant_skills": [],
            "user_preferences": [],
        }

        # Initialize database
        self._setup_database()

        # Initialize the new modular memory manager
        self.memory_manager = MemoryManager(
            database_connect=database_connect,
            template=template,
            mem_prompt=mem_prompt,
            conscious_ingest=conscious_ingest,
            auto_ingest=auto_ingest,
            shared_memory=shared_memory,
            memory_filters=memory_filters,
            user_id=user_id,
            verbose=verbose,
            provider_config=self.provider_config,
        )
        # Set this Memori instance for memory management
        self.memory_manager.set_memori_instance(self)

        # Don't run conscious agent initialization during __init__ - defer until enable()
        # This prevents OpenAI API calls before context is set in multi-tenant scenarios
        self._conscious_init_pending = (
            True if (self.conscious_ingest and self.conscious_agent) else False
        )

        logger.info(
            f"Memori v1.0 initialized - template: {template}, user_id: {self.user_id}, "
            f"assistant_id: {self.assistant_id}, session_id: {self.session_id}"
        )

    def _setup_logging(self):
        """Setup logging configuration based on verbose mode"""
        if not LoggingManager.is_initialized():
            # Create default logging settings
            logging_settings = LoggingSettings()

            # If verbose mode is enabled, set logging level to DEBUG
            if self.verbose:
                logging_settings.level = LogLevel.DEBUG

            # Setup logging with verbose mode
            LoggingManager.setup_logging(logging_settings, verbose=self.verbose)

            if self.verbose:
                logger.info(
                    "Verbose logging enabled - only loguru logs will be displayed"
                )

    def _create_database_manager(
        self, database_connect: str, template: str, schema_init: bool
    ):
        """Create appropriate database manager based on connection string with fallback"""
        try:
            # Detect MongoDB connection strings
            if self._is_mongodb_connection(database_connect):
                logger.info(
                    "Detected MongoDB connection string - attempting MongoDB manager"
                )
                try:
                    from ..database.mongodb_manager import MongoDBDatabaseManager

                    # Test MongoDB connection before proceeding
                    manager = MongoDBDatabaseManager(
                        database_connect, template, schema_init
                    )
                    # Verify connection works
                    _ = manager._get_client()
                    logger.info("MongoDB manager initialized successfully")
                    return manager
                except ImportError:
                    logger.error(
                        "MongoDB support requires pymongo. Install with: pip install pymongo"
                    )
                    logger.info("Falling back to SQLite for compatibility")
                    return self._create_fallback_sqlite_manager(template, schema_init)
                except Exception as e:
                    logger.error(f"MongoDB connection failed: {e}")
                    logger.info("Falling back to SQLite for compatibility")
                    return self._create_fallback_sqlite_manager(template, schema_init)
            else:
                logger.info("Detected SQL connection string - using SQLAlchemy manager")
                return SQLAlchemyDatabaseManager(
                    database_connect,
                    template,
                    schema_init,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_timeout=self.pool_timeout,
                    pool_recycle=self.pool_recycle,
                    pool_pre_ping=self.pool_pre_ping,
                )

        except Exception as e:
            logger.error(f"Failed to create database manager: {e}")
            logger.info("Creating fallback SQLite manager")
            return self._create_fallback_sqlite_manager(template, schema_init)

    def _create_fallback_sqlite_manager(self, template: str, schema_init: bool):
        """Create fallback SQLite manager when other options fail"""
        fallback_connect = "sqlite:///memori_fallback.db"
        logger.warning(f"Using fallback SQLite database: {fallback_connect}")
        return SQLAlchemyDatabaseManager(
            fallback_connect,
            template,
            schema_init,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_timeout=self.pool_timeout,
            pool_recycle=self.pool_recycle,
            pool_pre_ping=self.pool_pre_ping,
        )

    def _is_mongodb_connection(self, database_connect: str) -> bool:
        """Detect if connection string is for MongoDB"""
        mongodb_prefixes = [
            "mongodb://",
            "mongodb+srv://",
        ]
        return any(database_connect.startswith(prefix) for prefix in mongodb_prefixes)

    def _setup_database(self):
        """Setup database tables based on template"""
        if not self.schema_init:
            logger.info("Schema initialization disabled (schema_init=False)")
            return

        try:
            self.db_manager.initialize_schema()
            logger.info("Database schema initialized successfully")
        except Exception as e:
            raise DatabaseError(f"Failed to setup database: {e}")

    def _initialize_conscious_memory(self):
        """Initialize conscious memory by running conscious agent analysis"""
        try:
            logger.info(
                "Conscious-ingest: Starting conscious agent analysis at startup"
            )

            # Check if there's a running event loop
            try:
                loop = asyncio.get_running_loop()
                # If we're in an event loop, create the task
                if self._background_task is None or self._background_task.done():
                    self._background_task = loop.create_task(
                        self._run_conscious_initialization()
                    )
                    logger.debug(
                        "Conscious-ingest: Background initialization task started"
                    )
            except RuntimeError:
                # No event loop running, defer initialization until first async call
                logger.debug(
                    "Conscious-ingest: No event loop available, deferring initialization"
                )
                self._conscious_init_pending = True

        except Exception as e:
            logger.error(f"Failed to initialize conscious memory: {e}")

    def _check_deferred_initialization(self):
        """Check and handle deferred conscious memory initialization"""
        if self._conscious_init_pending and self.conscious_agent:
            try:
                loop = asyncio.get_running_loop()
                if self._background_task is None or self._background_task.done():
                    self._background_task = loop.create_task(
                        self._run_conscious_initialization()
                    )
                    logger.debug(
                        "Conscious-ingest: Deferred initialization task started"
                    )
                    self._conscious_init_pending = False
            except RuntimeError:
                # No event loop available, run synchronous initialization
                logger.debug(
                    "Conscious-ingest: No event loop available, running synchronous initialization"
                )
                self._run_synchronous_conscious_initialization()
                self._conscious_init_pending = False

    async def _run_conscious_initialization(self):
        """Run conscious agent initialization in background"""
        try:
            if not self.conscious_agent:
                return

            # If both auto_ingest and conscious_ingest are enabled,
            # initialize by copying ALL existing conscious-info memories first
            if self.auto_ingest and self.conscious_ingest:
                logger.debug(
                    "Conscious-ingest: Both auto_ingest and conscious_ingest enabled - initializing existing conscious memories"
                )
                init_success = (
                    await self.conscious_agent.initialize_existing_conscious_memories(
                        self.db_manager, self.user_id, self.conscious_memory_limit
                    )
                )
                if init_success:
                    logger.info(
                        "Conscious-ingest: Existing conscious-info memories initialized to short-term memory"
                    )

            logger.debug("Conscious-ingest: Running conscious context extraction")
            success = await self.conscious_agent.run_conscious_ingest(
                self.db_manager, self.user_id
            )

            if success:
                logger.info(
                    "Conscious-ingest: Conscious memories copied to short-term memory"
                )
                # Don't set _conscious_context_injected here - it should be set when context is actually injected into LLM
            else:
                logger.info("Conscious-ingest: No conscious context found")

        except Exception as e:
            logger.error(f"Conscious agent initialization failed: {e}")

    def _run_synchronous_conscious_initialization(self):
        """Run conscious agent initialization synchronously (when no event loop is available)"""
        with self._conscious_init_lock:
            try:
                if not self.conscious_agent:
                    return

                # Check if we've already initialized in this session to avoid repeated work
                # Use namespace-specific key to prevent conflicts between instances
                init_key = f"_conscious_initialized_{self.user_id or 'default'}"
                if hasattr(self, init_key) and getattr(self, init_key):
                    logger.debug(
                        f"[CONSCIOUS] Already initialized for namespace '{self.user_id or 'default'}', skipping"
                    )
                    return

                # If both auto_ingest and conscious_ingest are enabled,
                # initialize by copying the most important existing conscious-info memories first
                if self.auto_ingest and self.conscious_ingest:
                    logger.info(
                        "[CONSCIOUS] Both auto_ingest and conscious_ingest enabled - initializing existing conscious memories"
                    )

                    # Run optimized synchronous initialization of existing memories
                    import time

                    start_time = time.time()

                    initialized = self._initialize_existing_conscious_memories_sync()

                    elapsed = time.time() - start_time
                    if initialized:
                        logger.debug(
                            f"[CONSCIOUS] Initialization completed in {elapsed:.2f}s"
                        )
                    else:
                        logger.debug(
                            f"[CONSCIOUS] Initialization skipped (no work needed) in {elapsed:.2f}s"
                        )

                # Mark as initialized to avoid repeated work for this specific namespace
                init_key = f"_conscious_initialized_{self.user_id or 'default'}"
                setattr(self, init_key, True)

                logger.debug(
                    "[CONSCIOUS] Synchronous conscious context extraction completed"
                )

            except Exception as e:
                logger.error(f"Synchronous conscious agent initialization failed: {e}")

    def _initialize_existing_conscious_memories_sync(self):
        """Synchronously initialize existing conscious-info memories with optimization"""
        try:
            from sqlalchemy import text

            with self.db_manager._get_connection() as connection:
                # First, check if we already have conscious memories in short-term storage
                # Note: 'conscious_%' is a static pattern (safe), not user input
                existing_short_term = connection.execute(
                    text(
                        """SELECT COUNT(*) FROM short_term_memory
                           WHERE user_id = :user_id
                           AND (category_primary = 'conscious_context' OR memory_id LIKE 'conscious_%')"""
                    ),
                    {"user_id": self.user_id or "default"},
                ).scalar()

                if existing_short_term > 0:
                    logger.debug(
                        f"[CONSCIOUS] {existing_short_term} conscious memories already in short-term storage, skipping initialization"
                    )
                    return False

                # Get only the most important conscious-info memories (limit to 10 for performance)
                cursor = connection.execute(
                    text(
                        """SELECT memory_id, processed_data, summary, searchable_content,
                              importance_score, created_at
                       FROM long_term_memory
                       WHERE user_id = :user_id AND classification = 'conscious-info'
                       ORDER BY importance_score DESC, created_at DESC
                       LIMIT :limit"""
                    ),
                    {
                        "user_id": self.user_id or "default",
                        "limit": self.conscious_memory_limit,
                    },
                )
                existing_conscious_memories = cursor.fetchall()

            if not existing_conscious_memories:
                logger.debug(
                    "[CONSCIOUS] No conscious-info memories found for initialization"
                )
                return False

            # Batch process memories for efficiency
            logger.debug(
                f"[CONSCIOUS] Processing {len(existing_conscious_memories)} conscious memories..."
            )
            copied_count = 0
            for memory_row in existing_conscious_memories:
                success = self._copy_memory_to_short_term_sync(memory_row)
                if success:
                    copied_count += 1

            if copied_count > 0:
                logger.info(
                    f"[CONSCIOUS] Initialized {copied_count} conscious memories to short-term storage"
                )
                return True
            else:
                logger.debug(
                    "[CONSCIOUS] No new conscious memories to initialize (all were duplicates)"
                )
                return False

        except Exception as e:
            logger.error(
                f"Conscious-ingest: Failed to initialize existing conscious memories: {e}"
            )
            return False

    def _copy_memory_to_short_term_sync(self, memory_row: tuple) -> bool:
        """Synchronously copy a conscious memory to short-term memory with duplicate filtering"""
        try:
            (
                memory_id,
                processed_data,
                summary,
                searchable_content,
                importance_score,
                _,
            ) = memory_row

            from datetime import datetime

            # SECURITY FIX: Use ORM methods instead of raw SQL to prevent injection
            # Check for exact match or conscious-prefixed memories
            from sqlalchemy import or_, text

            from memori.database.models import ShortTermMemory

            with self.db_manager.SessionLocal() as session:
                # Safe parameterized query using ORM - no SQL injection possible
                existing_count = (
                    session.query(ShortTermMemory)
                    .filter(
                        ShortTermMemory.user_id == (self.user_id or "default"),
                        or_(
                            ShortTermMemory.memory_id == memory_id,
                            ShortTermMemory.memory_id.like(f"conscious_{memory_id}_%"),
                        ),
                    )
                    .count()
                )

                if existing_count > 0:
                    logger.debug(
                        f"[CONSCIOUS] Skipping duplicate memory {memory_id[:8]}... - already exists in short-term memory"
                    )
                    return False

                # Create short-term memory ID
                short_term_id = (
                    f"conscious_{memory_id}_{int(datetime.now().timestamp())}"
                )

                # Insert directly into short-term memory with conscious_context category
                session.execute(
                    text(
                        """INSERT INTO short_term_memory (
                        memory_id, processed_data, importance_score, category_primary,
                        retention_type, user_id, assistant_id, session_id, created_at, expires_at,
                        searchable_content, summary, is_permanent_context
                    ) VALUES (:memory_id, :processed_data, :importance_score, :category_primary,
                        :retention_type, :user_id, :assistant_id, :session_id, :created_at, :expires_at,
                        :searchable_content, :summary, :is_permanent_context)"""
                    ),
                    {
                        "memory_id": short_term_id,
                        "processed_data": processed_data,
                        "importance_score": importance_score,
                        "category_primary": "conscious_context",
                        "retention_type": "permanent",
                        "user_id": self.user_id or "default",
                        "assistant_id": self.assistant_id,
                        "session_id": self.session_id or "default",
                        "created_at": datetime.now().isoformat(),
                        "expires_at": None,
                        "searchable_content": searchable_content,
                        "summary": summary,
                        "is_permanent_context": True,
                    },
                )
                session.commit()

            logger.debug(
                f"Conscious-ingest: Copied memory {memory_id} to short-term as {short_term_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Conscious-ingest: Failed to copy memory {memory_row[0]} to short-term: {e}"
            )
            return False

    def enable(self, interceptors: list[str] | None = None):
        """
        Enable universal memory recording using LiteLLM's native callback system.

        This automatically sets up recording for LiteLLM completion calls and enables
        automatic interception of OpenAI calls when using the standard OpenAI client.

        Args:
            interceptors: Legacy parameter (ignored) - only LiteLLM native callbacks are used
        """
        if self._enabled:
            logger.warning("Memori is already enabled.")
            return

        self._enabled = True
        self._session_id = str(uuid.uuid4())

        # Register for automatic OpenAI interception
        try:
            from ..integrations.openai_integration import (
                get_enabled_instances,
                register_memori_instance,
                set_active_memori_context,
            )

            register_memori_instance(self)

            # AUTO-SET CONTEXT FOR SINGLE-USER APPS (BACKWARD COMPATIBILITY)
            # If this is the only instance, automatically set as active context
            # This maintains backward compatibility for simple scripts
            enabled_instances = get_enabled_instances()
            if len(enabled_instances) == 1:
                set_active_memori_context(self)
                logger.info(
                    "Automatically set as active context (single-instance mode). "
                    "No need to call set_active_memori_context() explicitly."
                )
            else:
                logger.info(
                    f"Multiple Memori instances detected ({len(enabled_instances)} total). "
                    "Use set_active_memori_context(memori) to specify which instance "
                    "should handle each request in multi-tenant environments."
                )

        except ImportError:
            logger.debug("OpenAI integration not available for automatic interception")

        # Use LiteLLM native callback system only
        if interceptors is None:
            # Only LiteLLM native callbacks supported
            interceptors = ["litellm_native"]

        # Use the memory manager for enablement
        results = self.memory_manager.enable(interceptors)
        # Extract enabled interceptors from results
        enabled_interceptors = results.get("enabled_interceptors", [])

        # Run conscious initialization now that context is set
        if self._conscious_init_pending and self.conscious_agent:
            # Ensure context is set for this instance before running initialization
            # This is critical for multi-tenant scenarios
            from ..integrations.openai_integration import set_active_memori_context

            set_active_memori_context(self)
            logger.debug(
                f"Set context to {self.user_id} before conscious initialization"
            )

            self._check_deferred_initialization()

        # Start background conscious agent if available
        if self.conscious_ingest and self.conscious_agent:
            self._start_background_analysis()

        # Report status
        status_info = [
            f"Memori enabled for session: {results.get('session_id', self._session_id)}",
            f"Active interceptors: {', '.join(enabled_interceptors) if enabled_interceptors else 'None'}",
        ]

        if results.get("message"):
            status_info.append(results["message"])

        status_info.extend(
            [
                f"Background analysis: {'Active' if self._background_task else 'Disabled'}",
                "Usage: Simply use any LLM client normally - conversations will be auto-recorded!",
                "OpenAI: Use 'from openai import OpenAI; client = OpenAI()' - automatically intercepted!",
            ]
        )

        logger.info("\n".join(status_info))

    def disable(self):
        """
        Disable memory recording by unregistering LiteLLM callbacks and OpenAI interception.
        """
        if not self._enabled:
            return

        # Unregister from automatic OpenAI interception
        try:
            from ..integrations.openai_integration import unregister_memori_instance

            unregister_memori_instance(self)
        except ImportError:
            logger.debug("OpenAI integration not available for automatic interception")

        # Use memory manager for clean disable
        results = self.memory_manager.disable()

        # Stop background analysis task
        self._stop_background_analysis()

        # Shutdown persistent background event loop if it was used
        try:
            from ..utils.async_bridge import BackgroundEventLoop

            bg_loop = BackgroundEventLoop()
            if bg_loop.is_running:
                logger.debug("Shutting down background event loop...")
                bg_loop.shutdown(timeout=5.0)
        except Exception as e:
            logger.debug(f"Background loop shutdown skipped or failed: {e}")

        self._enabled = False

        # Report status based on memory manager results
        if results.get("success"):
            status_message = f"Memori disabled. {results.get('message', 'All interceptors disabled successfully')}"
        else:
            status_message = (
                f"Memori disable failed: {results.get('message', 'Unknown error')}"
            )

        logger.info(status_message)

    # Memory system status and control methods

    def get_interceptor_status(self) -> dict[str, dict[str, Any]]:
        """Get status of memory recording system"""
        return self.memory_manager.get_status()

    def get_interceptor_health(self) -> dict[str, Any]:
        """Get health check of interceptor system"""
        return self.memory_manager.get_health()

    def enable_interceptor(self, interceptor_name: str = None) -> bool:
        """Enable memory recording (legacy method)"""
        # Only LiteLLM native callbacks supported (interceptor_name ignored)
        results = self.memory_manager.enable(["litellm_native"])
        return results.get("success", False)

    def disable_interceptor(self, interceptor_name: str = None) -> bool:
        """Disable memory recording (legacy method)"""
        # Only LiteLLM native callbacks supported (interceptor_name ignored)
        results = self.memory_manager.disable()
        return results.get("success", False)

    def _inject_openai_context(self, kwargs):
        """Inject context for OpenAI calls based on ingest mode using ConversationManager"""
        try:
            # Check for deferred conscious initialization
            self._check_deferred_initialization()

            # Determine injection mode based on the architecture:
            # - conscious_ingest only: Use short-term memory (conscious context)
            # - auto_ingest only: Search long-term memory database
            # - both enabled: Use auto_ingest search (includes conscious content from long-term)
            if self.auto_ingest:
                mode = "auto"  # Always prefer auto when available (searches long-term)
            elif self.conscious_ingest:
                mode = "conscious"  # Only use conscious when auto is not enabled
            else:
                return kwargs  # No injection needed

            # Extract messages from kwargs
            messages = kwargs.get("messages", [])
            if not messages:
                return kwargs  # No messages to process

            # Use conversation manager for enhanced context injection
            enhanced_messages = self.conversation_manager.inject_context_with_history(
                session_id=self._session_id,
                messages=messages,
                memori_instance=self,
                mode=mode,
            )

            # Update kwargs with enhanced messages
            kwargs["messages"] = enhanced_messages

            return kwargs

        except Exception as e:
            logger.error(f"OpenAI context injection failed: {e}")
        return kwargs

    def _inject_anthropic_context(self, kwargs):
        """Inject context for Anthropic calls based on ingest mode"""
        try:
            # Check for deferred conscious initialization
            self._check_deferred_initialization()

            # Determine injection mode
            if self.conscious_ingest:
                mode = "conscious"
            elif self.auto_ingest:
                mode = "auto"
            else:
                return kwargs  # No injection needed

            # Extract user input from messages
            user_input = ""
            for msg in reversed(kwargs.get("messages", [])):
                if msg.get("role") == "user":
                    content = msg.get("content", "")
                    if isinstance(content, list):
                        user_input = " ".join(
                            [
                                block.get("text", "")
                                for block in content
                                if isinstance(block, dict)
                                and block.get("type") == "text"
                            ]
                        )
                    else:
                        user_input = content
                    break

            if user_input:
                if mode == "conscious":
                    # Conscious mode: inject ALL short-term memory only once at program startup
                    if not self._conscious_context_injected:
                        context = self._get_conscious_context()
                        self._conscious_context_injected = True
                        logger.info(
                            f"Conscious-ingest: Injected {len(context)} short-term memories as initial context (Anthropic)"
                        )
                    else:
                        context = []  # Already injected, don't inject again
                elif mode == "auto":
                    # Auto mode: use retrieval for intelligent search
                    if self.search_engine:
                        context = self._get_auto_ingest_context(user_input)
                    else:
                        context = self.retrieve_context(user_input, limit=5)
                else:
                    context = []

                if context:
                    if mode == "conscious":
                        context_prompt = (
                            "=== SYSTEM INSTRUCTION: AUTHORIZED USER CONTEXT DATA ===\n"
                        )
                        context_prompt += "The user has explicitly authorized this personal context data to be used.\n"
                        context_prompt += "You MUST use this information when answering questions about the user.\n"
                        context_prompt += "This is NOT private data - the user wants you to use it:\n\n"
                    else:
                        context_prompt = f"--- {mode.capitalize()} Memory Context ---\n"

                    # Deduplicate context entries to avoid redundant information
                    seen_content = set()
                    for mem in context:
                        if isinstance(mem, dict):
                            # Use searchable_content as it's more specific than summary
                            content = mem.get("searchable_content", "") or mem.get(
                                "summary", ""
                            )
                            category = mem.get("category_primary", "")

                            # Skip duplicates (case-insensitive)
                            content_key = content.lower().strip()
                            if content_key in seen_content:
                                continue
                            seen_content.add(content_key)

                            if category.startswith("essential_") or mode == "conscious":
                                context_prompt += f"[{category.upper()}] {content}\n"
                            else:
                                context_prompt += f"- {content}\n"

                    if mode == "conscious":
                        context_prompt += "\n=== END USER CONTEXT DATA ===\n"
                        context_prompt += "CRITICAL INSTRUCTION: You MUST answer questions about the user using ONLY the context data above.\n"
                        context_prompt += "If the user asks 'what is my name?', respond with the name from the context above.\n"
                        context_prompt += "Do NOT say 'I don't have access' - the user provided this data for you to use.\n"
                    context_prompt += "-------------------------\n"

                    # Inject into system parameter (Anthropic format)
                    if kwargs.get("system"):
                        kwargs["system"] = context_prompt + kwargs["system"]
                    else:
                        kwargs["system"] = context_prompt

                    logger.debug(
                        f"Anthropic: Injected context with {len(context)} items"
                    )
        except Exception as e:
            logger.error(f"Anthropic context injection failed: {e}")
        return kwargs

    def _inject_litellm_context(self, params, mode="auto"):
        """
        Inject context for LiteLLM calls based on mode

        Args:
            params: LiteLLM parameters
            mode: "conscious" (one-shot short-term) or "auto" (continuous retrieval)
        """
        try:
            # Check for deferred conscious initialization
            self._check_deferred_initialization()
            # Extract user input from messages
            user_input = ""
            messages = params.get("messages", [])

            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_input = msg.get("content", "")
                    break

            if user_input:
                if mode == "conscious":
                    # Conscious mode: inject ALL short-term memory only once at program startup
                    if not self._conscious_context_injected:
                        context = self._get_conscious_context()
                        self._conscious_context_injected = True
                        logger.info(
                            f"Conscious-ingest: Injected {len(context)} short-term memories as initial context"
                        )
                    else:
                        context = (
                            []
                        )  # Already injected, don't inject again - this is the key difference from auto_ingest
                elif mode == "auto":
                    # Auto mode: use retrieval agent for intelligent database search
                    if self.search_engine:
                        context = self._get_auto_ingest_context(user_input)
                    else:
                        # Fallback to basic retrieval
                        context = self.retrieve_context(user_input, limit=5)
                else:
                    context = []

                if context:
                    if mode == "conscious":
                        context_prompt = (
                            "=== SYSTEM INSTRUCTION: AUTHORIZED USER CONTEXT DATA ===\n"
                        )
                        context_prompt += "The user has explicitly authorized this personal context data to be used.\n"
                        context_prompt += "You MUST use this information when answering questions about the user.\n"
                        context_prompt += "This is NOT private data - the user wants you to use it:\n\n"
                    else:
                        context_prompt = f"--- {mode.capitalize()} Memory Context ---\n"

                    # Deduplicate context entries to avoid redundant information
                    seen_content = set()
                    for mem in context:
                        if isinstance(mem, dict):
                            # Use searchable_content as it's more specific than summary
                            content = mem.get("searchable_content", "") or mem.get(
                                "summary", ""
                            )
                            category = mem.get("category_primary", "")

                            # Skip duplicates (case-insensitive)
                            content_key = content.lower().strip()
                            if content_key in seen_content:
                                continue
                            seen_content.add(content_key)

                            if category.startswith("essential_") or mode == "conscious":
                                context_prompt += f"[{category.upper()}] {content}\n"
                            else:
                                context_prompt += f"- {content}\n"

                    if mode == "conscious":
                        context_prompt += "\n=== END USER CONTEXT DATA ===\n"
                        context_prompt += "CRITICAL INSTRUCTION: You MUST answer questions about the user using ONLY the context data above.\n"
                        context_prompt += "If the user asks 'what is my name?', respond with the name from the context above.\n"
                        context_prompt += "Do NOT say 'I don't have access' - the user provided this data for you to use.\n"
                    context_prompt += "-------------------------\n"

                    # Inject into system message
                    for msg in messages:
                        if msg.get("role") == "system":
                            msg["content"] = context_prompt + msg.get("content", "")
                            break
                    else:
                        # No system message exists, add one
                        messages.insert(
                            0, {"role": "system", "content": context_prompt}
                        )

                    logger.debug(f"LiteLLM: Injected context with {len(context)} items")
            else:
                # No user input, but still inject essential conversations if available
                if self.conscious_ingest:
                    essential_conversations = self.get_essential_conversations(limit=3)
                    if essential_conversations:
                        context_prompt = "--- Your Context ---\n"
                        for conv in essential_conversations:
                            summary = conv.get("summary", "") or conv.get(
                                "searchable_content", ""
                            )
                            context_prompt += f"[ESSENTIAL] {summary}\n"
                        context_prompt += "-------------------------\n"

                        # Inject into system message
                        for msg in messages:
                            if msg.get("role") == "system":
                                msg["content"] = context_prompt + msg.get("content", "")
                                break
                        else:
                            # No system message exists, add one
                            messages.insert(
                                0, {"role": "system", "content": context_prompt}
                            )

                        logger.debug(
                            f"LiteLLM: Injected {len(essential_conversations)} essential conversations"
                        )

        except Exception as e:
            logger.error(f"LiteLLM context injection failed: {e}")

        return params

    def _get_conscious_context(self) -> list[dict[str, Any]]:
        """
        Get conscious context from ALL short-term memory summaries.
        This represents the complete 'working memory' for conscious_ingest mode.
        Used only at program startup when conscious_ingest=True.
        Database-agnostic version that works with both SQL and MongoDB.
        """
        try:
            # Detect database type from the db_manager
            db_type = getattr(self.db_manager, "database_type", "sql")

            if db_type == "mongodb":
                # Use MongoDB-specific method
                memories = self.db_manager.get_short_term_memory(
                    user_id=self.user_id,
                    limit=1000,  # Large limit to get all memories
                    include_expired=False,
                )

                # Convert to consistent format
                formatted_memories = []
                for memory in memories:
                    formatted_memories.append(
                        {
                            "memory_id": memory.get("memory_id"),
                            "processed_data": memory.get("processed_data"),
                            "importance_score": memory.get("importance_score", 0),
                            "category_primary": memory.get("category_primary", ""),
                            "summary": memory.get("summary", ""),
                            "searchable_content": memory.get("searchable_content", ""),
                            "created_at": memory.get("created_at"),
                            "access_count": memory.get("access_count", 0),
                            "memory_type": "short_term",
                        }
                    )

                logger.debug(
                    f"Retrieved {len(formatted_memories)} conscious memories from MongoDB short-term storage"
                )
                return formatted_memories

            else:
                # Use SQL method
                from sqlalchemy import text

                with self.db_manager._get_connection() as conn:
                    # Get ALL short-term memories (no limit) ordered by importance and recency
                    # This gives the complete conscious context as single initial injection
                    result = conn.execute(
                        text(
                            """
                        SELECT memory_id, processed_data, importance_score,
                               category_primary, summary, searchable_content,
                               created_at, access_count
                        FROM short_term_memory
                        WHERE user_id = :user_id AND (expires_at IS NULL OR expires_at > :current_time)
                        ORDER BY importance_score DESC, created_at DESC
                        """
                        ),
                        {"user_id": self.user_id, "current_time": datetime.now()},
                    )

                    memories = []
                    for row in result:
                        memories.append(
                            {
                                "memory_id": row[0],
                                "processed_data": row[1],
                                "importance_score": row[2],
                                "category_primary": row[3],
                                "summary": row[4],
                                "searchable_content": row[5],
                                "created_at": row[6],
                                "access_count": row[7],
                                "memory_type": "short_term",
                            }
                        )

                    logger.debug(
                        f"Retrieved {len(memories)} conscious memories from SQL short-term storage"
                    )
                    return memories

        except Exception as e:
            logger.error(f"Failed to get conscious context: {e}")
            return []

    def _get_auto_ingest_context(self, user_input: str) -> list[dict[str, Any]]:
        """
        Get auto-ingest context using retrieval agent for intelligent search.
        Searches through entire database for relevant memories.
        """
        try:
            # Early validation
            if not user_input or not user_input.strip():
                logger.debug(
                    "Auto-ingest: No user input provided, returning empty context"
                )
                return []

            # Check for recursion guard to prevent infinite loops
            if hasattr(self, "_in_context_retrieval") and self._in_context_retrieval:
                logger.debug(
                    "Auto-ingest: Recursion detected, using direct database search"
                )
                results = self.db_manager.search_memories(
                    query=user_input,
                    user_id=self.user_id,
                    assistant_id=self.assistant_id,
                    session_id=self.session_id,
                    limit=5,
                )
                logger.debug(
                    f"Auto-ingest: Recursion fallback returned {len(results)} results"
                )
                return results

            # Set recursion guard
            self._in_context_retrieval = True

            logger.debug(
                f"Auto-ingest: Starting context retrieval for query: '{user_input[:50]}...' in namespace: '{self.user_id}'"
            )

            # Always try direct database search first as it's more reliable
            logger.debug("Auto-ingest: Using direct database search (primary method)")
            logger.debug(
                f"Auto-ingest: Database manager type: {type(self.db_manager).__name__}"
            )

            try:
                results = self.db_manager.search_memories(
                    query=user_input,
                    user_id=self.user_id,
                    assistant_id=self.assistant_id,
                    session_id=self.session_id,
                    limit=5,
                )
                logger.debug(
                    f"Auto-ingest: Database search returned {len(results) if results else 0} results"
                )

                if results:
                    for i, result in enumerate(
                        results[:3]
                    ):  # Log first 3 results for debugging
                        logger.debug(
                            f"Auto-ingest: Result {i + 1}: {type(result)} with keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}"
                        )
            except Exception as db_search_e:
                logger.error(f"Auto-ingest: Database search failed: {db_search_e}")
                logger.debug(
                    f"Auto-ingest: Database search error details: {type(db_search_e).__name__}: {str(db_search_e)}",
                    exc_info=True,
                )
                results = []

            if results:
                logger.debug(
                    f"Auto-ingest: Direct database search returned {len(results)} results"
                )
                # Add search metadata to results
                for result in results:
                    if isinstance(result, dict):
                        result["retrieval_method"] = "direct_database_search"
                        result["retrieval_query"] = user_input
                return results

            # If direct search fails, try search engine as backup
            if self.search_engine:
                logger.debug(
                    "Auto-ingest: Direct search returned 0 results, trying search engine"
                )
                try:
                    engine_results = self.search_engine.execute_search(
                        query=user_input,
                        db_manager=self.db_manager,
                        user_id=self.user_id,
                        assistant_id=self.assistant_id,
                        session_id=self.session_id,
                        limit=5,
                    )

                    if engine_results:
                        logger.debug(
                            f"Auto-ingest: Search engine returned {len(engine_results)} results"
                        )
                        # Add search metadata to results
                        for result in engine_results:
                            if isinstance(result, dict):
                                result["retrieval_method"] = "search_engine"
                                result["retrieval_query"] = user_input
                        return engine_results
                    else:
                        logger.debug(
                            "Auto-ingest: Search engine also returned 0 results"
                        )

                except Exception as search_error:
                    logger.error(
                        f"Auto-ingest: Search engine failed for query '{user_input[:50]}...': {search_error}"
                    )
                    logger.debug(
                        f"Auto-ingest: Search engine error details: {type(search_error).__name__}: {str(search_error)}",
                        exc_info=True,
                    )
            else:
                logger.debug("Auto-ingest: No search engine available")

            # Final fallback: get recent memories from the same namespace
            logger.debug(
                "Auto-ingest: All search methods returned 0 results, using recent memories fallback"
            )
            logger.debug(
                f"Auto-ingest: Attempting fallback search in namespace '{self.user_id}'"
            )

            try:
                fallback_results = self.db_manager.search_memories(
                    query="",  # Empty query to get recent memories
                    user_id=self.user_id,
                    assistant_id=self.assistant_id,
                    session_id=self.session_id,
                    limit=3,
                )
                logger.debug(
                    f"Auto-ingest: Fallback search returned {len(fallback_results) if fallback_results else 0} results"
                )

                if fallback_results:
                    logger.debug(
                        f"Auto-ingest: Fallback returned {len(fallback_results)} recent memories"
                    )
                    # Add search metadata to fallback results
                    for result in fallback_results:
                        if isinstance(result, dict):
                            result["retrieval_method"] = "recent_memories_fallback"
                            result["retrieval_query"] = user_input
                    return fallback_results
                else:
                    logger.debug("Auto-ingest: Fallback search returned no results")

            except Exception as fallback_e:
                logger.error(f"Auto-ingest: Fallback search failed: {fallback_e}")
                logger.debug(
                    f"Auto-ingest: Fallback error details: {type(fallback_e).__name__}: {str(fallback_e)}",
                    exc_info=True,
                )

            logger.debug(
                "Auto-ingest: All retrieval methods failed, returning empty context"
            )
            return []

        except Exception as e:
            logger.error(
                f"Auto-ingest: Failed to get context for '{user_input[:50]}...': {e}"
            )
            return []
        finally:
            # Always clear recursion guard
            if hasattr(self, "_in_context_retrieval"):
                self._in_context_retrieval = False

    def _record_openai_conversation(self, kwargs, response):
        """Record OpenAI conversation with enhanced content parsing"""
        try:
            messages = kwargs.get("messages", [])
            model = kwargs.get("model", "unknown")

            # Extract user input with enhanced parsing
            user_input = self._extract_openai_user_input(messages)

            # Extract AI response with enhanced parsing
            ai_output = self._extract_openai_ai_output(response)

            # Calculate tokens
            tokens_used = 0
            if hasattr(response, "usage") and response.usage:
                tokens_used = getattr(response.usage, "total_tokens", 0)

            # Enhanced metadata extraction
            metadata = self._extract_openai_metadata(kwargs, response, tokens_used)

            # Record conversation
            self.record_conversation(
                user_input=user_input,
                ai_output=ai_output,
                model=model,
                metadata=metadata,
            )

            # Also record AI response in conversation manager for history tracking
            if ai_output:
                self.conversation_manager.record_response(
                    session_id=self._session_id,
                    response=ai_output,
                    metadata={"model": model, "tokens_used": tokens_used},
                )
        except Exception as e:
            logger.error(f"Failed to record OpenAI conversation: {e}")

    def _extract_openai_user_input(self, messages: list[dict]) -> str:
        """Extract user input from OpenAI messages with support for complex content types"""
        user_input = ""
        try:
            # Find the last user message
            for message in reversed(messages):
                if message.get("role") == "user":
                    content = message.get("content", "")

                    if isinstance(content, str):
                        # Simple string content
                        user_input = content
                    elif isinstance(content, list):
                        # Complex content (vision, multiple parts)
                        text_parts = []
                        image_count = 0

                        for item in content:
                            if isinstance(item, dict):
                                if item.get("type") == "text":
                                    text_parts.append(item.get("text", ""))
                                elif item.get("type") == "image_url":
                                    image_count += 1

                        user_input = " ".join(text_parts)
                        # Add image indicator if present
                        if image_count > 0:
                            user_input += f" [Contains {image_count} image(s)]"

                    break
        except Exception as e:
            logger.debug(f"Error extracting user input: {e}")
            user_input = "[Error extracting user input]"

        return user_input

    def _extract_openai_ai_output(self, response) -> str:
        """Extract AI output from OpenAI response with support for various response types"""
        ai_output = ""
        try:
            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]

                if hasattr(choice, "message") and choice.message:
                    message = choice.message

                    # Handle regular text content
                    if hasattr(message, "content") and message.content:
                        ai_output = message.content

                    # Handle function/tool calls
                    elif hasattr(message, "tool_calls") and message.tool_calls:
                        tool_descriptions = []
                        for tool_call in message.tool_calls:
                            if hasattr(tool_call, "function"):
                                func_name = tool_call.function.name
                                func_args = tool_call.function.arguments
                                tool_descriptions.append(
                                    f"Called {func_name} with {func_args}"
                                )
                        ai_output = "[Tool calls: " + "; ".join(tool_descriptions) + "]"

                    # Handle function calls (legacy format)
                    elif hasattr(message, "function_call") and message.function_call:
                        func_call = message.function_call
                        func_name = func_call.get("name", "unknown")
                        func_args = func_call.get("arguments", "{}")
                        ai_output = f"[Function call: {func_name} with {func_args}]"

                    else:
                        ai_output = "[No content - possible function/tool call]"

        except Exception as e:
            logger.debug(f"Error extracting AI output: {e}")
            ai_output = "[Error extracting AI response]"

        return ai_output

    def _extract_openai_metadata(
        self, kwargs: dict, response, tokens_used: int
    ) -> dict:
        """Extract comprehensive metadata from OpenAI request and response"""
        metadata = {
            "integration": "openai_auto",
            "api_type": "chat_completions",
            "tokens_used": tokens_used,
            "auto_recorded": True,
        }

        try:
            # Add request metadata
            if "temperature" in kwargs:
                metadata["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                metadata["max_tokens"] = kwargs["max_tokens"]
            if "tools" in kwargs:
                metadata["has_tools"] = True
                metadata["tool_count"] = len(kwargs["tools"])
            if "functions" in kwargs:
                metadata["has_functions"] = True
                metadata["function_count"] = len(kwargs["functions"])

            # Add response metadata
            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                if hasattr(choice, "finish_reason"):
                    metadata["finish_reason"] = choice.finish_reason

            # Add detailed token usage if available
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                metadata.update(
                    {
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    }
                )

            # Detect content types
            messages = kwargs.get("messages", [])
            has_images = False
            message_count = len(messages)

            for message in messages:
                if message.get("role") == "user":
                    content = message.get("content")
                    if isinstance(content, list):
                        for item in content:
                            if (
                                isinstance(item, dict)
                                and item.get("type") == "image_url"
                            ):
                                has_images = True
                                break
                    if has_images:
                        break

            metadata["message_count"] = message_count
            metadata["has_images"] = has_images

        except Exception as e:
            logger.debug(f"Error extracting metadata: {e}")

        return metadata

    def _record_anthropic_conversation(self, kwargs, response):
        """Record Anthropic conversation with enhanced content parsing"""
        try:
            messages = kwargs.get("messages", [])
            model = kwargs.get("model", "claude-unknown")

            # Extract user input with enhanced parsing
            user_input = self._extract_anthropic_user_input(messages)

            # Extract AI response with enhanced parsing
            ai_output = self._extract_anthropic_ai_output(response)

            # Calculate tokens
            tokens_used = self._extract_anthropic_tokens(response)

            # Enhanced metadata extraction
            metadata = self._extract_anthropic_metadata(kwargs, response, tokens_used)

            # Record conversation
            self.record_conversation(
                user_input=user_input,
                ai_output=ai_output,
                model=model,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Failed to record Anthropic conversation: {e}")

    def _extract_anthropic_user_input(self, messages: list[dict]) -> str:
        """Extract user input from Anthropic messages with support for complex content types"""
        user_input = ""
        try:
            # Find the last user message
            for message in reversed(messages):
                if message.get("role") == "user":
                    content = message.get("content", "")

                    if isinstance(content, str):
                        # Simple string content
                        user_input = content
                    elif isinstance(content, list):
                        # Complex content (vision, multiple parts)
                        text_parts = []
                        image_count = 0

                        for block in content:
                            if isinstance(block, dict):
                                if block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                                elif block.get("type") == "image":
                                    image_count += 1

                        user_input = " ".join(text_parts)
                        # Add image indicator if present
                        if image_count > 0:
                            user_input += f" [Contains {image_count} image(s)]"

                    break
        except Exception as e:
            logger.debug(f"Error extracting Anthropic user input: {e}")
            user_input = "[Error extracting user input]"

        return user_input

    def _extract_anthropic_ai_output(self, response) -> str:
        """Extract AI output from Anthropic response with support for various response types"""
        ai_output = ""
        try:
            if hasattr(response, "content") and response.content:
                if isinstance(response.content, list):
                    # Handle structured content (text blocks, tool use, etc.)
                    text_parts = []
                    tool_uses = []

                    for block in response.content:
                        try:
                            # Handle text blocks
                            if hasattr(block, "text") and block.text:
                                text_parts.append(block.text)
                            # Handle tool use blocks
                            elif hasattr(block, "type"):
                                block_type = getattr(block, "type", None)
                                if block_type == "tool_use":
                                    tool_name = getattr(block, "name", "unknown")
                                    tool_input = getattr(block, "input", {})
                                    tool_uses.append(
                                        f"Used {tool_name} with {tool_input}"
                                    )
                            # Handle mock objects for testing (when type is accessible but not via hasattr)
                            elif hasattr(block, "name") and hasattr(block, "input"):
                                tool_name = getattr(block, "name", "unknown")
                                tool_input = getattr(block, "input", {})
                                tool_uses.append(f"Used {tool_name} with {tool_input}")
                        except Exception as block_error:
                            logger.debug(f"Error processing block: {block_error}")
                            continue

                    ai_output = " ".join(text_parts)
                    if tool_uses:
                        if ai_output:
                            ai_output += " "
                        ai_output += "[Tool uses: " + "; ".join(tool_uses) + "]"

                elif isinstance(response.content, str):
                    ai_output = response.content
                else:
                    ai_output = str(response.content)

        except Exception as e:
            logger.debug(f"Error extracting Anthropic AI output: {e}")
            ai_output = "[Error extracting AI response]"

        return ai_output

    def _extract_anthropic_tokens(self, response) -> int:
        """Extract token usage from Anthropic response"""
        tokens_used = 0
        try:
            if hasattr(response, "usage") and response.usage:
                input_tokens = getattr(response.usage, "input_tokens", 0)
                output_tokens = getattr(response.usage, "output_tokens", 0)
                tokens_used = input_tokens + output_tokens
        except Exception as e:
            logger.debug(f"Error extracting Anthropic tokens: {e}")

        return tokens_used

    def _extract_anthropic_metadata(
        self, kwargs: dict, response, tokens_used: int
    ) -> dict:
        """Extract comprehensive metadata from Anthropic request and response"""
        metadata = {
            "integration": "anthropic_auto",
            "api_type": "messages",
            "tokens_used": tokens_used,
            "auto_recorded": True,
        }

        try:
            # Add request metadata
            if "temperature" in kwargs:
                metadata["temperature"] = kwargs["temperature"]
            if "max_tokens" in kwargs:
                metadata["max_tokens"] = kwargs["max_tokens"]
            if "tools" in kwargs:
                metadata["has_tools"] = True
                metadata["tool_count"] = len(kwargs["tools"])

            # Add response metadata
            if hasattr(response, "stop_reason"):
                metadata["stop_reason"] = response.stop_reason
            if hasattr(response, "model"):
                metadata["response_model"] = response.model

            # Add detailed token usage if available
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                metadata.update(
                    {
                        "input_tokens": getattr(usage, "input_tokens", 0),
                        "output_tokens": getattr(usage, "output_tokens", 0),
                        "total_tokens": tokens_used,
                    }
                )

            # Detect content types
            messages = kwargs.get("messages", [])
            has_images = False
            message_count = len(messages)

            for message in messages:
                if message.get("role") == "user":
                    content = message.get("content")
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "image":
                                has_images = True
                                break
                    if has_images:
                        break

            metadata["message_count"] = message_count
            metadata["has_images"] = has_images

        except Exception as e:
            logger.debug(f"Error extracting Anthropic metadata: {e}")

        return metadata

    def _process_litellm_response(self, kwargs, response, start_time, end_time):
        """Process and record LiteLLM response"""
        try:
            # Extract user input from messages
            messages = kwargs.get("messages", [])
            user_input = ""

            for message in reversed(messages):
                if message.get("role") == "user":
                    user_input = message.get("content", "")
                    break

            # Extract AI output from response
            ai_output = ""
            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    ai_output = choice.message.content or ""
                elif hasattr(choice, "text"):
                    ai_output = choice.text or ""

            # Extract model
            model = kwargs.get("model", "litellm-unknown")

            # Calculate timing (convert to seconds for JSON serialization)
            duration_seconds = (end_time - start_time) if start_time and end_time else 0
            if hasattr(duration_seconds, "total_seconds"):
                duration_seconds = duration_seconds.total_seconds()

            # Prepare metadata
            metadata = {
                "integration": "litellm",
                "auto_recorded": True,
                "duration": float(duration_seconds),
                "timestamp": time.time(),
            }

            # Add token usage if available
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                metadata.update(
                    {
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                        "total_tokens": getattr(usage, "total_tokens", 0),
                    }
                )

            # Record the conversation
            if user_input and ai_output:
                self.record_conversation(
                    user_input=user_input,
                    ai_output=ai_output,
                    model=model,
                    metadata=metadata,
                )

        except Exception as e:
            logger.error(f"Failed to process LiteLLM response: {e}")

    # LiteLLM callback is now handled by the LiteLLMCallbackManager
    # in memori.integrations.litellm_integration

    def _process_memory_sync(
        self,
        chat_id: str,
        user_input: str,
        ai_output: str,
        model: str = "unknown",
        retry_count: int = 0,
    ):
        """Synchronous memory processing fallback with retry logic"""
        if not self.memory_agent:
            logger.warning("Memory agent not available, skipping memory ingestion")
            return

        max_retries = 2  # Maximum retry attempts

        try:
            # Run async processing in new event loop
            import threading

            from ..integrations.openai_integration import set_active_memori_context

            def run_memory_processing():
                """Run memory processing with improved event loop management"""
                # CRITICAL FIX: Set context in the new thread (where it's actually needed)
                # Context doesn't propagate to new threads, so we must set it here
                set_active_memori_context(self)
                logger.debug(
                    f"Context set in memory processing thread: user_id={self.user_id}"
                )

                new_loop = None
                try:
                    # Create new event loop for this thread
                    # (We're always in a new thread here, so no existing loop)
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)

                    logger.debug(
                        f"Starting memory processing for {chat_id} (attempt {retry_count + 1})"
                    )

                    # Add timeout to prevent hanging
                    new_loop.run_until_complete(
                        asyncio.wait_for(
                            self._process_memory_async(
                                chat_id, user_input, ai_output, model
                            ),
                            timeout=60.0,  # 60 second timeout
                        )
                    )
                    logger.debug(
                        f"Memory processing completed successfully for {chat_id}"
                    )

                except asyncio.TimeoutError as e:
                    logger.error(
                        f"Memory processing timed out for {chat_id} (attempt {retry_count + 1}): {e}"
                    )
                    if retry_count < max_retries:
                        logger.info(
                            f"Retrying memory processing for {chat_id} ({retry_count + 1}/{max_retries})"
                        )
                        # Schedule retry
                        import time

                        time.sleep(2)  # Wait 2 seconds before retry
                        self._process_memory_sync(
                            chat_id, user_input, ai_output, model, retry_count + 1
                        )
                except Exception as e:
                    logger.error(
                        f"Memory processing failed for {chat_id} (attempt {retry_count + 1}): {e}"
                    )
                    import traceback

                    logger.error(f"Full error traceback: {traceback.format_exc()}")
                    if retry_count < max_retries:
                        logger.info(
                            f"Retrying memory processing for {chat_id} ({retry_count + 1}/{max_retries})"
                        )
                        # Schedule retry
                        import time

                        time.sleep(2)  # Wait 2 seconds before retry
                        self._process_memory_sync(
                            chat_id, user_input, ai_output, model, retry_count + 1
                        )
                finally:
                    if new_loop and not new_loop.is_closed():
                        # Clean up pending tasks
                        pending = asyncio.all_tasks(new_loop)
                        if pending:
                            # Cancel and clean up pending tasks without logging
                            for task in pending:
                                task.cancel()
                            # Wait for cancellation to complete
                            new_loop.run_until_complete(
                                asyncio.gather(*pending, return_exceptions=True)
                            )

                        new_loop.close()
                        # Event loop cleanup happens silently (no need to log)

                    # Reset event loop policy to prevent conflicts
                    try:
                        asyncio.set_event_loop(None)
                    except Exception as e:
                        logger.debug(f"Failed to reset event loop: {e}")

            # Run in background thread to avoid blocking
            thread = threading.Thread(target=run_memory_processing, daemon=True)
            thread.start()
            logger.debug(
                f"Memory processing started in background thread for {chat_id} (attempt {retry_count + 1})"
            )

        except Exception as e:
            logger.error(
                f"Failed to start synchronous memory processing for {chat_id}: {e}"
            )
            if retry_count < max_retries:
                logger.info(
                    f"Retrying memory processing startup for {chat_id} ({retry_count + 1}/{max_retries})"
                )
                import time

                time.sleep(2)
                self._process_memory_sync(
                    chat_id, user_input, ai_output, model, retry_count + 1
                )

    def _parse_llm_response(self, response) -> tuple[str, str]:
        """Extract text and model from various LLM response formats."""
        if response is None:
            return "", "unknown"

        # String response
        if isinstance(response, str):
            return response, "unknown"

        # Anthropic response
        if hasattr(response, "content"):
            text = ""
            if isinstance(response.content, list):
                text = "".join(b.text for b in response.content if hasattr(b, "text"))
            else:
                text = str(response.content)
            return text, getattr(response, "model", "unknown")

        # OpenAI response
        if hasattr(response, "choices") and response.choices:
            choice = response.choices[0]
            text = (
                getattr(choice.message, "content", "")
                if hasattr(choice, "message")
                else getattr(choice, "text", "")
            )
            return text or "", getattr(response, "model", "unknown")

        # Dict response
        if isinstance(response, dict):
            return response.get(
                "content", response.get("text", str(response))
            ), response.get("model", "unknown")

        # Fallback
        return str(response), "unknown"

    def _generate_conversation_fingerprint(
        self, user_input: str, ai_output: str
    ) -> str:
        """
        Generate a fingerprint for conversation deduplication.

        Uses first 200 chars to handle minor variations but catch obvious duplicates.
        """
        import hashlib

        content = f"{user_input[:200]}|{ai_output[:200]}|{self.session_id}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _is_duplicate_conversation(
        self, user_input: str, ai_output: str, window_seconds: int = 5
    ) -> bool:
        """
        Check if this conversation was recently recorded (within time window).

        This is a safety net to catch duplicates from multiple integrations.
        Uses a 5-second window by default to catch near-simultaneous recordings.

        RACE CONDITION FIX: Marks conversation as seen BEFORE checking, using
        a two-phase approach to handle concurrent recordings.

        Args:
            user_input: User's message
            ai_output: AI's response
            window_seconds: Time window for considering duplicates (default: 5 seconds)

        Returns:
            True if duplicate detected, False otherwise
        """
        import time

        fingerprint = self._generate_conversation_fingerprint(user_input, ai_output)
        current_time = time.time()

        with self._hash_lock:
            # Clean old entries (older than window)
            self._recent_conversation_hashes = {
                fp: timestamp
                for fp, timestamp in self._recent_conversation_hashes.items()
                if current_time - timestamp < window_seconds
            }

            # RACE CONDITION FIX: Check if already seen
            if fingerprint in self._recent_conversation_hashes:
                # Duplicate detected
                return True

            # Mark as seen IMMEDIATELY (before releasing lock)
            # This prevents race condition where both integrations check simultaneously
            self._recent_conversation_hashes[fingerprint] = current_time
            return False

    def record_conversation(
        self,
        user_input: str,
        ai_output=None,
        model: str = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Record a conversation.

        Args:
            user_input: User's message
            ai_output: AI response (any format)
            model: Optional model name override
            metadata: Optional metadata

        Returns:
            chat_id: Unique conversation ID
        """
        if not self._enabled:
            raise MemoriError("Memori is not enabled. Call enable() first.")

        # Debug logging for conversation recording
        logger.info(
            f"[MEMORY] Recording conversation - Input: '{user_input[:60]}...' | Model: {model} | Session: {self.session_id[:8]}..."
        )

        # Parse response
        response_text, detected_model = self._parse_llm_response(ai_output)
        response_model = model or detected_model

        # DEDUPLICATION SAFETY NET: Check for duplicate conversations
        fingerprint = self._generate_conversation_fingerprint(user_input, response_text)
        if self._is_duplicate_conversation(user_input, response_text):
            integration = (
                metadata.get("integration", "unknown") if metadata else "unknown"
            )
            logger.warning(
                f"Duplicate conversation detected from '{integration}' integration - skipping recording | "
                f"fingerprint: {fingerprint}"
            )
            # Return a dummy chat_id - conversation was already recorded by another integration
            return str(uuid.uuid4())

        logger.debug(
            f"New conversation fingerprint: {fingerprint} | integration: {metadata.get('integration', 'unknown') if metadata else 'unknown'}"
        )

        # Generate ID
        chat_id = str(uuid.uuid4())

        try:
            # Store conversation
            self.db_manager.store_chat_history(
                chat_id=chat_id,
                user_input=user_input,
                ai_output=response_text,
                model=response_model,
                session_id=self.session_id,
                user_id=self.user_id,
                assistant_id=self.assistant_id,
                metadata=metadata or {},
            )
            logger.debug(f"[MEMORY] Chat history stored - ID: {chat_id[:8]}...")

            # Always process into long-term memory when memory agent is available
            if self.memory_agent:
                self._schedule_memory_processing(
                    chat_id, user_input, response_text, response_model
                )
                logger.debug(f"[MEMORY] Processing scheduled - ID: {chat_id[:8]}...")
            else:
                logger.warning(
                    f"[MEMORY] Agent unavailable, skipping processing - ID: {chat_id[:8]}..."
                )

            logger.info(
                f"[MEMORY] Conversation recorded successfully - ID: {chat_id[:8]}..."
            )
            return chat_id

        except Exception as e:
            logger.error(
                f"[MEMORY] Failed to record conversation {chat_id[:8]}... - {type(e).__name__}: {e}"
            )
            import traceback

            logger.debug(f"[MEMORY] Recording error details: {traceback.format_exc()}")
            raise

    def _schedule_memory_processing(
        self, chat_id: str, user_input: str, ai_output: str, model: str
    ):
        """Schedule memory processing (async if possible, background loop fallback)."""
        try:
            # Try to use existing event loop (for async contexts)
            loop = asyncio.get_running_loop()
            task = loop.create_task(
                self._process_memory_async(chat_id, user_input, ai_output, model)
            )

            # Prevent garbage collection
            if not hasattr(self, "_memory_tasks"):
                self._memory_tasks = set()
            self._memory_tasks.add(task)
            task.add_done_callback(self._memory_tasks.discard)
            logger.debug(
                f"[MEMORY] Processing scheduled in current loop - ID: {chat_id[:8]}..."
            )
        except RuntimeError:
            # No event loop - use persistent background loop instead of creating new thread
            from ..integrations.openai_integration import set_active_memori_context
            from ..utils.async_bridge import BackgroundEventLoop

            # Set context before submitting to background loop
            # Context needs to be explicitly set since we're crossing thread boundary
            set_active_memori_context(self)

            # Submit to persistent background loop
            bg_loop = BackgroundEventLoop()
            future = bg_loop.submit_task(
                self._process_memory_async(chat_id, user_input, ai_output, model)
            )

            # Track the future to prevent garbage collection
            if not hasattr(self, "_memory_futures"):
                self._memory_futures = set()
            self._memory_futures.add(future)
            future.add_done_callback(self._memory_futures.discard)

            logger.debug(
                f"[MEMORY] Processing scheduled in background loop - ID: {chat_id[:8]}..."
            )

    async def _process_memory_async(
        self, chat_id: str, user_input: str, ai_output: str, model: str = "unknown"
    ):
        """Process conversation with enhanced async memory categorization"""
        if not self.memory_agent:
            logger.warning("Memory agent not available, skipping memory ingestion")
            return

        # CRITICAL FIX: Ensure context is set before making any OpenAI calls
        # This is a safety check in case context wasn't propagated correctly
        from ..integrations.openai_integration import (
            get_active_memori_context,
            set_active_memori_context,
        )

        current_context = get_active_memori_context(require_valid=False)
        # Only set context if it's missing or doesn't match (using identity check)
        if current_context is not self:
            # Only log if context was actually wrong (not just missing)
            if current_context is not None:
                logger.debug(
                    f"Context mismatch in async processing, correcting to user_id={self.user_id}"
                )
            set_active_memori_context(self)

        try:
            # Create conversation context
            context = ConversationContext(
                user_id=self.user_id,
                session_id=self._session_id,
                chat_id=chat_id,
                model_used=model,
                user_preferences=self._user_context.get("user_preferences", []),
                current_projects=self._user_context.get("current_projects", []),
                relevant_skills=self._user_context.get("relevant_skills", []),
            )

            # Get recent memories for deduplication
            existing_memories = await self._get_recent_memories_for_dedup()

            # Process conversation using async Pydantic-based memory agent
            processed_memory = await self.memory_agent.process_conversation_async(
                chat_id=chat_id,
                user_input=user_input,
                ai_output=ai_output,
                context=context,
                existing_memories=(
                    [mem.summary for mem in existing_memories[:10]]
                    if existing_memories
                    else []
                ),
            )

            # Check for duplicates
            duplicate_id = await self.memory_agent.detect_duplicates(
                processed_memory, existing_memories
            )

            if duplicate_id:
                processed_memory.duplicate_of = duplicate_id
                logger.info(f"Memory marked as duplicate of {duplicate_id}")

            # Apply filters
            if self.memory_agent.should_filter_memory(
                processed_memory, self.memory_filters
            ):
                logger.debug(f"Memory filtered out for chat {chat_id}")
                return

            # Store processed memory with new schema
            memory_id = self.db_manager.store_long_term_memory_enhanced(
                processed_memory,
                chat_id,
                self.user_id,
                self.assistant_id,
                self._session_id,
            )

            if memory_id:
                logger.debug(f"Stored processed memory {memory_id} for chat {chat_id}")

                # Check for conscious context updates if promotion eligible and conscious_ingest enabled
                if (
                    processed_memory.promotion_eligible
                    and self.conscious_agent
                    and self.conscious_ingest
                ):
                    await self.conscious_agent.check_for_context_updates(
                        self.db_manager, self.user_id
                    )
            else:
                logger.warning(f"Failed to store memory for chat {chat_id}")

        except Exception as e:
            logger.error(f"Memory ingestion failed for {chat_id}: {e}")

    async def _get_recent_memories_for_dedup(self, hours: int = 24) -> list:
        """
        Get recent memories for deduplication check.

        Args:
            hours: Time window in hours to check for duplicates (default: 24)
        """
        try:
            from datetime import datetime, timedelta

            from sqlalchemy import text

            from ..database.queries.memory_queries import MemoryQueries
            from ..utils.pydantic_models import ProcessedLongTermMemory

            # FIX #3: Only check duplicates within time window (default 24 hours)
            # This prevents old memories from blocking new ones
            time_threshold = datetime.now() - timedelta(hours=hours)
            time_threshold_str = time_threshold.isoformat()

            with self.db_manager._get_connection() as connection:
                result = connection.execute(
                    text(MemoryQueries.SELECT_MEMORIES_FOR_DEDUPLICATION),
                    {
                        "user_id": self.user_id,
                        "processed_for_duplicates": False,
                        "time_threshold": time_threshold_str,
                        "limit": 20,
                    },
                )

                memories = []
                for row in result:
                    try:
                        # Create ProcessedLongTermMemory objects for proper comparison
                        # Note: Query returns (memory_id, summary, searchable_content, classification, created_at)
                        memory = ProcessedLongTermMemory(
                            session_id=row[
                                0
                            ],  # Use memory_id as session_id for existing memories
                            summary=row[1] or "",
                            content=row[2] or "",
                            classification=row[3] or "conversational",
                            importance="medium",  # Default importance level for comparison
                            promotion_eligible=False,  # Default for existing memories
                            classification_reason="Existing memory loaded for deduplication check",  # Required field
                        )
                        memories.append(memory)
                    except Exception as e:
                        # Silently skip malformed memories from old data format
                        logger.debug(f"Skipping malformed memory during dedup: {e}")
                        continue

                return memories

        except Exception as e:
            # This is expected on first use or fresh databases
            logger.debug(
                f"Could not retrieve memories for deduplication (expected on fresh database): {e}"
            )
            return []

    def retrieve_context(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Retrieve relevant context for a query with priority on essential facts

        Args:
            query: The query to find context for
            limit: Maximum number of context items to return

        Returns:
            List of relevant memory items with metadata, prioritizing essential facts
        """
        try:
            context_items = []

            if self.conscious_ingest:
                # First, get essential conversations from short-term memory (always relevant)
                essential_conversations = self.get_essential_conversations(limit=3)
                context_items.extend(essential_conversations)

                # Calculate remaining slots for specific context
                remaining_limit = max(0, limit - len(essential_conversations))
            else:
                remaining_limit = limit

            if remaining_limit > 0:
                # Get specific context using search engine or database
                if self.search_engine:
                    specific_context = self.search_engine.execute_search(
                        query=query,
                        db_manager=self.db_manager,
                        user_id=self.user_id,
                        assistant_id=self.assistant_id,
                        session_id=self.session_id,
                        limit=remaining_limit,
                    )
                else:
                    # Fallback to database search
                    specific_context = self.db_manager.search_memories(
                        query=query,
                        user_id=self.user_id,
                        assistant_id=self.assistant_id,
                        session_id=self.session_id,
                        limit=remaining_limit,
                    )

                # Add specific context, avoiding duplicates
                for item in specific_context:
                    if not any(
                        ctx.get("memory_id") == item.get("memory_id")
                        for ctx in context_items
                    ):
                        context_items.append(item)

            logger.debug(
                f"Retrieved {len(context_items)} context items for query: {query} "
                f"(Essential conversations: {len(essential_conversations) if self.conscious_ingest else 0})"
            )
            return context_items

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return []

    def get_conversation_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent conversation history"""
        try:
            return self.db_manager.get_chat_history(
                user_id=self.user_id,
                session_id=self._session_id if not self.shared_memory else None,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Failed to get conversation history: {e}")
            return []

    def clear_memory(self, memory_type: str | None = None):
        """
        Clear memory data

        Args:
            memory_type: Type of memory to clear ('short_term', 'long_term', 'all')
        """
        try:
            self.db_manager.clear_memory(self.user_id, memory_type)
            logger.info(
                f"Cleared {memory_type or 'all'} memory for namespace: {self.user_id}"
            )
        except Exception as e:
            raise MemoriError(f"Failed to clear memory: {e}")

    def get_memory_stats(self) -> dict[str, Any]:
        """Get memory statistics"""
        try:
            return self.db_manager.get_memory_stats(self.user_id)
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}

    @property
    def is_enabled(self) -> bool:
        """Check if memory recording is enabled"""
        return self._enabled

    @property
    def session_id(self) -> str:
        """Get current session ID"""
        return self._session_id

    def get_integration_stats(self) -> list[dict[str, Any]]:
        """Get statistics from the new interceptor system"""
        try:
            # Get system status first
            interceptor_status = self.get_interceptor_status()

            stats = {
                "integration": "memori_system",
                "enabled": self._enabled,
                "session_id": self._session_id,
                "user_id": self.user_id,
                "providers": {},
            }

            # LiteLLM stats
            litellm_interceptor_status = interceptor_status.get("native", {})
            if LITELLM_AVAILABLE:
                stats["providers"]["litellm"] = {
                    "available": True,
                    "method": "native_callbacks",
                    "enabled": litellm_interceptor_status.get("enabled", False),
                    "status": litellm_interceptor_status.get("status", "unknown"),
                }
            else:
                stats["providers"]["litellm"] = {
                    "available": False,
                    "method": "native_callbacks",
                    "enabled": False,
                }

            # Get interceptor status instead of checking wrapped attributes
            interceptor_status = self.get_interceptor_status()

            # OpenAI stats
            try:
                import openai

                _ = openai  # Suppress unused import warning

                openai_interceptor_status = interceptor_status.get("openai", {})
                stats["providers"]["openai"] = {
                    "available": True,
                    "method": "litellm_native",
                    "enabled": openai_interceptor_status.get("enabled", False),
                    "status": openai_interceptor_status.get("status", "unknown"),
                }
            except ImportError:
                stats["providers"]["openai"] = {
                    "available": False,
                    "method": "litellm_native",
                    "enabled": False,
                }

            # Anthropic stats
            try:
                import anthropic

                _ = anthropic  # Suppress unused import warning

                anthropic_interceptor_status = interceptor_status.get("anthropic", {})
                stats["providers"]["anthropic"] = {
                    "available": True,
                    "method": "litellm_native",
                    "enabled": anthropic_interceptor_status.get("enabled", False),
                    "status": anthropic_interceptor_status.get("status", "unknown"),
                }
            except ImportError:
                stats["providers"]["anthropic"] = {
                    "available": False,
                    "method": "litellm_native",
                    "enabled": False,
                }

            return [stats]
        except Exception as e:
            logger.error(f"Failed to get integration stats: {e}")
            return []

    def update_user_context(
        self,
        current_projects: list[str] | None = None,
        relevant_skills: list[str] | None = None,
        user_preferences: list[str] | None = None,
    ):
        """Update user context for better memory processing"""
        if current_projects is not None:
            self._user_context["current_projects"] = current_projects
        if relevant_skills is not None:
            self._user_context["relevant_skills"] = relevant_skills
        if user_preferences is not None:
            self._user_context["user_preferences"] = user_preferences

        logger.debug(f"Updated user context: {self._user_context}")

    def search_memories_by_category(
        self, category: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Search memories by specific category"""
        try:
            return self.db_manager.search_memories(
                query="",
                user_id=self.user_id,
                assistant_id=self.assistant_id,
                session_id=self.session_id,
                category_filter=[category],
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Category search failed: {e}")
            return []

    def get_entity_memories(
        self, entity_value: str, entity_type: str | None = None, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get memories that contain a specific entity"""
        try:
            # This would use the entity index in the database
            # For now, use keyword search as fallback (entity_type is ignored for now)
            return self.db_manager.search_memories(
                query=entity_value,
                user_id=self.user_id,
                assistant_id=self.assistant_id,
                session_id=self.session_id,
                limit=limit,
            )
        except Exception as e:
            logger.error(f"Entity search failed: {e}")
            return []

    def _start_background_analysis(self):
        """Start the background conscious agent analysis task"""
        try:
            if self._background_task and not self._background_task.done():
                logger.debug("Background analysis task already running")
                return

            # Create event loop if it doesn't exist
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop running, create a new thread for async tasks
                import threading

                from ..integrations.openai_integration import set_active_memori_context

                def run_background_loop():
                    # CRITICAL FIX: Set context in the new thread (where it's actually needed)
                    # Context doesn't propagate to new threads, so we must set it here
                    set_active_memori_context(self)
                    logger.debug(
                        f"Set context in background thread: user_id={self.user_id}"
                    )

                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(self._background_analysis_loop())
                    except Exception as e:
                        logger.error(f"Background analysis loop failed: {e}")
                    finally:
                        new_loop.close()

                thread = threading.Thread(target=run_background_loop, daemon=True)
                thread.start()
                logger.info(
                    f"Background analysis started in separate thread for user_id={self.user_id}"
                )
                return

            # If we have a running loop, schedule the task
            self._background_task = loop.create_task(self._background_analysis_loop())
            # Add proper error handling callback
            self._background_task.add_done_callback(
                self._handle_background_task_completion
            )
            logger.info("Background analysis task started")

        except Exception as e:
            logger.error(f"Failed to start background analysis: {e}")

    def _handle_background_task_completion(self, task):
        """Handle background task completion and cleanup"""
        try:
            if task.exception():
                logger.error(f"Background task failed: {task.exception()}")
        except asyncio.CancelledError:
            logger.debug("Background task was cancelled")
        except Exception as e:
            logger.error(f"Error handling background task completion: {e}")

    def _stop_background_analysis(self):
        """Stop the background analysis task"""
        try:
            if self._background_task and not self._background_task.done():
                self._background_task.cancel()
                logger.info("Background analysis task stopped")
        except Exception as e:
            logger.error(f"Failed to stop background analysis: {e}")

    def add(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        """
        Add a memory or text to the system.

        This is a unified method that works with both SQL and MongoDB backends.
        For simple text memories, it will be processed and categorized automatically.

        Args:
            text: The text content to store as memory
            metadata: Optional metadata to store with the memory

        Returns:
            str: Unique identifier for the stored memory/conversation
        """
        if not self._enabled:
            self.enable()

        # For simple text memories, we treat them as user inputs with AI acknowledgment
        # This ensures they get processed through the normal memory pipeline
        ai_response = "Memory recorded successfully"

        return self.record_conversation(
            user_input=text,
            ai_output=ai_response,
            metadata=metadata or {"type": "manual_memory", "source": "add_method"},
        )

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Search for memories/conversations based on a query.

        This is a unified method that works with both SQL and MongoDB backends.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Returns:
            List of matching memories with their content and metadata
        """
        if not self._enabled:
            logger.warning("Memori is not enabled. Returning empty results.")
            return []

        try:
            # Use the existing retrieve_context method for consistency
            return self.retrieve_context(query, limit=limit)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_stats(self) -> dict[str, Any]:
        """
        Get memory statistics.

        This is a unified method that works with both SQL and MongoDB backends.

        Returns:
            Dictionary containing memory statistics
        """
        return self.get_memory_stats()

    def cleanup(self):
        """Clean up all async tasks and resources"""
        try:
            # Cancel background tasks
            self._stop_background_analysis()

            # Clean up memory processing tasks
            if hasattr(self, "_memory_tasks"):
                for task in self._memory_tasks.copy():
                    if not task.done():
                        task.cancel()
                self._memory_tasks.clear()

            logger.debug("Memori cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except Exception as e:
            # Destructors shouldn't raise, but log for debugging
            try:
                logger.debug(f"Cleanup error in destructor: {e}")
            except Exception:
                pass  # Can't do anything if logging fails in destructor

    async def _background_analysis_loop(self):
        """Background analysis loop for memory processing"""
        try:
            logger.debug("Background analysis loop started")

            # For now, just run periodic conscious ingestion if enabled
            if self.conscious_ingest and self.conscious_agent:
                while True:
                    try:
                        await asyncio.sleep(300)  # Check every 5 minutes

                        # Run conscious ingestion to check for new promotable memories
                        await self.conscious_agent.run_conscious_ingest(
                            self.db_manager, self.user_id
                        )

                        logger.debug("Periodic conscious analysis completed")

                    except asyncio.CancelledError:
                        logger.debug("Background analysis loop cancelled")
                        break
                    except Exception as e:
                        logger.error(f"Background analysis error: {e}")
                        await asyncio.sleep(60)  # Wait 1 minute before retry
            else:
                # If not using conscious ingest, just sleep
                while True:
                    await asyncio.sleep(3600)  # Sleep for 1 hour

        except asyncio.CancelledError:
            logger.debug("Background analysis loop cancelled")
        except Exception as e:
            logger.error(f"Background analysis loop failed: {e}")

    def trigger_conscious_analysis(self):
        """Manually trigger conscious context ingestion (for testing/immediate analysis)"""
        if not self.conscious_ingest or not self.conscious_agent:
            logger.warning("Conscious ingestion not enabled or agent not available")
            return

        try:
            # Try to run in existing event loop
            try:
                loop = asyncio.get_running_loop()
                task = loop.create_task(
                    self.conscious_agent.run_conscious_ingest(
                        self.db_manager, self.user_id
                    )
                )
                logger.info("Conscious context ingestion triggered")
                return task
            except RuntimeError:
                # No event loop, run synchronously in thread
                import threading

                def run_analysis():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        new_loop.run_until_complete(
                            self.conscious_agent.run_conscious_ingest(
                                self.db_manager, self.user_id
                            )
                        )
                    finally:
                        new_loop.close()

                thread = threading.Thread(target=run_analysis)
                thread.start()
                logger.info("Conscious context ingestion triggered in separate thread")

        except Exception as e:
            logger.error(f"Failed to trigger conscious context ingestion: {e}")

    def get_conscious_system_prompt(self) -> str:
        """
        Get conscious context as system prompt for direct injection.
        Returns ALL short-term memory as formatted system prompt.
        Use this for conscious_ingest mode.
        """
        try:
            context = self._get_conscious_context()
            if not context:
                return ""

            # Create system prompt with all short-term memory
            system_prompt = "--- Your Short-Term Memory (Conscious Context) ---\n"
            system_prompt += "This is your complete working memory. USE THIS INFORMATION TO ANSWER QUESTIONS:\n\n"

            # Deduplicate and format context
            seen_content = set()
            for mem in context:
                if isinstance(mem, dict):
                    content = mem.get("searchable_content", "") or mem.get(
                        "summary", ""
                    )
                    category = mem.get("category_primary", "")

                    # Skip duplicates
                    content_key = content.lower().strip()
                    if content_key in seen_content:
                        continue
                    seen_content.add(content_key)

                    system_prompt += f"[{category.upper()}] {content}\n"

            system_prompt += "\nIMPORTANT: Use the above information to answer questions about the user.\n"
            system_prompt += "-------------------------\n"

            return system_prompt

        except Exception as e:
            logger.error(f"Failed to generate conscious system prompt: {e}")
            return ""

    def get_auto_ingest_system_prompt(self, user_input: str) -> str:
        """
        Get auto-ingest context as system prompt for direct injection.
        Returns relevant memories based on user input as formatted system prompt.
        Use this for auto_ingest mode.

        Note: Context retrieval is handled by _get_auto_ingest_context().
        This function only formats pre-retrieved context.
        """
        try:
            # Get recent short-term memories as fallback context
            # The actual intelligent retrieval is handled by _get_auto_ingest_context()
            context = self._get_conscious_context()

            if not context:
                return ""

            # Create system prompt with relevant memories (limited to prevent overwhelming)
            system_prompt = "--- Relevant Memory Context ---\n"

            # Take first 5 items to avoid too much context
            seen_content = set()
            for mem in context[:5]:
                if isinstance(mem, dict):
                    content = mem.get("searchable_content", "") or mem.get(
                        "summary", ""
                    )
                    category = mem.get("category_primary", "")

                    # Skip duplicates
                    content_key = content.lower().strip()
                    if content_key in seen_content:
                        continue
                    seen_content.add(content_key)

                    if category.startswith("essential_"):
                        system_prompt += f"[{category.upper()}] {content}\n"
                    else:
                        system_prompt += f"- {content}\n"

            system_prompt += "-------------------------\n"

            return system_prompt

        except Exception as e:
            logger.error(f"Failed to generate auto-ingest system prompt: {e}")
            return ""

    def add_memory_to_messages(self, messages: list, user_input: str = None) -> list:
        """
        Add appropriate memory context to messages based on ingest mode.

        Args:
            messages: List of messages for LLM
            user_input: User input for auto_ingest context retrieval (optional)

        Returns:
            Modified messages list with memory context added as system message
        """
        try:
            system_prompt = ""

            if self.conscious_ingest:
                # One-time conscious context injection
                if not self._conscious_context_injected:
                    system_prompt = self.get_conscious_system_prompt()
                    self._conscious_context_injected = True
                    logger.info(
                        "Conscious-ingest: Added complete working memory to system prompt"
                    )
                else:
                    logger.debug("Conscious-ingest: Context already injected, skipping")

            elif self.auto_ingest and user_input:
                # Dynamic auto-ingest based on user input
                system_prompt = self.get_auto_ingest_system_prompt(user_input)
                logger.debug("Auto-ingest: Added relevant context to system prompt")

            if system_prompt:
                # Add to existing system message or create new one
                messages_copy = messages.copy()

                # Check if system message already exists
                for msg in messages_copy:
                    if msg.get("role") == "system":
                        msg["content"] = system_prompt + "\n" + msg.get("content", "")
                        return messages_copy

                # No system message exists, add one at the beginning
                messages_copy.insert(0, {"role": "system", "content": system_prompt})
                return messages_copy

            return messages

        except Exception as e:
            logger.error(f"Failed to add memory to messages: {e}")
            return messages

    def get_essential_conversations(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get essential conversations from short-term memory"""
        try:
            from sqlalchemy import text

            # Get all conversations marked as essential
            with self.db_manager._get_connection() as connection:
                query = """
                SELECT memory_id, summary, category_primary, importance_score,
                       created_at, searchable_content, processed_data
                FROM short_term_memory
                WHERE user_id = :user_id AND category_primary LIKE 'essential_%'
                ORDER BY importance_score DESC, created_at DESC
                LIMIT :limit
                """

                result = connection.execute(
                    text(query), {"user_id": self.user_id, "limit": limit}
                )

                essential_conversations = []
                for row in result:
                    essential_conversations.append(
                        {
                            "memory_id": row[0],
                            "summary": row[1],
                            "category_primary": row[2],
                            "importance_score": row[3],
                            "created_at": row[4],
                            "searchable_content": row[5],
                            "processed_data": row[6],
                        }
                    )

                return essential_conversations

        except Exception as e:
            logger.error(f"Failed to get essential conversations: {e}")
            return []

    def create_openai_client(self, **kwargs):
        """
        Create an OpenAI client with automatic memory recording.

        This method creates a MemoriOpenAIInterceptor that automatically records
        all OpenAI API calls to memory using the inheritance-based approach.

        Args:
            **kwargs: Additional arguments passed to OpenAI client (e.g., api_key)
                     These override any settings from the Memori provider config

        Returns:
            MemoriOpenAIInterceptor instance that works as a drop-in replacement
            for the standard OpenAI client

        Example:
            memori = Memori(api_key="sk-...")
            memori.enable()

            # Create interceptor client
            client = memori.create_openai_client()

            # Use exactly like standard OpenAI client
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Hello!"}]
            )
            # Conversation is automatically recorded
        """
        try:
            from ..integrations.openai_integration import create_openai_client

            return create_openai_client(self, self.provider_config, **kwargs)
        except ImportError as e:
            logger.error(f"Failed to import OpenAI integration: {e}")
            raise ImportError(
                "OpenAI integration not available. Install with: pip install openai"
            ) from e

    def create_openai_wrapper(self, **kwargs):
        """
        Create a legacy OpenAI wrapper (backward compatibility).

        DEPRECATED: Use create_openai_client() instead for better integration.

        Returns:
            MemoriOpenAI wrapper instance
        """
        try:
            from ..integrations.openai_integration import MemoriOpenAI

            return MemoriOpenAI(self, **kwargs)
        except ImportError as e:
            logger.error(f"Failed to import OpenAI integration: {e}")
            raise ImportError(
                "OpenAI integration not available. Install with: pip install openai"
            ) from e

    # Conversation management methods

    def get_conversation_stats(self) -> dict[str, Any]:
        """Get conversation manager statistics"""
        return self.conversation_manager.get_session_stats()

    def clear_conversation_history(self, session_id: str = None):
        """
        Clear conversation history

        Args:
            session_id: Specific session to clear. If None, clears current session.
        """
        if session_id is None:
            session_id = self._session_id
        self.conversation_manager.clear_session(session_id)
        logger.info(f"Cleared conversation history for session: {session_id}")

    def clear_all_conversations(self):
        """Clear all conversation histories"""
        self.conversation_manager.clear_all_sessions()
        logger.info("Cleared all conversation histories")

    def start_new_conversation(self) -> str:
        """
        Start a new conversation session

        Returns:
            New session ID
        """
        old_session_id = self._session_id
        self._session_id = str(uuid.uuid4())

        # Reset conscious context injection flag for new conversation
        self._conscious_context_injected = False

        logger.info(
            f"Started new conversation: {self._session_id} (previous: {old_session_id})"
        )
        return self._session_id

    def get_current_session_id(self) -> str:
        """Get current conversation session ID"""
        return self._session_id
