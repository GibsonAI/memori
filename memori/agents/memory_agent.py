"""
Memory Agent - Async Pydantic-based conversation processing

This agent processes conversations and extracts structured information with
enhanced classification and conscious context detection.
"""

import asyncio
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

import openai
from loguru import logger

if TYPE_CHECKING:
    from ..core.providers import ProviderConfig

from ..utils.pydantic_models import (
    ConversationContext,
    MemoryClassification,
    MemoryImportanceLevel,
    ProcessedLongTermMemory,
)


class MemoryAgent:
    """
    Async Memory Agent for processing conversations with enhanced classification
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        provider_config: Optional["ProviderConfig"] = None,
    ):
        """
        Initialize Memory Agent with LLM provider configuration

        Args:
            api_key: API key (deprecated, use provider_config)
            model: Model to use for structured output (defaults to 'gpt-4o' if not specified)
            provider_config: Provider configuration for LLM client
        """
        if provider_config:
            # Use provider configuration to create clients
            self.client = provider_config.create_client()
            self.async_client = provider_config.create_async_client()
            # Use provided model, fallback to provider config model, then default to gpt-4o
            self.model = model or provider_config.model or "gpt-4o"
            logger.debug(f"Memory agent initialized with model: {self.model}")
            self.provider_config = provider_config
        else:
            # Backward compatibility: use api_key directly with proper timeout and retries
            self.client = openai.OpenAI(api_key=api_key, timeout=60.0, max_retries=2)
            self.async_client = openai.AsyncOpenAI(
                api_key=api_key, timeout=60.0, max_retries=2
            )
            self.model = model or "gpt-4o"
            self.provider_config = None

        # Determine if we're using a local/custom endpoint that might not support structured outputs
        self._supports_structured_outputs = self._detect_structured_output_support()

        # Database type detection for unified processing
        self._database_type = None

    def _detect_database_type(self, db_manager):
        """Detect database type from db_manager"""
        if self._database_type is None:
            self._database_type = getattr(db_manager, "database_type", "sql")
            logger.debug(f"MemoryAgent: Detected database type: {self._database_type}")
        return self._database_type

    SYSTEM_PROMPT = """You are an advanced Memory Processing Agent responsible for analyzing conversations and extracting structured information with intelligent classification and conscious context detection.

Your primary functions:
1. **Intelligent Classification**: Categorize memories with enhanced classification system
2. **Conscious Context Detection**: Identify user context information for immediate promotion
3. **Entity Extraction**: Extract comprehensive entities and keywords
4. **Deduplication**: Identify and handle duplicate information
5. **Context Filtering**: Determine what should be stored vs filtered out

**ENHANCED CLASSIFICATION SYSTEM:**

**CONSCIOUS_INFO** (Auto-promote to short-term context):
- User's name, location, job, personal details
- Current projects, technologies they work with
- Preferences, work style, communication style
- Skills, expertise, learning goals
- Important personal context for AI interaction

**ESSENTIAL**:
- Core facts that define user's context
- Important preferences and opinions
- Key skills and knowledge areas
- Critical project information

**CONTEXTUAL**:
- Current work context
- Ongoing projects and goals
- Environmental setup and tools

**CONVERSATIONAL**:
- Regular discussions and questions
- Explanations and clarifications
- Problem-solving conversations

**REFERENCE**:
- Code examples and technical references
- Documentation and resources
- Learning materials

**PERSONAL**:
- Life events and personal information
- Relationships and social context
- Personal interests and hobbies

**IMPORTANCE LEVELS:**
- **CRITICAL**: Must never be lost
- **HIGH**: Very important for context
- **MEDIUM**: Useful to remember
- **LOW**: Nice to have context

**CONSCIOUS CONTEXT DETECTION:**
Mark is_user_context=True for:
- Personal identifiers (name, location, role)
- Work context (job, company, projects)
- Technical preferences (languages, tools, frameworks)
- Communication style and preferences
- Skills and expertise areas
- Learning goals and interests

Set promotion_eligible=True for memories that should be immediately available in short-term context for all future conversations.

**PROCESSING RULES:**
1. AVOID DUPLICATES: Check if similar information already exists
2. MERGE SIMILAR: Combine related information when appropriate
3. FILTER UNNECESSARY: Skip trivial greetings, acknowledgments
4. EXTRACT ENTITIES: Identify people, places, technologies, projects
5. ASSESS IMPORTANCE: Rate based on relevance to user context
6. FLAG USER CONTEXT: Mark information for conscious promotion

