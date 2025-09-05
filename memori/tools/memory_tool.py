"""
Memory Tool - A tool/function for manual integration with any LLM library
"""

import json
from typing import Any, Callable, Dict

from loguru import logger

from ..core.memory import Memori


class MemoryTool:
    """
    A tool that can be attached to any LLM library for using Memori functionality.

    This provides a standardized interface for:
    1. Recording conversations manually
    2. Retrieving relevant context
    3. Getting memory statistics
    """

    def __init__(self, memori_instance: Memori):
        """
        Initialize MemoryTool with a Memori instance

        Args:
            memori_instance: The Memori instance to use for memory operations
        """
        self.memori = memori_instance
        self.tool_name = "memori_memory"
        self.description = "Access and manage AI conversation memory"

    def get_tool_schema(self) -> Dict[str, Any]:
        """
        Get the tool schema for function calling in LLMs

        Returns:
            Tool schema compatible with OpenAI function calling format
        """
        return {
            "name": self.tool_name,
            "description": "Search and retrieve information from conversation memory",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query to find relevant memories, conversations, or personal information about the user",
                    },
                },
                "required": ["query"],
            },
        }

    def execute(self, query: str = None, **kwargs) -> str:
        """
        Execute a memory search/retrieve action

        Args:
            query: Search query string
            **kwargs: Additional parameters for backward compatibility

        Returns:
            String result of the memory search
        """
        # Accept query as direct parameter or from kwargs
        if query is None:
            query = kwargs.get("query", "")

        if not query:
            return "Error: Query is required for memory search"

        # Use retrieval agent for intelligent search
        try:
            from ..agents.retrieval_agent import MemorySearchEngine

            # Create search engine if not already initialized
            if not hasattr(self, "_search_engine"):
                if hasattr(self.memori, "provider_config") and self.memori.provider_config:
                    self._search_engine = MemorySearchEngine(provider_config=self.memori.provider_config)
                else:
                    self._search_engine = MemorySearchEngine()

            # Execute search using retrieval agent
            results = self._search_engine.execute_search(
                query=query,
                db_manager=self.memori.db_manager,
                namespace=self.memori.namespace,
                limit=5,
            )

            if not results:
                return f"No relevant memories found for query: '{query}'"

            # Format results as a readable string
            formatted_output = f"🔍 Memory Search Results for: '{query}'\n\n"

            for i, result in enumerate(results, 1):
                try:
                    # Try to parse processed data for better formatting
                    if "processed_data" in result:
                        import json

                        if isinstance(result["processed_data"], dict):
                            processed_data = result["processed_data"]
                        elif isinstance(result["processed_data"], str):
                            processed_data = json.loads(result["processed_data"])
                        else:
                            raise ValueError("Error, wrong 'processed_data' format")
                            
                        summary = processed_data.get("summary", "")
                        category = processed_data.get("category", {}).get(
                            "primary_category", ""
                        )
                    else:
                        summary = result.get(
                            "summary",
                            result.get("searchable_content", "")[:100] + "...",
                        )
                        category = result.get("category_primary", "unknown")

                    importance = result.get("importance_score", 0.0)
                    created_at = result.get("created_at", "")

                    formatted_output += f"{i}. [{category.upper()}] {summary}\n"
                    formatted_output += (
                        f"   📊 Importance: {importance:.2f} | 📅 {created_at}\n"
                    )

                    if result.get("search_reasoning"):
                        formatted_output += f"   🎯 {result['search_reasoning']}\n"

                    formatted_output += "\n"

                except Exception:
                    # Fallback formatting
                    content = result.get(
                        "searchable_content", "Memory content available"
                    )[:100]
                    formatted_output += f"{i}. {content}...\n\n"

            return formatted_output.strip()

        except ImportError:
            # Fallback to original search methods if retrieval agent is not available
            # Try different search strategies based on query content
            if any(word in query.lower() for word in ["name", "who am i", "about me"]):
                # Personal information query - try essential conversations first
                essential_result = self._get_essential_conversations()
                if essential_result.get("count", 0) > 0:
                    return self._format_dict_to_string(essential_result)

            # General search
            search_result = self._search_memories(query=query, limit=10)
            if search_result.get("results_count", 0) > 0:
                return self._format_dict_to_string(search_result)

            # Fallback to context retrieval
            context_result = self._retrieve_context(query=query, limit=5)
            return self._format_dict_to_string(context_result)

        except Exception as e:
            return f"Error searching memories: {str(e)}"

    def _format_dict_to_string(self, result_dict: Dict[str, Any]) -> str:
        """Helper method to format dictionary results to readable strings"""
        if result_dict.get("error"):
            return f"Error: {result_dict['error']}"

        if "essential_conversations" in result_dict:
            conversations = result_dict.get("essential_conversations", [])
            if not conversations:
                return "No essential conversations found in memory."

            output = f"🧠 Essential Information ({len(conversations)} items):\n\n"
            for i, conv in enumerate(conversations, 1):
                category = conv.get("category", "").title()
                summary = conv.get("summary", "")
                importance = conv.get("importance", 0.0)
                output += f"{i}. [{category}] {summary}\n"
                output += f"   📊 Importance: {importance:.2f}\n\n"
            return output.strip()

        elif "results" in result_dict:
            results = result_dict.get("results", [])
            if not results:
                return "No memories found for your search."

            output = f"🔍 Memory Search Results ({len(results)} found):\n\n"
            for i, result in enumerate(results, 1):
                content = result.get("searchable_content", "Memory content")[:100]
                output += f"{i}. {content}...\n\n"
            return output.strip()

        elif "context" in result_dict:
            context_items = result_dict.get("context", [])
            if not context_items:
                return "No relevant context found in memory."

            output = f"📚 Relevant Context ({len(context_items)} items):\n\n"
            for i, item in enumerate(context_items, 1):
                content = item.get("content", "")[:100]
                category = item.get("category", "unknown")
                output += f"{i}. [{category.upper()}] {content}...\n\n"
            return output.strip()

        else:
            # Generic formatting
            message = result_dict.get("message", "Memory search completed")
            return message

    def _record_conversation(self, **kwargs) -> Dict[str, Any]:
        """Record a conversation"""
        try:
            user_input = kwargs.get("user_input", "")
            ai_output = kwargs.get("ai_output", "")
            model = kwargs.get("model", "unknown")

            if not user_input or not ai_output:
                return {
                    "error": "Both user_input and ai_output are required for recording"
                }

            chat_id = self.memori.record_conversation(
                user_input=user_input,
                ai_output=ai_output,
                model=model,
                metadata={"tool": "memory_tool", "manual_record": True},
            )

            return {
                "success": True,
                "chat_id": chat_id,
                "message": "Conversation recorded successfully",
            }

        except Exception as e:
            logger.error(f"Failed to record conversation: {e}")
            return {"error": f"Failed to record conversation: {str(e)}"}

    def _retrieve_context(self, **kwargs) -> Dict[str, Any]:
        """Retrieve relevant context for a query"""
        try:
            query = kwargs.get("query", "")
            limit = kwargs.get("limit", 5)

            if not query:
                return {"error": "Query is required for retrieval"}

            context_items = self.memori.retrieve_context(query, limit)

            # Format context items for easier consumption
            formatted_context = []
            for item in context_items:
                formatted_context.append(
                    {
                        "content": item.get("content", ""),
                        "category": item.get("category", ""),
                        "importance": item.get("importance_score", 0),
                        "created_at": item.get("created_at", ""),
                        "memory_type": item.get("memory_type", ""),
                    }
                )

            return {
                "success": True,
                "query": query,
                "context_count": len(formatted_context),
                "context": formatted_context,
                "message": f"Retrieved {len(formatted_context)} relevant memories",
            }

        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return {"error": f"Failed to retrieve context: {str(e)}"}

    def _search_memories(self, **kwargs) -> Dict[str, Any]:
        """Search memories by content"""
        try:
            query = kwargs.get("query", "")
            limit = kwargs.get("limit", 10)

            if not query:
                return {"error": "Query is required for search"}

            search_results = self.memori.db_manager.search_memories(
                query=query, namespace=self.memori.namespace, limit=limit
            )

            return {
                "success": True,
                "query": query,
                "results_count": len(search_results),
                "results": search_results,
                "message": f"Found {len(search_results)} matching memories",
            }

        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return {"error": f"Failed to search memories: {str(e)}"}

    def _get_stats(self, **kwargs) -> Dict[str, Any]:
        """Get memory and integration statistics"""
        try:
            memory_stats = self.memori.get_memory_stats()
            integration_stats = self.memori.get_integration_stats()

            return {
                "success": True,
                "memory_stats": memory_stats,
                "integration_stats": integration_stats,
                "namespace": self.memori.namespace,
                "session_id": self.memori.session_id,
                "enabled": self.memori.is_enabled,
            }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": f"Failed to get stats: {str(e)}"}

    def _get_essential_conversations(self, **kwargs) -> Dict[str, Any]:
        """Get essential conversations from short-term memory"""
        try:
            limit = kwargs.get("limit", 10)

            if hasattr(self.memori, "get_essential_conversations"):
                essential_conversations = self.memori.get_essential_conversations(limit)

                # Format for better readability
                formatted_conversations = []
                for conv in essential_conversations:
                    formatted_conversations.append(
                        {
                            "summary": conv.get("summary", ""),
                            "category": conv.get("category_primary", "").replace(
                                "essential_", ""
                            ),
                            "importance": conv.get("importance_score", 0),
                            "created_at": conv.get("created_at", ""),
                            "content": conv.get("searchable_content", ""),
                        }
                    )

                return {
                    "success": True,
                    "essential_conversations": formatted_conversations,
                    "count": len(formatted_conversations),
                    "message": f"Retrieved {len(formatted_conversations)} essential conversations from short-term memory",
                }
            else:
                return {"error": "Essential conversations feature not available"}

        except Exception as e:
            logger.error(f"Failed to get essential conversations: {e}")
            return {"error": f"Failed to get essential conversations: {str(e)}"}

    def _trigger_analysis(self, **kwargs) -> Dict[str, Any]:
        """Trigger conscious agent analysis"""
        try:
            if hasattr(self.memori, "trigger_conscious_analysis"):
                self.memori.trigger_conscious_analysis()
                return {
                    "success": True,
                    "message": "Conscious agent analysis triggered successfully. This will analyze memory patterns and update essential conversations in short-term memory.",
                }
            else:
                return {"error": "Conscious analysis feature not available"}

        except Exception as e:
            logger.error(f"Failed to trigger analysis: {e}")
            return {"error": f"Failed to trigger analysis: {str(e)}"}


