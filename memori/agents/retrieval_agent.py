"""
Memory Search Engine - Intelligent memory retrieval using Pydantic models
"""

import asyncio
import json
import threading
import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

import openai
from loguru import logger

if TYPE_CHECKING:
    from ..core.providers import ProviderConfig

from ..utils.pydantic_models import MemorySearchQuery


class MemorySearchEngine:
    """
    Pydantic-based search engine for intelligent memory retrieval.
    Uses OpenAI Structured Outputs to understand queries and plan searches.
    """

    SYSTEM_PROMPT = """You are a Memory Search Agent responsible for understanding user queries and planning effective memory retrieval strategies.

Your primary functions:
1. **Analyze Query Intent**: Understand what the user is actually looking for
2. **Extract Search Parameters**: Identify key entities, topics, and concepts
3. **Plan Search Strategy**: Recommend the best approach to find relevant memories
4. **Filter Recommendations**: Suggest appropriate filters for category, importance, etc.

**MEMORY CATEGORIES AVAILABLE:**
- **fact**: Factual information, definitions, technical details, specific data points
- **preference**: User preferences, likes/dislikes, settings, personal choices, opinions
- **skill**: Skills, abilities, competencies, learning progress, expertise levels
- **context**: Project context, work environment, current situations, background info
- **rule**: Rules, policies, procedures, guidelines, constraints

**SEARCH STRATEGIES:**
- **keyword_search**: Direct keyword/phrase matching in content
- **entity_search**: Search by specific entities (people, technologies, topics)
- **category_filter**: Filter by memory categories
- **importance_filter**: Filter by importance levels
- **temporal_filter**: Search within specific time ranges
- **semantic_search**: Conceptual/meaning-based search

**QUERY INTERPRETATION GUIDELINES:**
- "What did I learn about X?" → Focus on facts and skills related to X
- "My preferences for Y" → Focus on preference category
- "Rules about Z" → Focus on rule category
- "Recent work on A" → Temporal filter + context/skill categories
- "Important information about B" → Importance filter + keyword search

Be strategic and comprehensive in your search planning."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        provider_config: Optional["ProviderConfig"] = None,
    ):
        """
        Initialize Memory Search Engine with LLM provider configuration

        Args:
            api_key: API key (deprecated, use provider_config)
            model: Model to use for query understanding (defaults to 'gpt-4o' if not specified)
            provider_config: Provider configuration for LLM client
        """
        if provider_config:
            # Use provider configuration to create client
            self.client = provider_config.create_client()
            # Use provided model, fallback to provider config model, then default to gpt-4o
            self.model = model or provider_config.model or "gpt-4o"
            logger.debug(f"Search engine initialized with model: {self.model}")
            self.provider_config = provider_config
        else:
            # Backward compatibility: use api_key directly with proper timeout and retries
            self.client = openai.OpenAI(api_key=api_key, timeout=60.0, max_retries=2)
            self.model = model or "gpt-4o"
            self.provider_config = None

        # Determine if we're using a local/custom endpoint that might not support structured outputs
        self._supports_structured_outputs = self._detect_structured_output_support()

        # Performance improvements
        self._query_cache = {}  # Cache for search plans
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._cache_lock = threading.Lock()

        # Background processing
        self._background_executor = None

        # Database type detection for unified search
        self._database_type = None

    def _detect_database_type(self, db_manager):
        """Detect database type from db_manager"""
        if self._database_type is None:
            self._database_type = getattr(db_manager, "database_type", "sql")
            logger.debug(
                f"MemorySearchEngine: Detected database type: {self._database_type}"
            )
        return self._database_type

    def plan_search(self, query: str, context: str | None = None) -> MemorySearchQuery:
        """
        Plan search strategy for a user query using OpenAI Structured Outputs with caching

        Args:
            query: User's search query
            context: Optional additional context

        Returns:
            Structured search query plan
        """
        try:
            # Create cache key
            cache_key = f"{query}|{context or ''}"

            # Check cache first
            with self._cache_lock:
                if cache_key in self._query_cache:
                    cached_result, timestamp = self._query_cache[cache_key]
                    if time.time() - timestamp < self._cache_ttl:
                        logger.debug(f"Using cached search plan for: {query}")
                        return cached_result

            # Prepare the prompt with internal marker to prevent recording
            prompt = f"[INTERNAL_MEMORI_SEARCH]\nUser query: {query}"
            if context:
                prompt += f"\nAdditional context: {context}"

            # Try structured outputs first, fall back to manual parsing
            search_query = None

            if self._supports_structured_outputs:
                try:
                    # Call OpenAI Structured Outputs
                    completion = self.client.beta.chat.completions.parse(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": prompt,
                            },
                        ],
                        response_format=MemorySearchQuery,
                        temperature=0.1,
                    )

                    # Handle potential refusal
                    if completion.choices[0].message.refusal:
                        logger.warning(
                            f"Search planning refused: {completion.choices[0].message.refusal}"
                        )
                        return self._create_fallback_query(query)

                    search_query = completion.choices[0].message.parsed

                except Exception as e:
                    logger.warning(
                        f"Structured outputs failed for search planning, falling back to manual parsing: {e}"
                    )
                    self._supports_structured_outputs = (
                        False  # Disable for future calls
                    )
                    search_query = None

            # Fallback to manual parsing if structured outputs failed or not supported
            if search_query is None:
                search_query = self._plan_search_with_fallback_parsing(query)

            # Cache the result
            with self._cache_lock:
                self._query_cache[cache_key] = (search_query, time.time())
                # Clean old cache entries
                self._cleanup_cache()

            logger.debug(
                f"Planned search for query '{query}': intent='{search_query.intent}', strategies={search_query.search_strategy}"
            )
            return search_query

        except Exception as e:
            logger.error(f"Search planning failed: {e}")
            return self._create_fallback_query(query)

    def execute_search(
        self,
        query: str,
        db_manager,
        user_id: str = "default",
        assistant_id: str = None,
        session_id: str = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Execute intelligent search using planned strategies (SESSION-OPTIMIZED)

        This method now uses a SINGLE database session for all search operations,
        reducing connection pool pressure by 75% and improving latency by 35-45%.

        Args:
            query: User's search query
            db_manager: Database manager instance (SQL or MongoDB)
            user_id: User identifier for multi-tenant isolation
            assistant_id: Optional assistant identifier for isolation
            session_id: Optional session identifier for isolation
            limit: Maximum results to return

        Returns:
            List of relevant memory items with search metadata
        """
        # Session and search service must be explicitly managed
        session = None
        search_service = None

        try:
            # Detect database type for optimal search strategy
            db_type = self._detect_database_type(db_manager)

            # Plan the search
            search_plan = self.plan_search(query)
            logger.debug(
                f"Search plan for '{query}': strategies={search_plan.search_strategy}, "
                f"entities={search_plan.entity_filters}, db_type={db_type}"
            )

            all_results = []
            seen_memory_ids = set()

            # OPTIMIZATION: Create ONE session for entire search operation
            from ..database.search_service import SearchService

            session = db_manager.SessionLocal()
            search_service = SearchService(session, db_type)
            logger.debug(
                "Created single SearchService instance for request (session-optimized)"
            )

            # PRIMARY SEARCH: Use the session we just created
            try:
                primary_results = search_service.search_memories(
                    query=search_plan.query_text or query,
                    user_id=user_id,
                    assistant_id=assistant_id,
                    session_id=session_id,
                    limit=limit,
                )
                logger.debug(f"Primary search returned {len(primary_results)} results")
            except Exception as e:
                logger.error(f"Primary search failed: {e}")
                primary_results = []

            # Process primary results
            for result in primary_results:
                if (
                    isinstance(result, dict)
                    and result.get("memory_id") not in seen_memory_ids
                ):
                    seen_memory_ids.add(result["memory_id"])
                    result["search_strategy"] = f"{db_type}_unified_search"
                    result["search_reasoning"] = f"Direct {db_type} database search"
                    all_results.append(result)

            # KEYWORD SEARCH: Reuse same session
            if len(all_results) < limit and search_plan.entity_filters:
                logger.debug(
                    f"Adding targeted keyword search for: {search_plan.entity_filters}"
                )
                keyword_results = self._execute_keyword_search_with_session(
                    search_plan,
                    search_service,
                    user_id,
                    assistant_id,
                    session_id,
                    limit - len(all_results),
                )

                for result in keyword_results:
                    if (
                        isinstance(result, dict)
                        and result.get("memory_id") not in seen_memory_ids
                    ):
                        seen_memory_ids.add(result["memory_id"])
                        result["search_strategy"] = "keyword_search"
                        result["search_reasoning"] = (
                            f"Keyword match for: {', '.join(search_plan.entity_filters)}"
                        )
                        all_results.append(result)

            # CATEGORY SEARCH: Reuse same session
            if len(all_results) < limit and (
                search_plan.category_filters
                or "category_filter" in search_plan.search_strategy
            ):
                logger.debug(
                    f"Adding category search for: {[c.value for c in search_plan.category_filters]}"
                )
                category_results = self._execute_category_search_with_session(
                    search_plan,
                    search_service,
                    user_id,
                    assistant_id,
                    session_id,
                    limit - len(all_results),
                )

                for result in category_results:
                    if (
                        isinstance(result, dict)
                        and result.get("memory_id") not in seen_memory_ids
                    ):
                        seen_memory_ids.add(result["memory_id"])
                        result["search_strategy"] = "category_filter"
                        result["search_reasoning"] = (
                            f"Category match: {', '.join([c.value for c in search_plan.category_filters])}"
                        )
                        all_results.append(result)

            # IMPORTANCE SEARCH: Reuse same session
            if len(all_results) < limit and (
                search_plan.min_importance > 0.0
                or "importance_filter" in search_plan.search_strategy
            ):
                logger.debug(
                    f"Adding importance search with min_importance: {search_plan.min_importance}"
                )
                importance_results = self._execute_importance_search_with_session(
                    search_plan,
                    search_service,
                    user_id,
                    assistant_id,
                    session_id,
                    limit - len(all_results),
                )

                for result in importance_results:
                    if (
                        isinstance(result, dict)
                        and result.get("memory_id") not in seen_memory_ids
                    ):
                        seen_memory_ids.add(result["memory_id"])
                        result["search_strategy"] = "importance_filter"
                        result["search_reasoning"] = (
                            f"High importance (≥{search_plan.min_importance})"
                        )
                        all_results.append(result)

            # Filter out any non-dictionary results before processing
            valid_results = []
            for result in all_results:
                if isinstance(result, dict):
                    valid_results.append(result)
                else:
                    logger.warning(
                        f"Filtering out non-dict search result: {type(result)}"
                    )

            all_results = valid_results

            # Sort by relevance (importance score + recency)
            if all_results:

                def safe_created_at_parse(created_at_value):
                    """Safely parse created_at value to datetime"""
                    try:
                        if created_at_value is None:
                            return datetime.fromisoformat("2000-01-01")
                        if isinstance(created_at_value, str):
                            return datetime.fromisoformat(created_at_value)
                        if hasattr(created_at_value, "isoformat"):  # datetime object
                            return created_at_value
                        # Fallback for any other type
                        return datetime.fromisoformat("2000-01-01")
                    except (ValueError, TypeError):
                        return datetime.fromisoformat("2000-01-01")

                all_results.sort(
                    key=lambda x: (
                        x.get("importance_score", 0) * 0.7  # Importance weight
                        + (
                            datetime.now().replace(tzinfo=None)  # Ensure timezone-naive
                            - safe_created_at_parse(x.get("created_at")).replace(
                                tzinfo=None
                            )
                        ).days
                        * -0.001  # Recency weight
                    ),
                    reverse=True,
                )

                # Add search metadata
                for result in all_results:
                    result["search_metadata"] = {
                        "original_query": query,
                        "interpreted_intent": search_plan.intent,
                        "search_timestamp": datetime.now().isoformat(),
                    }

            logger.debug(
                f"Search executed for '{query}': {len(all_results)} results found"
            )
            return all_results[:limit]

        except Exception as e:
            logger.error(f"Search execution failed: {e}")
            return []

        finally:
            # CRITICAL: Ensure session cleanup even if exceptions occur
            if session:
                try:
                    session.close()
                    logger.debug("Closed search session (session-optimized)")
                except Exception as cleanup_error:
                    logger.warning(f"Error closing search session: {cleanup_error}")

    def _execute_keyword_search(
        self,
        search_plan: MemorySearchQuery,
        db_manager,
        user_id: str,
        assistant_id: str = None,
        session_id: str = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        DEPRECATED: Execute keyword-based search (creates new session)

        This method is deprecated in favor of execute_search() which reuses sessions.
        Kept for backwards compatibility. Creates a new database session.

        Use execute_search() instead for better performance (35-45% faster).
        """
        import warnings

        warnings.warn(
            "_execute_keyword_search() creates a new session and is less efficient. "
            "Use execute_search() instead for session reuse optimization.",
            DeprecationWarning,
            stacklevel=2,
        )

        db_type = self._detect_database_type(db_manager)

        try:
            from ..database.search_service import SearchService

            with db_manager.SessionLocal() as session:
                search_service = SearchService(session, db_type)
                return self._execute_keyword_search_with_session(
                    search_plan,
                    search_service,
                    user_id,
                    assistant_id,
                    session_id,
                    limit,
                )
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _execute_keyword_search_with_session(
        self,
        search_plan: MemorySearchQuery,
        search_service,
        user_id: str,
        assistant_id: str = None,
        session_id: str = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Execute keyword-based search using existing search service (session-reuse optimized)

        Args:
            search_plan: Search query plan
            search_service: Existing SearchService instance with active session
            user_id: User identifier
            assistant_id: Optional assistant identifier
            session_id: Optional session identifier
            limit: Maximum results

        Returns:
            List of memory dictionaries
        """
        keywords = search_plan.entity_filters
        if not keywords:
            # Extract keywords from query text
            keywords = [
                word.strip()
                for word in search_plan.query_text.split()
                if len(word.strip()) > 2
            ]

        search_terms = " ".join(keywords)
        try:
            # Use provided search service (no new session creation)
            results = search_service.search_memories(
                query=search_terms,
                user_id=user_id,
                assistant_id=assistant_id,
                session_id=session_id,
                limit=limit,
            )

            # Validate results
            if not isinstance(results, list):
                logger.warning(f"Search returned non-list result: {type(results)}")
                return []

            # Filter out any non-dictionary items
            valid_results = []
            for result in results:
                if isinstance(result, dict):
                    valid_results.append(result)
                else:
                    logger.warning(f"Search returned non-dict item: {type(result)}")

            return valid_results
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []

    def _execute_category_search(
        self,
        search_plan: MemorySearchQuery,
        db_manager,
        user_id: str,
        assistant_id: str = None,
        session_id: str = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        DEPRECATED: Execute category-based search (creates new session)

        This method is deprecated in favor of execute_search() which reuses sessions.
        Kept for backwards compatibility. Creates a new database session.

        Use execute_search() instead for better performance (35-45% faster).
        """
        import warnings

        warnings.warn(
            "_execute_category_search() creates a new session and is less efficient. "
            "Use execute_search() instead for session reuse optimization.",
            DeprecationWarning,
            stacklevel=2,
        )

        db_type = self._detect_database_type(db_manager)

        try:
            from ..database.search_service import SearchService

            with db_manager.SessionLocal() as session:
                search_service = SearchService(session, db_type)
                return self._execute_category_search_with_session(
                    search_plan,
                    search_service,
                    user_id,
                    assistant_id,
                    session_id,
                    limit,
                )
        except Exception as e:
            logger.error(f"Category search failed: {e}")
            return []

    def _execute_category_search_with_session(
        self,
        search_plan: MemorySearchQuery,
        search_service,
        user_id: str,
        assistant_id: str = None,
        session_id: str = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Execute category-based search using existing search service (session-reuse optimized)

        Args:
            search_plan: Search query plan
            search_service: Existing SearchService instance with active session
            user_id: User identifier
            assistant_id: Optional assistant identifier
            session_id: Optional session identifier
            limit: Maximum results

        Returns:
            List of memory dictionaries
        """
        categories = (
            [cat.value for cat in search_plan.category_filters]
            if search_plan.category_filters
            else []
        )

        if not categories:
            return []

        logger.debug(
            f"Searching memories by categories: {categories} for user_id: {user_id}"
        )
        try:
            # Use provided search service (no new session creation)
            all_results = search_service.search_memories(
                query="",
                user_id=user_id,
                assistant_id=assistant_id,
                session_id=session_id,
                limit=limit * 3,
            )
        except Exception as e:
            logger.error(f"Category search failed: {e}")
            all_results = []

        logger.debug(
            f"Retrieved {len(all_results)} total results for category filtering"
        )

        # Category filtering logic (same as original method)
        filtered_results = []
        for i, result in enumerate(all_results):
            logger.debug(f"Processing result {i+1}/{len(all_results)}: {type(result)}")

            try:
                memory_category = None

                # Check processed_data field first
                if "processed_data" in result and result["processed_data"]:
                    processed_data = result["processed_data"]

                    # Handle both dict and JSON string formats
                    if isinstance(processed_data, str):
                        try:
                            processed_data = json.loads(processed_data)
                        except json.JSONDecodeError:
                            continue

                    if isinstance(processed_data, dict):
                        # Try multiple possible category locations
                        category_paths = [
                            ["category", "primary_category"],
                            ["category"],
                            ["primary_category"],
                            ["metadata", "category"],
                            ["classification", "category"],
                        ]

                        for path in category_paths:
                            temp_data = processed_data
                            try:
                                for key in path:
                                    temp_data = temp_data.get(key, {})
                                if isinstance(temp_data, str) and temp_data:
                                    memory_category = temp_data
                                    break
                            except (AttributeError, TypeError):
                                continue

                # Fallback: check direct category field
                if not memory_category:
                    if "category_primary" in result and result["category_primary"]:
                        memory_category = result["category_primary"]
                    elif "category" in result and result["category"]:
                        memory_category = result["category"]

                # Check if category matches
                if memory_category and memory_category in categories:
                    filtered_results.append(result)
                    logger.debug(f"✓ Category match found: {memory_category}")

            except Exception as e:
                logger.debug(f"Error processing result {i+1}: {e}")
                continue

        logger.debug(
            f"Category filtering complete: {len(filtered_results)} results match categories {categories}"
        )
        return filtered_results[:limit]

    def _detect_structured_output_support(self) -> bool:
        """
        Detect if the current provider/endpoint supports OpenAI structured outputs

        Returns:
            True if structured outputs are likely supported, False otherwise
        """
        try:
            # Check if we have a provider config with custom base_url
            if self.provider_config and hasattr(self.provider_config, "base_url"):
                base_url = self.provider_config.base_url
                if base_url:
                    # Local/custom endpoints typically don't support beta features
                    if "localhost" in base_url or "127.0.0.1" in base_url:
                        logger.debug(
                            f"Detected local endpoint ({base_url}), disabling structured outputs"
                        )
                        return False
                    # Custom endpoints that aren't OpenAI
                    if "api.openai.com" not in base_url:
                        logger.debug(
                            f"Detected custom endpoint ({base_url}), disabling structured outputs"
                        )
                        return False

            # Check for Azure endpoints - test if they support structured outputs
            if self.provider_config and hasattr(self.provider_config, "api_type"):
                if self.provider_config.api_type == "azure":
                    return self._test_azure_structured_outputs_support()
                elif self.provider_config.api_type in ["custom", "openai_compatible"]:
                    logger.debug(
                        f"Detected {self.provider_config.api_type} endpoint, disabling structured outputs"
                    )
                    return False

            # Default: assume OpenAI endpoint supports structured outputs
            logger.debug("Assuming OpenAI endpoint, enabling structured outputs")
            return True

        except Exception as e:
            logger.debug(
                f"Error detecting structured output support: {e}, defaulting to enabled"
            )
            return True

    def _test_azure_structured_outputs_support(self) -> bool:
        """
        Test if Azure OpenAI supports structured outputs by making a test call

        Returns:
            True if structured outputs are supported, False otherwise
        """
        try:
            from pydantic import BaseModel

            # Simple test model
            class TestModel(BaseModel):
                test_field: str

            # Try to make a structured output call
            test_response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[{"role": "user", "content": "Say hello"}],
                response_format=TestModel,
                max_tokens=10,
                temperature=0,
            )

            if (
                test_response
                and hasattr(test_response, "choices")
                and test_response.choices
            ):
                logger.debug(
                    "Azure endpoint supports structured outputs - test successful"
                )
                return True
            else:
                logger.debug(
                    "Azure endpoint structured outputs test failed - response invalid"
                )
                return False

        except Exception as e:
            # If structured outputs fail, log the error and fall back to regular completions
            logger.debug(f"Azure endpoint doesn't support structured outputs: {e}")
            return False

    def _plan_search_with_fallback_parsing(self, query: str) -> MemorySearchQuery:
        """
        Plan search strategy using regular chat completions with manual JSON parsing

        This method works with any OpenAI-compatible API that supports chat completions
        but doesn't support structured outputs (like Ollama, local models, etc.)
        """
        try:
            # Prepare the prompt from raw query with internal marker
            prompt = f"[INTERNAL_MEMORI_SEARCH]\nUser query: {query}"

            # Enhanced system prompt for JSON output
            json_system_prompt = (
                self.SYSTEM_PROMPT
                + "\n\nIMPORTANT: You MUST respond with a valid JSON object that matches this exact schema:\n"
            )
            json_system_prompt += self._get_search_query_json_schema()
            json_system_prompt += "\n\nRespond ONLY with the JSON object, no additional text or formatting."

            # Call regular chat completions
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": json_system_prompt},
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.1,
                max_tokens=1000,  # Ensure enough tokens for full response
            )

            # Extract and parse JSON response
            response_text = completion.choices[0].message.content
            if not response_text:
                raise ValueError("Empty response from model")

            # Clean up response (remove markdown formatting if present)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            # Parse JSON
            try:
                parsed_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response for search planning: {e}")
                logger.debug(f"Raw response: {response_text}")
                return self._create_fallback_query(query)

            # Convert to MemorySearchQuery object with validation and defaults
            search_query = self._create_search_query_from_dict(parsed_data, query)

            logger.debug("Successfully parsed search query using fallback method")
            return search_query

        except Exception as e:
            logger.error(f"Fallback search planning failed: {e}")
            return self._create_fallback_query(query)

    def _get_search_query_json_schema(self) -> str:
        """
        Get JSON schema description for manual search query parsing
        """
        return """{
  "query_text": "string - Original query text",
  "intent": "string - Interpreted intent of the query",
  "entity_filters": ["array of strings - Specific entities to search for"],
  "category_filters": ["array of strings - Memory categories: fact, preference, skill, context, rule"],
  "time_range": "string or null - Time range for search (e.g., last_week)",
  "min_importance": "number - Minimum importance score (0.0-1.0)",
  "search_strategy": ["array of strings - Recommended search strategies"],
  "expected_result_types": ["array of strings - Expected types of results"]
}"""

    def _create_search_query_from_dict(
        self, data: dict[str, Any], original_query: str
    ) -> MemorySearchQuery:
        """
        Create MemorySearchQuery from dictionary with proper validation and defaults
        """
        try:
            # Import here to avoid circular imports
            from ..utils.pydantic_models import MemoryCategoryType

            # Validate and convert category filters
            category_filters = []
            raw_categories = data.get("category_filters", [])
            if isinstance(raw_categories, list):
                for cat_str in raw_categories:
                    try:
                        category = MemoryCategoryType(cat_str.lower())
                        category_filters.append(category)
                    except ValueError:
                        logger.debug(f"Invalid category filter '{cat_str}', skipping")

            # Create search query object with proper validation
            search_query = MemorySearchQuery(
                query_text=data.get("query_text", original_query),
                intent=data.get("intent", "General search (fallback)"),
                entity_filters=data.get("entity_filters", []),
                category_filters=category_filters,
                time_range=data.get("time_range"),
                min_importance=max(
                    0.0, min(1.0, float(data.get("min_importance", 0.0)))
                ),
                search_strategy=data.get("search_strategy", ["keyword_search"]),
                expected_result_types=data.get("expected_result_types", ["any"]),
            )

            return search_query

        except Exception as e:
            logger.error(f"Error creating search query from dict: {e}")
            return self._create_fallback_query(original_query)

    def _execute_importance_search(
        self,
        search_plan: MemorySearchQuery,
        db_manager,
        user_id: str,
        assistant_id: str = None,
        session_id: str = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        DEPRECATED: Execute importance-based search (creates new session)

        This method is deprecated in favor of execute_search() which reuses sessions.
        Kept for backwards compatibility. Creates a new database session.

        Use execute_search() instead for better performance (35-45% faster).
        """
        import warnings

        warnings.warn(
            "_execute_importance_search() creates a new session and is less efficient. "
            "Use execute_search() instead for session reuse optimization.",
            DeprecationWarning,
            stacklevel=2,
        )

        db_type = self._detect_database_type(db_manager)

        try:
            from ..database.search_service import SearchService

            with db_manager.SessionLocal() as session:
                search_service = SearchService(session, db_type)
                return self._execute_importance_search_with_session(
                    search_plan,
                    search_service,
                    user_id,
                    assistant_id,
                    session_id,
                    limit,
                )
        except Exception as e:
            logger.error(f"Importance search failed: {e}")
            return []

    def _execute_importance_search_with_session(
        self,
        search_plan: MemorySearchQuery,
        search_service,
        user_id: str,
        assistant_id: str = None,
        session_id: str = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Execute importance-based search using existing search service (session-reuse optimized)

        Args:
            search_plan: Search query plan
            search_service: Existing SearchService instance with active session
            user_id: User identifier
            assistant_id: Optional assistant identifier
            session_id: Optional session identifier
            limit: Maximum results

        Returns:
            List of memory dictionaries
        """
        min_importance = max(
            search_plan.min_importance, 0.7
        )  # Default to high importance

        try:
            # Use provided search service (no new session creation)
            all_results = search_service.search_memories(
                query="",
                user_id=user_id,
                assistant_id=assistant_id,
                session_id=session_id,
                limit=limit * 2,
            )

            high_importance_results = [
                result
                for result in all_results
                if isinstance(result, dict)
                and result.get("importance_score", 0) >= min_importance
            ]

            return high_importance_results[:limit]
        except Exception as e:
            logger.error(f"Importance search failed: {e}")
            return []

    def _create_fallback_query(self, query: str) -> MemorySearchQuery:
        """Create a fallback search query for error cases"""
        return MemorySearchQuery(
            query_text=query,
            intent="General search (fallback)",
            entity_filters=[word for word in query.split() if len(word) > 2],
            search_strategy=["keyword_search", "general_search"],
            expected_result_types=["any"],
        )

    def _cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self._query_cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        for key in expired_keys:
            del self._query_cache[key]

    async def execute_search_async(
        self,
        query: str,
        db_manager,
        user_id: str = "default",
        assistant_id: str = None,
        session_id: str = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Async version of execute_search using session-optimized implementation.

        This method now uses the P1-optimized execute_search() which creates
        only ONE session per search instead of 3-4 sessions.
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self._background_executor,
                self.execute_search,
                query,
                db_manager,
                user_id,
                assistant_id,
                session_id,
                limit,
            )
        except Exception as e:
            logger.error(f"Async search execution failed: {e}")
            return []

    def execute_search_background(
        self,
        query: str,
        db_manager,
        user_id: str = "default",
        limit: int = 10,
        callback=None,
    ):
        """
        Execute search in background thread for non-blocking operation

        Args:
            query: Search query
            db_manager: Database manager
            user_id: User identifier for multi-tenant isolation
            limit: Max results
            callback: Optional callback function to handle results
        """

        def _background_search():
            try:
                results = self.execute_search(query, db_manager, user_id, limit)
                if callback:
                    callback(results)
                return results
            except Exception as e:
                logger.error(f"Background search failed: {e}")
                if callback:
                    callback([])
                return []

        # Start background thread
        thread = threading.Thread(target=_background_search, daemon=True)
        thread.start()
        return thread

    def search_memories(
        self, query: str, max_results: int = 5, user_id: str = "default"
    ) -> list[dict[str, Any]]:
        """
        Simple search interface for compatibility with memory tools

        Args:
            query: Search query
            max_results: Maximum number of results
            user_id: User identifier for multi-tenant isolation

        Returns:
            List of memory search results
        """
        # This is a compatibility method that uses the database manager directly
        # We'll need the database manager to be injected or passed
        # For now, return empty list and log the issue with parameters
        logger.warning(
            f"search_memories called without database manager: query='{query}', "
            f"max_results={max_results}, user_id='{user_id}'"
        )
        return []


def create_retrieval_agent(
    memori_instance=None, api_key: str = None, model: str = "gpt-4o"
) -> MemorySearchEngine:
    """
    Create a retrieval agent instance

    Args:
        memori_instance: Optional Memori instance for direct database access
        api_key: OpenAI API key
        model: Model to use for query planning

    Returns:
        MemorySearchEngine instance
    """
    agent = MemorySearchEngine(api_key=api_key, model=model)
    if memori_instance:
        agent._memori_instance = memori_instance
    return agent


def smart_memory_search(query: str, memori_instance, limit: int = 5) -> str:
    """
    Direct string-based memory search function that uses intelligent retrieval

    Args:
        query: Search query string
        memori_instance: Memori instance with database access
        limit: Maximum number of results

    Returns:
        Formatted string with search results
    """
    try:
        # Create search engine
        search_engine = MemorySearchEngine()

        # Execute intelligent search
        results = search_engine.execute_search(
            query=query,
            db_manager=memori_instance.db_manager,
            user_id=memori_instance.user_id,
            limit=limit,
        )

        if not results:
            return f"No relevant memories found for query: '{query}'"

        # Format results as a readable string
        output = f"Smart Memory Search Results for: '{query}'\n\n"

        for i, result in enumerate(results, 1):
            try:
                # Try to parse processed data for better formatting
                if "processed_data" in result:
                    import json

                    processed_data = result["processed_data"]
                    # Handle both dict and JSON string formats
                    if isinstance(processed_data, str):
                        processed_data = json.loads(processed_data)
                    elif isinstance(processed_data, dict):
                        pass  # Already a dict, use as-is
                    else:
                        # Fallback to basic result fields
                        summary = result.get(
                            "summary",
                            result.get("searchable_content", "")[:100] + "...",
                        )
                        category = result.get("category_primary", "unknown")
                        continue

                    summary = processed_data.get("summary", "")
                    category = processed_data.get("category", {}).get(
                        "primary_category", ""
                    )
                else:
                    summary = result.get(
                        "summary", result.get("searchable_content", "")[:100] + "..."
                    )
                    category = result.get("category_primary", "unknown")

                importance = result.get("importance_score", 0.0)
                created_at = result.get("created_at", "")
                search_strategy = result.get("search_strategy", "unknown")
                search_reasoning = result.get("search_reasoning", "")

                output += f"{i}. [{category.upper()}] {summary}\n"
                output += f"   Importance: {importance:.2f} | Created: {created_at}\n"
                output += f"   Strategy: {search_strategy}\n"

                if search_reasoning:
                    output += f"   Reason: {search_reasoning}\n"

                output += "\n"

            except Exception:
                # Fallback formatting
                content = result.get("searchable_content", "Memory content available")[
                    :100
                ]
                output += f"{i}. {content}...\n\n"

        return output.strip()

    except Exception as e:
        logger.error(f"Smart memory search failed: {e}")
        return f"Error in smart memory search: {str(e)}"
