"""
Google GenAI Integration - Automatic Interception System

This module provides automatic interception of Google GenAI API calls when Memori is enabled.
Users can import and use the standard Google GenAI client normally, and Memori will automatically
record conversations when enabled.

Usage:
    import google.generativeai as genai
    from memori import Memori

    # Initialize Memori and enable it
    genai_memory = Memori(
        database_connect="sqlite:///genai_memory.db",
        conscious_ingest=True,
        verbose=True,
    )
    genai_memory.enable()

    # Use standard Google GenAI client - automatically intercepted!
    genai.configure(api_key="your-api-key")
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content("Hello!")
    # Conversation is automatically recorded to Memori
"""

from loguru import logger

# Global registry of enabled Memori instances
_enabled_memori_instances = []


class GoogleGenAIInterceptor:
    """
    Automatic Google GenAI interception system that patches the Google GenAI module
    to automatically record conversations when Memori instances are enabled.
    """

    _original_methods = {}
    _is_patched = False

    @classmethod
    def patch_genai(cls):
        """Patch Google GenAI module to intercept API calls."""
        if cls._is_patched:
            return

        try:
            import google.generativeai as genai

            # Patch GenerativeModel class
            if hasattr(genai, "GenerativeModel"):
                cls._patch_generative_model(genai.GenerativeModel)

            # Patch ChatSession class if accessible
            try:
                from google.generativeai.generative_models import ChatSession
                cls._patch_chat_session(ChatSession)
            except (ImportError, AttributeError):
                logger.debug("ChatSession class not found for patching")

            cls._is_patched = True
            logger.debug("Google GenAI module patched for automatic interception")

        except ImportError:
            logger.warning("Google GenAI not available - skipping patch")
        except Exception as e:
            logger.error(f"Failed to patch Google GenAI module: {e}")

    @classmethod
    def _patch_generative_model(cls, model_class):
        """Patch GenerativeModel class for generate_content methods."""
        
        # Patch synchronous generate_content
        if hasattr(model_class, "generate_content"):
            original_key = "generate_content_sync"
            if original_key not in cls._original_methods:
                cls._original_methods[original_key] = model_class.generate_content

            original_method = cls._original_methods[original_key]

            def patched_generate_content(self, contents, **kwargs):
                # Inject context before generating
                modified_contents = cls._inject_context_for_enabled_instances(
                    contents, self, kwargs
                )

                # Call original method
                result = original_method(self, modified_contents, **kwargs)

                # Record conversation for enabled instances
                cls._record_conversation_for_enabled_instances(
                    self, modified_contents, result, kwargs, "generate_content"
                )

                return result

            model_class.generate_content = patched_generate_content

        # Patch asynchronous generate_content_async
        if hasattr(model_class, "generate_content_async"):
            original_key = "generate_content_async"
            if original_key not in cls._original_methods:
                cls._original_methods[original_key] = model_class.generate_content_async

            original_method = cls._original_methods[original_key]

            async def patched_generate_content_async(self, contents, **kwargs):
                # Inject context before generating
                modified_contents = cls._inject_context_for_enabled_instances(
                    contents, self, kwargs
                )

                # Call original method
                result = await original_method(self, modified_contents, **kwargs)

                # Record conversation for enabled instances
                cls._record_conversation_for_enabled_instances(
                    self, modified_contents, result, kwargs, "generate_content_async"
                )

                return result

            model_class.generate_content_async = patched_generate_content_async

        # Patch start_chat method
        if hasattr(model_class, "start_chat"):
            original_key = "start_chat"
            if original_key not in cls._original_methods:
                cls._original_methods[original_key] = model_class.start_chat

            original_method = cls._original_methods[original_key]

            def patched_start_chat(self, **kwargs):
                # Get chat history if provided
                history = kwargs.get("history", [])
                
                # Inject context into history
                if history and _enabled_memori_instances:
                    modified_history = cls._inject_context_into_history(history)
                    kwargs["history"] = modified_history

                # Call original method
                chat = original_method(self, **kwargs)

                return chat

            model_class.start_chat = patched_start_chat

    @classmethod
    def _patch_chat_session(cls, chat_class):
        """Patch ChatSession class for send_message methods."""
        
        # Patch synchronous send_message
        if hasattr(chat_class, "send_message"):
            original_key = "chat_send_message_sync"
            if original_key not in cls._original_methods:
                cls._original_methods[original_key] = chat_class.send_message

            original_method = cls._original_methods[original_key]

            def patched_send_message(self, content, **kwargs):
                # Inject context if this is the first message or has history
                modified_content = cls._inject_context_for_chat_message(
                    content, self, kwargs
                )

                # Call original method
                result = original_method(self, modified_content, **kwargs)

                # Record conversation
                cls._record_chat_message_for_enabled_instances(
                    self, modified_content, result, kwargs, "send_message"
                )

                return result

            chat_class.send_message = patched_send_message

        # Patch asynchronous send_message_async
        if hasattr(chat_class, "send_message_async"):
            original_key = "chat_send_message_async"
            if original_key not in cls._original_methods:
                cls._original_methods[original_key] = chat_class.send_message_async

            original_method = cls._original_methods[original_key]

            async def patched_send_message_async(self, content, **kwargs):
                # Inject context if this is the first message or has history
                modified_content = cls._inject_context_for_chat_message(
                    content, self, kwargs
                )

                # Call original method
                result = await original_method(self, modified_content, **kwargs)

                # Record conversation
                cls._record_chat_message_for_enabled_instances(
                    self, modified_content, result, kwargs, "send_message_async"
                )

                return result

            chat_class.send_message_async = patched_send_message_async

    @classmethod
    def _inject_context_for_enabled_instances(cls, contents, model, kwargs):
        """Inject context for all enabled Memori instances with conscious/auto ingest."""
        for memori_instance in _enabled_memori_instances:
            if memori_instance.is_enabled and (
                memori_instance.conscious_ingest or memori_instance.auto_ingest
            ):
                try:
                    # Convert contents to messages format
                    messages = cls._contents_to_messages(contents)
                    
                    if messages:
                        logger.debug(
                            f"GenAI: Injecting context with {len(messages)} messages"
                        )
                        
                        # Use Memori's context injection (assuming it has a GenAI variant)
                        updated_data = memori_instance._inject_genai_context(
                            {"messages": messages}
                        )

                        if updated_data.get("messages"):
                            # Convert back to GenAI format
                            contents = cls._messages_to_contents(
                                updated_data["messages"]
                            )
                            logger.debug("GenAI: Successfully injected context")

                except Exception as e:
                    logger.error(f"Context injection failed for GenAI: {e}")

        return contents

    @classmethod
    def _inject_context_into_history(cls, history):
        """Inject context into chat history."""
        for memori_instance in _enabled_memori_instances:
            if memori_instance.is_enabled and (
                memori_instance.conscious_ingest or memori_instance.auto_ingest
            ):
                try:
                    # Convert history to messages format
                    messages = []
                    for msg in history:
                        role = msg.get("role", "user")
                        parts = msg.get("parts", [])
                        content = " ".join([str(part) for part in parts])
                        messages.append({"role": role, "content": content})

                    if messages:
                        updated_data = memori_instance._inject_genai_context(
                            {"messages": messages}
                        )

                        if updated_data.get("messages"):
                            # Convert back to GenAI history format
                            new_history = []
                            for msg in updated_data["messages"]:
                                new_history.append({
                                    "role": msg.get("role", "user"),
                                    "parts": [msg.get("content", "")]
                                })
                            return new_history

                except Exception as e:
                    logger.error(f"History context injection failed: {e}")

        return history

    @classmethod
    def _inject_context_for_chat_message(cls, content, chat, kwargs):
        """Inject context for chat message."""
        for memori_instance in _enabled_memori_instances:
            if memori_instance.is_enabled and (
                memori_instance.conscious_ingest or memori_instance.auto_ingest
            ):
                try:
                    # Build message history from chat
                    messages = []
                    if hasattr(chat, "history"):
                        for msg in chat.history:
                            role = msg.role if hasattr(msg, "role") else "user"
                            parts = msg.parts if hasattr(msg, "parts") else []
                            msg_content = " ".join([str(part.text) if hasattr(part, "text") else str(part) for part in parts])
                            messages.append({"role": role, "content": msg_content})

                    # Add current message
                    messages.append({"role": "user", "content": str(content)})

                    updated_data = memori_instance._inject_genai_context(
                        {"messages": messages}
                    )

                    if updated_data.get("messages"):
                        # Return modified content (last message)
                        return updated_data["messages"][-1].get("content", content)

                except Exception as e:
                    logger.error(f"Chat context injection failed: {e}")

        return content

    @classmethod
    def _is_internal_agent_call(cls, contents):
        """Check if this is an internal agent processing call that should not be recorded."""
        try:
            content_str = str(contents)
            
            # Check for specific internal agent processing patterns
            internal_patterns = [
                "Process this conversation for enhanced memory storage:",
                "Enhanced memory processing:",
                "Memory classification:",
                "Search for relevant memories:",
                "Analyze conversation for:",
                "Extract entities from:",
                "Categorize the following conversation:",
                "INTERNAL_MEMORY_PROCESSING:",
                "AGENT_PROCESSING_MODE:",
                "MEMORY_AGENT_TASK:",
            ]

            for pattern in internal_patterns:
                if pattern in content_str:
                    return True

            return False

        except Exception as e:
            logger.debug(f"Failed to check internal agent call: {e}")
            return False

    @classmethod
    def _record_conversation_for_enabled_instances(
        cls, model, contents, response, kwargs, method_name
    ):
        """Record conversation for all enabled Memori instances."""
        for memori_instance in _enabled_memori_instances:
            if memori_instance.is_enabled:
                try:
                    # Check if this is an internal agent processing call
                    if cls._is_internal_agent_call(contents):
                        logger.debug("Skipping internal agent call (detected pattern match)")
                        continue

                    # Extract user input
                    user_input = cls._extract_user_input(contents)
                    
                    # Extract AI output
                    ai_output = cls._extract_ai_output(response)

                    # Get model name
                    model_name = getattr(model, "model_name", "gemini-pro")

                    # Calculate tokens if available
                    tokens_used = 0
                    if hasattr(response, "usage_metadata"):
                        usage = response.usage_metadata
                        tokens_used = (
                            getattr(usage, "total_token_count", 0) or
                            getattr(usage, "prompt_token_count", 0) + 
                            getattr(usage, "candidates_token_count", 0)
                        )

                    # Debug logging
                    if user_input:
                        logger.debug(
                            f"Recording GenAI conversation: '{user_input[:50]}...'"
                        )

                    # Record conversation
                    memori_instance.record_conversation(
                        user_input=user_input,
                        ai_output=ai_output,
                        model=model_name,
                        metadata={
                            "integration": "genai_auto_intercept",
                            "method": method_name,
                            "tokens_used": tokens_used,
                            "auto_recorded": True,
                            **cls._extract_additional_metadata(response, kwargs),
                        },
                    )

                except Exception as e:
                    logger.error(f"Failed to record GenAI conversation: {e}")

    @classmethod
    def _record_chat_message_for_enabled_instances(
        cls, chat, content, response, kwargs, method_name
    ):
        """Record chat message for all enabled Memori instances."""
        for memori_instance in _enabled_memori_instances:
            if memori_instance.is_enabled:
                try:
                    # Check if internal call
                    if cls._is_internal_agent_call(content):
                        logger.debug("Skipping internal agent call")
                        continue

                    # Extract user input and AI output
                    user_input = str(content)
                    ai_output = cls._extract_ai_output(response)

                    # Get model name
                    model_name = getattr(chat, "model", "gemini-pro")
                    if hasattr(model_name, "model_name"):
                        model_name = model_name.model_name

                    # Calculate tokens
                    tokens_used = 0
                    if hasattr(response, "usage_metadata"):
                        usage = response.usage_metadata
                        tokens_used = (
                            getattr(usage, "total_token_count", 0) or
                            getattr(usage, "prompt_token_count", 0) + 
                            getattr(usage, "candidates_token_count", 0)
                        )

                    logger.debug(f"Recording chat message: '{user_input[:50]}...'")

                    # Record conversation
                    memori_instance.record_conversation(
                        user_input=user_input,
                        ai_output=ai_output,
                        model=model_name,
                        metadata={
                            "integration": "genai_auto_intercept",
                            "method": method_name,
                            "chat_session": True,
                            "tokens_used": tokens_used,
                            "auto_recorded": True,
                            **cls._extract_additional_metadata(response, kwargs),
                        },
                    )

                except Exception as e:
                    logger.error(f"Failed to record chat message: {e}")

    @classmethod
    def _contents_to_messages(cls, contents):
        """Convert GenAI contents to standard messages format."""
        messages = []
        
        if isinstance(contents, str):
            messages.append({"role": "user", "content": contents})
        elif isinstance(contents, list):
            for item in contents:
                if isinstance(item, str):
                    messages.append({"role": "user", "content": item})
                elif isinstance(item, dict):
                    role = item.get("role", "user")
                    parts = item.get("parts", [])
                    content = " ".join([str(part) for part in parts])
                    messages.append({"role": role, "content": content})
        elif hasattr(contents, "parts"):
            # Single content object
            parts = contents.parts
            content = " ".join([str(part) for part in parts])
            messages.append({"role": "user", "content": content})
        
        return messages

    @classmethod
    def _messages_to_contents(cls, messages):
        """Convert standard messages format to GenAI contents."""
        if len(messages) == 1:
            return messages[0].get("content", "")
        
        contents = []
        for msg in messages:
            contents.append({
                "role": msg.get("role", "user"),
                "parts": [msg.get("content", "")]
            })
        
        return contents

    @classmethod
    def _extract_user_input(cls, contents):
        """Extract user input from contents."""
        if isinstance(contents, str):
            return contents
        elif isinstance(contents, list):
            # Get last user message
            for item in reversed(contents):
                if isinstance(item, str):
                    return item
                elif isinstance(item, dict) and item.get("role") == "user":
                    parts = item.get("parts", [])
                    return " ".join([str(part) for part in parts])
        elif hasattr(contents, "parts"):
            parts = contents.parts
            return " ".join([str(part) for part in parts])
        
        return str(contents)

    @classmethod
    def _extract_ai_output(cls, response):
        """Extract AI output from response."""
        try:
            if hasattr(response, "text"):
                return response.text
            elif hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content"):
                    content = candidate.content
                    if hasattr(content, "parts"):
                        parts = content.parts
                        return " ".join([str(part.text) if hasattr(part, "text") else str(part) for part in parts])
            
            return str(response)
        except Exception as e:
            logger.debug(f"Failed to extract AI output: {e}")
            return ""

    @classmethod
    def _extract_additional_metadata(cls, response, kwargs):
        """Extract additional metadata from response and kwargs."""
        metadata = {}
        
        try:
            # Safety ratings
            if hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "safety_ratings"):
                    metadata["safety_ratings"] = [
                        {
                            "category": str(rating.category),
                            "probability": str(rating.probability)
                        }
                        for rating in candidate.safety_ratings
                    ]
                
                # Finish reason
                if hasattr(candidate, "finish_reason"):
                    metadata["finish_reason"] = str(candidate.finish_reason)
            
            # Generation config from kwargs
            if "generation_config" in kwargs:
                metadata["generation_config"] = str(kwargs["generation_config"])
            
            # Safety settings from kwargs
            if "safety_settings" in kwargs:
                metadata["safety_settings"] = str(kwargs["safety_settings"])
        
        except Exception as e:
            logger.debug(f"Failed to extract additional metadata: {e}")
        
        return metadata

    @classmethod
    def unpatch_genai(cls):
        """Restore original Google GenAI module methods."""
        if not cls._is_patched:
            return

        try:
            import google.generativeai as genai

            # Restore GenerativeModel methods
            if "generate_content_sync" in cls._original_methods:
                genai.GenerativeModel.generate_content = cls._original_methods[
                    "generate_content_sync"
                ]

            if "generate_content_async" in cls._original_methods:
                genai.GenerativeModel.generate_content_async = cls._original_methods[
                    "generate_content_async"
                ]

            if "start_chat" in cls._original_methods:
                genai.GenerativeModel.start_chat = cls._original_methods["start_chat"]

            # Restore ChatSession methods
            try:
                from google.generativeai.generative_models import ChatSession
                
                if "chat_send_message_sync" in cls._original_methods:
                    ChatSession.send_message = cls._original_methods[
                        "chat_send_message_sync"
                    ]

                if "chat_send_message_async" in cls._original_methods:
                    ChatSession.send_message_async = cls._original_methods[
                        "chat_send_message_async"
                    ]
            except (ImportError, AttributeError):
                pass

            cls._is_patched = False
            cls._original_methods.clear()
            logger.debug("Google GenAI module patches removed")

        except ImportError:
            pass  # GenAI not available
        except Exception as e:
            logger.error(f"Failed to unpatch Google GenAI module: {e}")


