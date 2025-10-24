"""
Conversation Manager for Stateless LLM SDK Integration

This module provides conversation tracking and context management for stateless LLM SDKs
like OpenAI, Anthropic, etc. It bridges the gap between memori's stateful memory system
and stateless LLM API calls by maintaining conversation history and context.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from loguru import logger


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation"""

    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationSession:
    """Represents an active conversation session"""

    session_id: str
    messages: list[ConversationMessage] = field(default_factory=list)
    context_injected: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: dict[str, Any] = None):
        """Add a message to the conversation"""
        message = ConversationMessage(
            role=role, content=content, metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_accessed = datetime.now()

    def get_history_messages(self, limit: int = 10) -> list[dict[str, str]]:
        """Get conversation history in OpenAI message format"""
        # Get recent messages (excluding system messages)
        user_assistant_messages = [
            msg for msg in self.messages if msg.role in ["user", "assistant"]
        ]

        # Limit to recent messages to prevent context overflow
        recent_messages = (
            user_assistant_messages[-limit:] if limit > 0 else user_assistant_messages
        )

        return [{"role": msg.role, "content": msg.content} for msg in recent_messages]


class ConversationManager:
    """
    Manages conversation sessions for stateless LLM integrations.

    This class provides:
    - Session-based conversation tracking
    - Context injection with conversation history
    - Automatic session cleanup
    - Support for both conscious_ingest and auto_ingest modes
    """

    def __init__(
        self,
        max_sessions: int = 100,
        session_timeout_minutes: int = 60,
        max_history_per_session: int = 20,
    ):
        """
        Initialize ConversationManager

        Args:
            max_sessions: Maximum number of active sessions
            session_timeout_minutes: Session timeout in minutes
            max_history_per_session: Maximum messages to keep per session
        """
        self.max_sessions = max_sessions
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.max_history_per_session = max_history_per_session

        # Active conversation sessions
        self.sessions: dict[str, ConversationSession] = {}

        logger.info(
            f"ConversationManager initialized: max_sessions={max_sessions}, "
            f"timeout={session_timeout_minutes}min, max_history={max_history_per_session}"
        )

    def get_or_create_session(self, session_id: str = None) -> ConversationSession:
        """
        Get existing session or create new one

        Args:
            session_id: Optional session ID. If None, generates new one.

        Returns:
            ConversationSession instance
        """
        if session_id is None:
            session_id = str(uuid.uuid4())

        # Clean up expired sessions first
        self._cleanup_expired_sessions()

        # Get existing session or create new one
        if session_id not in self.sessions:
            if len(self.sessions) >= self.max_sessions:
                # Remove oldest session to make room
                oldest_session_id = min(
                    self.sessions.keys(),
                    key=lambda sid: self.sessions[sid].last_accessed,
                )
                del self.sessions[oldest_session_id]
                logger.debug(f"Removed oldest session {oldest_session_id} to make room")

            self.sessions[session_id] = ConversationSession(session_id=session_id)
            logger.debug(f"Created new conversation session: {session_id}")
        else:
            # Update last accessed time
            self.sessions[session_id].last_accessed = datetime.now()

        return self.sessions[session_id]

    def add_user_message(
        self, session_id: str, content: str, metadata: dict[str, Any] = None
    ):
        """Add user message to conversation session"""
        session = self.get_or_create_session(session_id)
        session.add_message("user", content, metadata)

        # Limit history to prevent memory bloat
        if len(session.messages) > self.max_history_per_session:
            # Keep system messages and recent messages
            system_messages = [msg for msg in session.messages if msg.role == "system"]
            other_messages = [msg for msg in session.messages if msg.role != "system"]

            # Keep recent non-system messages
            recent_messages = other_messages[
                -(self.max_history_per_session - len(system_messages)) :
            ]
            session.messages = system_messages + recent_messages

            logger.debug(f"Trimmed conversation history for session {session_id}")

    def add_assistant_message(
        self, session_id: str, content: str, metadata: dict[str, Any] = None
    ):
        """Add assistant message to conversation session"""
        session = self.get_or_create_session(session_id)
        session.add_message("assistant", content, metadata)

    def inject_context_with_history(
        self,
        session_id: str,
        messages: list[dict[str, str]],
        memori_instance,
        mode: str = "conscious",
    ) -> list[dict[str, str]]:
        """
        Inject context and conversation history into messages

        Args:
            session_id: Conversation session ID
            messages: Original messages from API call
            memori_instance: Memori instance for context retrieval
            mode: Context injection mode ("conscious" or "auto")

        Returns:
            Modified messages with context and history injected
        """
        try:
            session = self.get_or_create_session(session_id)

            # Extract user input from current messages
            user_input = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_input = msg.get("content", "")
                    break

            # Add current user message to session history
            if user_input:
                self.add_user_message(session_id, user_input)

            # Build context based on mode
            context_prompt = ""

            if mode == "conscious":
                # Conscious mode: Always inject short-term memory context
                # (Not just once - this fixes the original bug)
                context = memori_instance._get_conscious_context()
                if context:
                    context_prompt = self._build_conscious_context_prompt(context)
                    logger.debug(
                        f"Injected conscious context with {len(context)} items for session {session_id}"
                    )

            elif mode == "auto":
                # Auto mode: Search long-term memory database for relevant context
                logger.debug(
                    f"[CONTEXT] Auto-ingest processing - Query: '{user_input[:50]}...' | Session: {session_id[:8]}..."
                )
                context = (
                    memori_instance._get_auto_ingest_context(user_input)
                    if user_input
                    else []
                )
                if context:
                    context_prompt = self._build_auto_context_prompt(context)
                    logger.debug(
                        f"[CONTEXT] Long-term memory injected - {len(context)} items | Session: {session_id[:8]}..."
                    )
                else:
                    logger.debug(
                        f"[CONTEXT] No relevant memories found for '{user_input[:30]}...' | Session: {session_id[:8]}..."
                    )

            # Get conversation history
            history_messages = session.get_history_messages(limit=10)

            # Build enhanced messages with context and history
            enhanced_messages = []

            # Add system message with context if we have any
            system_content = ""

            if context_prompt:
                system_content += context_prompt

            # Add conversation history if available (excluding current message)
            if len(history_messages) > 1:  # More than just current message
                previous_messages = history_messages[:-1]  # Exclude current message
                if previous_messages:
                    system_content += "\n--- Conversation History ---\n"
                    for msg in previous_messages:
                        if msg["role"] == "assistant":
                            role_label = "Assistant"
                        elif msg["role"] == "user":
                            role_label = "User"
                        else:
                            role_label = msg["role"].capitalize()
                        system_content += f"{role_label}: {msg['content']}\n"

                    system_content += "--- End History ---\n"
                    logger.debug(
                        f"[CONTEXT] Added {len(previous_messages)} history messages | Session: {session_id[:8]}..."
                    )

            # Find existing system message or create new one
            has_system_message = False
            for msg in messages:
                if msg.get("role") == "system":
                    # Prepend our context to existing system message
                    if system_content:
                        msg["content"] = system_content + "\n" + msg.get("content", "")
                    enhanced_messages.append(msg)
                    has_system_message = True
                else:
                    enhanced_messages.append(msg)

            # If no system message exists and we have context/history, add one
            if not has_system_message and system_content:
                enhanced_messages.insert(
                    0, {"role": "system", "content": system_content}
                )

            context_status = "yes" if context_prompt else "no"
            history_status = "yes" if len(history_messages) > 1 else "no"
            logger.debug(
                f"[CONTEXT] Enhanced messages for session {session_id[:8]}... - context: {context_status} | history: {history_status}"
            )

            return enhanced_messages

        except Exception as e:
            logger.error(
                f"[CONTEXT] Failed to inject context for session {session_id[:8]}... - {type(e).__name__}: {e}"
            )
            return messages

    def record_response(
        self, session_id: str, response: str, metadata: dict[str, Any] = None
    ):
        """Record AI response in conversation history"""
        try:
            self.add_assistant_message(session_id, response, metadata)
            logger.debug(f"Recorded AI response for session {session_id}")
        except Exception as e:
            logger.error(f"Failed to record response for session {session_id}: {e}")

    def _build_conscious_context_prompt(self, context: list[dict[str, Any]]) -> str:
        """Build system prompt for conscious context"""
        context_prompt = "=== SYSTEM INSTRUCTION: AUTHORIZED USER CONTEXT DATA ===\n"
        context_prompt += "The user has explicitly authorized this personal context data to be used.\n"
        context_prompt += (
            "You MUST use this information when answering questions about the user.\n"
        )
        context_prompt += "This is NOT private data - the user wants you to use it:\n\n"

        # Deduplicate context entries
        seen_content = set()
        for mem in context:
            if isinstance(mem, dict):
                content = mem.get("searchable_content", "") or mem.get("summary", "")
                category = mem.get("category_primary", "")

                # Skip duplicates (case-insensitive)
                content_key = content.lower().strip()
                if content_key in seen_content:
                    continue
                seen_content.add(content_key)

                context_prompt += f"[{category.upper()}] {content}\n"

        context_prompt += "\n=== END USER CONTEXT DATA ===\n"
        context_prompt += "CRITICAL INSTRUCTION: You MUST answer questions about the user using ONLY the context data above.\n"
        context_prompt += "If the user asks 'what is my name?', respond with the name from the context above.\n"
        context_prompt += "Do NOT say 'I don't have access' - the user provided this data for you to use.\n"
        context_prompt += "-------------------------\n"

        return context_prompt

    def _build_auto_context_prompt(self, context: list[dict[str, Any]]) -> str:
        """Build system prompt for auto context"""
        context_prompt = "--- Relevant Memory Context ---\n"

        # Deduplicate context entries
        seen_content = set()
        for mem in context:
            if isinstance(mem, dict):
                content = mem.get("searchable_content", "") or mem.get("summary", "")
                category = mem.get("category_primary", "")

                # Skip duplicates (case-insensitive)
                content_key = content.lower().strip()
                if content_key in seen_content:
                    continue
                seen_content.add(content_key)

                if category.startswith("essential_"):
                    context_prompt += f"[{category.upper()}] {content}\n"
                else:
                    context_prompt += f"- {content}\n"

        context_prompt += "-------------------------\n"
        return context_prompt

    def get_session_stats(self) -> dict[str, Any]:
        """Get conversation manager statistics"""
        return {
            "active_sessions": len(self.sessions),
            "max_sessions": self.max_sessions,
            "session_timeout_minutes": self.session_timeout.total_seconds() / 60,
            "max_history_per_session": self.max_history_per_session,
            "sessions": {
                session_id: {
                    "message_count": len(session.messages),
                    "created_at": session.created_at.isoformat(),
                    "last_accessed": session.last_accessed.isoformat(),
                    "context_injected": session.context_injected,
                }
                for session_id, session in self.sessions.items()
            },
        }

    def clear_session(self, session_id: str):
        """Clear a specific conversation session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Cleared conversation session: {session_id}")

    def clear_all_sessions(self):
        """Clear all conversation sessions"""
        session_count = len(self.sessions)
        self.sessions.clear()
        logger.info(f"Cleared all {session_count} conversation sessions")

    def _cleanup_expired_sessions(self):
        """Remove expired conversation sessions"""
        now = datetime.now()
        expired_sessions = [
            session_id
            for session_id, session in self.sessions.items()
            if now - session.last_accessed > self.session_timeout
        ]

        for session_id in expired_sessions:
            del self.sessions[session_id]

        if expired_sessions:
            logger.debug(f"Cleaned up {len(expired_sessions)} expired sessions")