# Helper function to create a tool instance
def create_memory_tool(memori_instance: Memori) -> MemoryTool:
    """
    Create a MemoryTool instance

    Args:
        memori_instance: The Memori instance to use

    Returns:
        MemoryTool instance
    """
    return MemoryTool(memori_instance)


# Function calling interface
def memori_tool_function(memori_instance: Memori, query: str = None, **kwargs) -> str:
    """
    Direct function interface for memory operations

    This can be used as a function call in LLM libraries that support function calling.

    Args:
        memori_instance: The Memori instance to use
        query: Search query string
        **kwargs: Additional parameters for backward compatibility

    Returns:
        String result of the memory operation
    """
    tool = MemoryTool(memori_instance)
    return tool.execute(query=query, **kwargs)


# Decorator for automatic conversation recording
def record_conversation(memori_instance: Memori):
    """
    Decorator to automatically record LLM conversations

    Args:
        memori_instance: The Memori instance to use for recording

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Call the original function
            result = func(*args, **kwargs)

            try:
                # Try to extract conversation details from common patterns
                if hasattr(result, "choices") and result.choices:
                    # OpenAI-style response
                    ai_output = result.choices[0].message.content

                    # Try to find user input in kwargs
                    user_input = ""
                    if "messages" in kwargs:
                        for msg in reversed(kwargs["messages"]):
                            if msg.get("role") == "user":
                                user_input = msg.get("content", "")
                                break

                    model = kwargs.get("model", "unknown")

                    if user_input and ai_output:
                        memori_instance.record_conversation(
                            user_input=user_input,
                            ai_output=ai_output,
                            model=model,
                            metadata={
                                "decorator": "record_conversation",
                                "auto_recorded": True,
                            },
                        )

            except Exception as e:
                logger.error(f"Failed to auto-record conversation: {e}")

            return result

        return wrapper

    return decorator


def create_memory_search_tool(memori_instance: Memori):
    """
    Create memory search tool for LLM function calling (v1.0 architecture)

    This creates a search function compatible with OpenAI function calling
    that uses SQL-based memory retrieval.

    Args:
        memori_instance: The Memori instance to search

    Returns:
        Memory search function for LLM tool use
    """

    def memory_search(query: str, max_results: int = 5) -> str:
        """
        Search through stored memories for relevant information

        Args:
            query: Search query for memories
            max_results: Maximum number of results to return

        Returns:
            Formatted string with search results
        """
        try:
            # Use the SQL-based search from the database manager
            results = memori_instance.db_manager.search_memories(
                query=query, namespace=memori_instance.namespace, limit=max_results
            )

            if not results:
                return f"No relevant memories found for query: '{query}'"

            # Format results according to v1.0 structure
            formatted_results = []
            for result in results:
                try:
                    # Parse the ProcessedMemory JSON
                    memory_data = json.loads(result["processed_data"])

                    formatted_result = {
                        "summary": memory_data.get("summary", ""),
                        "category": memory_data.get("category", {}).get(
                            "primary_category", ""
                        ),
                        "importance_score": result.get("importance_score", 0.0),
                        "created_at": result.get("created_at", ""),
                        "entities": memory_data.get("entities", {}),
                        "confidence": memory_data.get("category", {}).get(
                            "confidence_score", 0.0
                        ),
                        "searchable_content": result.get("searchable_content", ""),
                        "retention_type": memory_data.get("importance", {}).get(
                            "retention_type", "short_term"
                        ),
                    }
                    formatted_results.append(formatted_result)

                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing memory data: {e}")
                    # Fallback to basic result structure
                    formatted_results.append(
                        {
                            "summary": result.get(
                                "summary", "Memory content available"
                            ),
                            "category": result.get("category_primary", "unknown"),
                            "importance_score": result.get("importance_score", 0.0),
                            "created_at": result.get("created_at", ""),
                        }
                    )

            # Format as readable string instead of JSON
            output = f"🔍 Memory Search Results for: '{query}' ({len(formatted_results)} found)\n\n"

            for i, result in enumerate(formatted_results, 1):
                summary = result.get("summary", "Memory content available")
                category = result.get("category", "unknown")
                importance = result.get("importance_score", 0.0)
                created_at = result.get("created_at", "")

                output += f"{i}. [{category.upper()}] {summary}\n"
                output += f"   📊 Importance: {importance:.2f} | 📅 {created_at}\n\n"

            return output.strip()

        except Exception as e:
            logger.error(f"Memory search error: {e}")
            return f"Error searching memories: {str(e)}"

    return memory_search