Focus on extracting information that would genuinely help provide better context and assistance in future conversations."""

    async def _retry_with_backoff(self, func, *args, max_retries=3, **kwargs):
        """
        Retry a function with exponential backoff for connection errors

        Args:
            func: Async function to retry
            max_retries: Maximum number of retry attempts (default: 3)
            *args, **kwargs: Arguments to pass to func

        Returns:
            Result from func

        Raises:
            Exception: Re-raises the last exception if all retries are exhausted
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                error_msg = str(e).lower()
                # Retry only on connection/timeout errors
                if "connection" in error_msg or "timeout" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = (2**attempt) * 0.5  # 0.5s, 1s, 2s
                        logger.debug(
                            f"Connection error (attempt {attempt + 1}/{max_retries}), "
                            f"retrying in {wait_time}s: {e}"
                        )
                        await asyncio.sleep(wait_time)
                        continue
                # Re-raise if not a retryable error or max retries reached
                raise
        # If all retries exhausted with connection errors, raise the last exception
        if last_exception:
            raise last_exception
        return None

    async def process_conversation_async(
        self,
        chat_id: str,
        user_input: str,
        ai_output: str,
        context: ConversationContext | None = None,
        existing_memories: list[str] | None = None,
    ) -> ProcessedLongTermMemory:
        """
        Async conversation processing with classification and conscious context detection

        Args:
            chat_id: Conversation ID
            user_input: User's input message
            ai_output: AI's response
            context: Additional conversation context
            existing_memories: List of existing memory summaries for deduplication

        Returns:
            Processed memory with classification and conscious flags
        """
        try:
            # Prepare conversation content
            conversation_text = f"User: {user_input}\nAssistant: {ai_output}"

            # Build system prompt
            system_prompt = self.SYSTEM_PROMPT

            # Add deduplication context
            if existing_memories:
                dedup_context = (
                    "\n\nEXISTING MEMORIES (for deduplication):\n"
                    + "\n".join(existing_memories[:10])
                )
                system_prompt += dedup_context

            # Prepare context information
            context_info = ""
            if context:
                context_info = f"""
CONVERSATION CONTEXT:
- Session: {context.session_id}
- Model: {context.model_used}
- User Projects: {', '.join(context.current_projects) if context.current_projects else 'None specified'}
- Relevant Skills: {', '.join(context.relevant_skills) if context.relevant_skills else 'None specified'}
- Topic Thread: {context.topic_thread or 'General conversation'}
"""

            # Try structured outputs first, fall back to manual parsing
            processed_memory = None

            if self._supports_structured_outputs:
                try:
                    # Call OpenAI Structured Outputs (async) with retry logic
                    completion = await self._retry_with_backoff(
                        lambda: self.async_client.beta.chat.completions.parse(
                            model=self.model,
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {
                                    "role": "user",
                                    "content": f"Process this conversation for enhanced memory storage:\n\n{conversation_text}\n{context_info}",
                                },
                            ],
                            response_format=ProcessedLongTermMemory,
                            temperature=0.1,  # Low temperature for consistent processing
                        )
                    )

                    # Handle potential refusal
                    if completion.choices[0].message.refusal:
                        logger.warning(
                            f"Memory processing refused for chat {chat_id}: {completion.choices[0].message.refusal}"
                        )
                        return self._create_empty_long_term_memory(
                            context.session_id if context else "default",
                            "Processing refused for safety reasons",
                        )

                    processed_memory = completion.choices[0].message.parsed
                    processed_memory.session_id = (
                        context.session_id if context else "default"
                    )
                    processed_memory.extraction_timestamp = datetime.now()

                except Exception as e:
                    logger.warning(
                        f"Structured outputs failed for {chat_id}, falling back to manual parsing: {e}"
                    )
                    self._supports_structured_outputs = (
                        False  # Disable for future calls
                    )
                    processed_memory = None

            # Fallback to manual parsing if structured outputs failed or not supported
            if processed_memory is None:
                processed_memory = await self._process_with_fallback_parsing(
                    chat_id, system_prompt, conversation_text, context_info
                )

            logger.debug(
                f"[AGENT] Processed conversation {chat_id[:8]}... - "
                f"classification: {processed_memory.classification.value} | "
                f"importance: {processed_memory.importance.value} | "
                f"conscious_context: {processed_memory.is_user_context} | "
                f"promotion_eligible: {processed_memory.promotion_eligible}"
            )

            return processed_memory

        except Exception as e:
            logger.error(
                f"[AGENT] Memory processing failed for {chat_id[:8]}... - {type(e).__name__}: {e}"
            )
            return self._create_empty_long_term_memory(
                context.session_id if context else "default",
                f"Processing failed: {str(e)}",
            )

    def _create_empty_long_term_memory(
        self, session_id: str, reason: str
    ) -> ProcessedLongTermMemory:
        """Create an empty long-term memory object for error cases"""
        return ProcessedLongTermMemory(
            content="Processing failed",
            summary="Processing failed",
            classification=MemoryClassification.CONVERSATIONAL,
            importance=MemoryImportanceLevel.LOW,
            session_id=session_id,
            classification_reason=reason,
            confidence_score=0.0,
            extraction_timestamp=datetime.now(),
        )

    # === DEDUPLICATION & FILTERING METHODS ===

    async def detect_duplicates(
        self,
        new_memory: ProcessedLongTermMemory,
        existing_memories: list[ProcessedLongTermMemory],
        similarity_threshold: float = 0.92,  # Increased from 0.8 to reduce false positives
    ) -> str | None:
        """
        Detect if new memory is a duplicate of existing memories

        Args:
            new_memory: New memory to check
            existing_memories: List of existing memories to compare against
            similarity_threshold: Threshold for considering memories similar (default: 0.92)

        Returns:
            Memory ID of duplicate if found, None otherwise
        """
        # FIX #2: Skip deduplication for conversational/query memories
        # Queries like "What's my name?" are valid every time and shouldn't be deduplicated
        skip_classifications = ["conversational", "query", "question", "reference"]
        if new_memory.classification in skip_classifications:
            logger.debug(
                f"[AGENT] Skipping duplicate check for {new_memory.classification} memory"
            )
            return None

        # Simple text similarity check - could be enhanced with embeddings
        new_content = new_memory.content.lower().strip()
        new_summary = new_memory.summary.lower().strip()

        for existing in existing_memories:
            existing_content = existing.content.lower().strip()
            existing_summary = existing.summary.lower().strip()

            # Check content similarity
            content_similarity = self._calculate_similarity(
                new_content, existing_content
            )
            summary_similarity = self._calculate_similarity(
                new_summary, existing_summary
            )

            # Average similarity score
            avg_similarity = (content_similarity + summary_similarity) / 2

            if avg_similarity >= similarity_threshold:
                # FIX #4: Improved logging with details
                logger.info(
                    f"[AGENT] Duplicate detected - {avg_similarity:.2f} similarity with {existing.session_id[:8]}..."
                )
                logger.debug(
                    f"[AGENT] Duplicate match details:\n"
                    f"  New content: '{new_content[:80]}...'\n"
                    f"  Existing content: '{existing_content[:80]}...'\n"
                    f"  Content similarity: {content_similarity:.2f}, Summary similarity: {summary_similarity:.2f}"
                )
                return existing.session_id

        return None

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Simple text similarity calculation using word overlap
        Could be enhanced with more sophisticated methods
        """
        if not text1 or not text2:
            return 0.0

        # Simple word-based similarity
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

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

            # Check for Azure endpoints (they may or may not support beta features)
            if self.provider_config and hasattr(self.provider_config, "api_type"):
                if self.provider_config.api_type == "azure":
                    logger.debug(
                        "Detected Azure endpoint, enabling structured outputs (may need manual verification)"
                    )
                    return (
                        True  # Azure may support it, let it try and fallback if needed
                    )
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

    async def _process_with_fallback_parsing(
        self,
        chat_id: str,
        system_prompt: str,
        conversation_text: str,
        context_info: str,
    ) -> ProcessedLongTermMemory:
        """
        Process conversation using regular chat completions with manual JSON parsing

        This method works with any OpenAI-compatible API that supports chat completions
        but doesn't support structured outputs (like Ollama, local models, etc.)
        """
        try:
            # Enhanced system prompt for JSON output
            json_system_prompt = (
                system_prompt
                + "\n\nIMPORTANT: You MUST respond with a valid JSON object that matches this exact schema:\n"
            )
            json_system_prompt += self._get_json_schema_prompt()
            json_system_prompt += "\n\nRespond ONLY with the JSON object, no additional text or formatting."

            # Call regular chat completions with retry logic
            completion = await self._retry_with_backoff(
                lambda: self.async_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": json_system_prompt},
                        {
                            "role": "user",
                            "content": f"Process this conversation for enhanced memory storage:\n\n{conversation_text}\n{context_info}",
                        },
                    ],
                    temperature=0.1,  # Low temperature for consistent processing
                    max_tokens=2000,  # Ensure enough tokens for full response
                )
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
                logger.error(f"Failed to parse JSON response for {chat_id}: {e}")
                logger.debug(f"Raw response: {response_text}")
                return self._create_empty_long_term_memory(
                    "default", f"JSON parsing failed: {e}"
                )

            # Convert to ProcessedLongTermMemory object with validation and defaults
            processed_memory = self._create_memory_from_dict(parsed_data, chat_id)

            logger.debug(
                f"Successfully parsed memory using fallback method for {chat_id}"
            )
            return processed_memory

        except Exception as e:
            logger.error(f"Fallback memory processing failed for {chat_id}: {e}")
            return self._create_empty_long_term_memory(
                "default", f"Fallback processing failed: {str(e)}"
            )

    def _get_json_schema_prompt(self) -> str:
        """
        Get JSON schema description for manual parsing
        """
        return """{
  "content": "string - The actual memory content",
  "summary": "string - Concise summary for search",
  "classification": "string - One of: essential, contextual, conversational, reference, personal, conscious-info",
  "importance": "string - One of: critical, high, medium, low",
  "topic": "string or null - Main topic/subject",
  "entities": ["array of strings - People, places, technologies mentioned"],
  "keywords": ["array of strings - Key terms for search"],
  "is_user_context": "boolean - Contains user personal info",
  "is_preference": "boolean - User preference/opinion",
  "is_skill_knowledge": "boolean - User's abilities/expertise",
  "is_current_project": "boolean - Current work context",
  "classification_reason": "string - Why this classification was chosen",
  "confidence_score": "number - AI confidence in extraction (0.0-1.0)",
  "promotion_eligible": "boolean - Should be promoted to short-term"
}"""

    def _create_memory_from_dict(
        self, data: dict[str, Any], chat_id: str
    ) -> ProcessedLongTermMemory:
        """
        Create ProcessedLongTermMemory from dictionary with proper validation and defaults
        """
        try:
            # Import here to avoid circular imports
            from ..utils.pydantic_models import (
                MemoryClassification,
                MemoryImportanceLevel,
            )

            # Validate and convert classification
            classification_str = (
                data.get("classification", "conversational").lower().replace("_", "-")
            )
            try:
                classification = MemoryClassification(classification_str)
            except ValueError:
                logger.warning(
                    f"Invalid classification '{classification_str}', using 'conversational'"
                )
                classification = MemoryClassification.CONVERSATIONAL

            # Validate and convert importance
            importance_str = data.get("importance", "medium").lower()
            try:
                importance = MemoryImportanceLevel(importance_str)
            except ValueError:
                logger.warning(f"Invalid importance '{importance_str}', using 'medium'")
                importance = MemoryImportanceLevel.MEDIUM

            # Create memory object with proper validation
            processed_memory = ProcessedLongTermMemory(
                content=data.get("content", "No content extracted"),
                summary=data.get("summary", "No summary available"),
                classification=classification,
                importance=importance,
                topic=data.get("topic"),
                entities=data.get("entities", []),
                keywords=data.get("keywords", []),
                is_user_context=bool(data.get("is_user_context", False)),
                is_preference=bool(data.get("is_preference", False)),
                is_skill_knowledge=bool(data.get("is_skill_knowledge", False)),
                is_current_project=bool(data.get("is_current_project", False)),
                session_id="default",  # Default session for fallback parsing
                confidence_score=float(data.get("confidence_score", 0.7)),
                classification_reason=data.get(
                    "classification_reason", "Extracted via fallback parsing"
                ),
                promotion_eligible=bool(data.get("promotion_eligible", False)),
                extraction_timestamp=datetime.now(),
            )

            return processed_memory

        except Exception as e:
            logger.error(f"Error creating memory from dict: {e}")
            return self._create_empty_long_term_memory(
                "default", f"Memory creation failed: {str(e)}"
            )

    def should_filter_memory(
        self, memory: ProcessedLongTermMemory, filters: dict[str, Any] | None = None
    ) -> bool:
        """
        Determine if memory should be filtered out

        Args:
            memory: Memory to check
            filters: Optional filtering criteria

        Returns:
            True if memory should be filtered out, False otherwise
        """
        if not filters:
            return False

        # Classification filter
        if "exclude_classifications" in filters:
            if memory.classification in filters["exclude_classifications"]:
                return True

        # Importance filter
        if "min_importance" in filters:
            importance_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}

            min_level = importance_map.get(filters["min_importance"], 1)
            memory_level = importance_map.get(memory.importance, 1)

            if memory_level < min_level:
                return True

        # Confidence filter
        if "min_confidence" in filters:
            if memory.confidence_score < filters["min_confidence"]:
                return True

        # Content filters
        if "exclude_keywords" in filters:
            content_lower = memory.content.lower()
            if any(
                keyword.lower() in content_lower
                for keyword in filters["exclude_keywords"]
            ):
                return True

        # Length filter
        if "min_content_length" in filters:
            if len(memory.content.strip()) < filters["min_content_length"]:
                return True

        return False
