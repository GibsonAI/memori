"""
Chat history database queries
"""

from .base_queries import BaseQueries


class ChatQueries(BaseQueries):
    """Centralized chat history SQL queries"""

    def get_table_creation_queries(self) -> dict[str, str]:
        """Chat table creation queries"""
        from .base_queries import SchemaQueries

        return {"chat_history": SchemaQueries.TABLE_CREATION["chat_history"]}

    def get_index_creation_queries(self) -> dict[str, str]:
        """Chat index creation queries"""
        from .base_queries import SchemaQueries

        return {k: v for k, v in SchemaQueries.INDEX_CREATION.items() if "chat" in k}

    def get_trigger_creation_queries(self) -> dict[str, str]:
        """Chat trigger creation queries"""
        return {}  # No triggers for chat history currently

    # INSERT Queries
    INSERT_CHAT_HISTORY = """
        INSERT INTO chat_history (
            chat_id, user_input, ai_output, model, created_at,
            session_id, user_id, assistant_id, tokens_used, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    # SELECT Queries
    # NOTE: These queries now support multi-column filtering (user_id + assistant_id + session_id)
    # The calling code should pass None for optional filters (assistant_id, session_id)
    # and build WHERE clauses dynamically

    SELECT_CHAT_BY_ID = """
        SELECT * FROM chat_history
        WHERE chat_id = ? AND user_id = ?
    """

    SELECT_CHAT_BY_SESSION = """
        SELECT chat_id, user_input, ai_output, model, created_at, tokens_used
        FROM chat_history
        WHERE session_id = ? AND user_id = ?
        ORDER BY created_at ASC
    """

    SELECT_RECENT_CHATS = """
        SELECT chat_id, user_input, ai_output, model, created_at, tokens_used
        FROM chat_history
        WHERE user_id = ? AND created_at >= ?
        ORDER BY created_at DESC
        LIMIT ?
    """

    SELECT_CHATS_BY_MODEL = """
        SELECT chat_id, user_input, ai_output, created_at, tokens_used
        FROM chat_history
        WHERE user_id = ? AND model = ?
        ORDER BY created_at DESC
        LIMIT ?
    """

    SELECT_CHAT_STATISTICS = """
        SELECT
            COUNT(*) as total_chats,
            COUNT(DISTINCT session_id) as unique_sessions,
            COUNT(DISTINCT model) as unique_models,
            SUM(tokens_used) as total_tokens,
            AVG(tokens_used) as avg_tokens,
            MIN(created_at) as first_chat,
            MAX(created_at) as last_chat
        FROM chat_history
        WHERE user_id = ?
    """

    SELECT_CHATS_BY_DATE_RANGE = """
        SELECT chat_id, user_input, ai_output, model, created_at, tokens_used
        FROM chat_history
        WHERE user_id = ? AND created_at BETWEEN ? AND ?
        ORDER BY created_at DESC
        LIMIT ?
    """

    # UPDATE Queries
    UPDATE_CHAT_METADATA = """
        UPDATE chat_history
        SET metadata = ?
        WHERE chat_id = ? AND user_id = ?
    """

    # DELETE Queries
    DELETE_CHAT = """
        DELETE FROM chat_history
        WHERE chat_id = ? AND user_id = ?
    """

    DELETE_OLD_CHATS = """
        DELETE FROM chat_history
        WHERE user_id = ? AND created_at < ?
    """

    DELETE_CHATS_BY_SESSION = """
        DELETE FROM chat_history
        WHERE session_id = ? AND user_id = ?
    """

    # ANALYTICS Queries
    GET_CHAT_VOLUME_BY_DATE = """
        SELECT
            DATE(created_at) as chat_date,
            COUNT(*) as chat_count,
            SUM(tokens_used) as tokens_used
        FROM chat_history
        WHERE user_id = ? AND created_at >= ?
        GROUP BY DATE(created_at)
        ORDER BY chat_date DESC
    """

    GET_MODEL_USAGE_STATS = """
        SELECT
            model,
            COUNT(*) as usage_count,
            SUM(tokens_used) as total_tokens,
            AVG(tokens_used) as avg_tokens
        FROM chat_history
        WHERE user_id = ?
        GROUP BY model
        ORDER BY usage_count DESC
    """

    GET_SESSION_STATS = """
        SELECT
            session_id,
            COUNT(*) as message_count,
            MIN(created_at) as session_start,
            MAX(created_at) as session_end,
            SUM(tokens_used) as total_tokens
        FROM chat_history
        WHERE user_id = ?
        GROUP BY session_id
        ORDER BY session_start DESC
        LIMIT ?
    """

    SEARCH_CHAT_CONTENT = """
        SELECT chat_id, user_input, ai_output, model, created_at
        FROM chat_history
        WHERE user_id = ? AND (
            user_input LIKE ? OR
            ai_output LIKE ?
        )
        ORDER BY created_at DESC
        LIMIT ?
    """