def register_memori_instance(memori_instance):
    """
    Register a Memori instance for automatic Google GenAI interception.

    Args:
        memori_instance: Memori instance to register
    """
    global _enabled_memori_instances

    if memori_instance not in _enabled_memori_instances:
        _enabled_memori_instances.append(memori_instance)
        logger.debug("Registered Memori instance for GenAI interception")

    # Ensure GenAI is patched
    GoogleGenAIInterceptor.patch_genai()


def unregister_memori_instance(memori_instance):
    """
    Unregister a Memori instance from automatic Google GenAI interception.

    Args:
        memori_instance: Memori instance to unregister
    """
    global _enabled_memori_instances

    if memori_instance in _enabled_memori_instances:
        _enabled_memori_instances.remove(memori_instance)
        logger.debug("Unregistered Memori instance from GenAI interception")

    # If no more instances, unpatch GenAI
    if not _enabled_memori_instances:
        GoogleGenAIInterceptor.unpatch_genai()


def get_enabled_instances():
    """Get list of currently enabled Memori instances."""
    return _enabled_memori_instances.copy()


def is_genai_patched():
    """Check if Google GenAI module is currently patched."""
    return GoogleGenAIInterceptor._is_patched


def create_genai_model(memori_instance, model_name="gemini-2.5-flash", **kwargs):
    """
    Create a Google GenAI model that automatically records to memori.

    This is the recommended way to create GenAI models with memori integration.

    Args:
        memori_instance: Memori instance to record conversations to
        model_name: Name of the model to use (default: "gemini-pro")
        **kwargs: Additional arguments for GenerativeModel

    Returns:
        GenerativeModel instance with automatic recording
    """
    try:
        import google.generativeai as genai

        # Register the memori instance for automatic interception
        register_memori_instance(memori_instance)

        # Create standard GenAI model - it will be automatically intercepted
        model = genai.GenerativeModel(model_name, **kwargs)

        logger.info(f"Created GenAI model '{model_name}' with automatic memori recording")
        return model

    except ImportError as e:
        logger.error(f"Failed to import Google GenAI: {e}")
        raise ImportError(
            "Google GenAI package required: pip install google-generativeai"
        ) from e
    except Exception as e:
        logger.error(f"Failed to create GenAI model: {e}")
        raise