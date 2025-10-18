"""
OpenAI Integration - Automatic Interception System

This module provides automatic interception of OpenAI API calls when Memori is enabled.
Users can import and use the standard OpenAI client normally, and Memori will automatically
record conversations when enabled.

Usage:
    from openai import OpenAI
    from memori import Memori

    # Initialize Memori and enable it
    openai_memory = Memori(
        database_connect="sqlite:///openai_memory.db",
        conscious_ingest=True,
        verbose=True,
    )
    openai_memory.enable()

    # Use standard OpenAI client - automatically intercepted!
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello!"}]
    )
    # Conversation is automatically recorded to Memori
"""

import inspect
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from loguru import logger

# Global registry of enabled Memori instances
_enabled_memori_instances = []


_current_memori_instance: ContextVar | None = None
_recording_suppressed: ContextVar | None = None


def _get_current_instance_var() -> ContextVar:
    global _current_memori_instance
    if _current_memori_instance is None:
        _current_memori_instance = ContextVar("memori_current_instance", default=None)
    return _current_memori_instance


def _get_recording_suppressed_var() -> ContextVar:
    global _recording_suppressed
    if _recording_suppressed is None:
        _recording_suppressed = ContextVar("memori_recording_suppressed", default=False)
    return _recording_suppressed


def get_current_memori_instance():
    """Return the Memori instance currently bound to interception context."""
    return _get_current_instance_var().get()


def set_current_memori_instance(memori_instance):
    """Set the active Memori instance for the current context."""
    if memori_instance is None:
        token = _get_current_instance_var().set(None)
        return token
    return _get_current_instance_var().set(memori_instance)


@contextmanager
def activate_memori_instance(memori_instance) -> Iterator[None]:
    """Context manager that temporarily sets the current Memori instance."""
    token = set_current_memori_instance(memori_instance)
    try:
        yield
    finally:
        _get_current_instance_var().reset(token)


@contextmanager
def suppress_auto_recording() -> Iterator[None]:
    """Temporarily disable automatic recording for the current context."""
    var = _get_recording_suppressed_var()
    token = var.set(True)
    try:
        yield
    finally:
        var.reset(token)


def is_recording_suppressed() -> bool:
    """Check whether automatic recording is currently suppressed."""
    return bool(_get_recording_suppressed_var().get())


def _safe_setattr(target, name: str, value) -> bool:
    """Attempt to set attribute and return whether it succeeded."""
    try:
        setattr(target, name, value)
        return True
    except Exception:
        return False


class OpenAIInterceptor:
    """
    Automatic OpenAI interception system that patches the OpenAI module
    to automatically record conversations when Memori instances are enabled.
    """

    _original_methods = {}
    _is_patched = False

    @classmethod
    def patch_openai(cls):
        """Patch OpenAI module to intercept API calls."""
        if cls._is_patched:
            return

        try:
            import openai

            # Patch sync OpenAI client
            if hasattr(openai, "OpenAI"):
                cls._patch_client_class(openai.OpenAI, "sync")

            # Patch async OpenAI client
            if hasattr(openai, "AsyncOpenAI"):
                cls._patch_async_client_class(openai.AsyncOpenAI, "async")

            # Patch Azure clients if available
            if hasattr(openai, "AzureOpenAI"):
                cls._patch_client_class(openai.AzureOpenAI, "azure_sync")

            if hasattr(openai, "AsyncAzureOpenAI"):
                cls._patch_async_client_class(openai.AsyncAzureOpenAI, "azure_async")

            cls._is_patched = True
            logger.debug("OpenAI module patched for automatic interception")

        except ImportError:
            logger.warning("OpenAI not available - skipping patch")
        except Exception as e:
            logger.error(f"Failed to patch OpenAI module: {e}")

    @classmethod
    def _patch_client_class(cls, client_class, client_type):
        """Patch a sync OpenAI client class."""
        # Store the original unbound method
        original_key = f"{client_type}_process_response"
        if original_key not in cls._original_methods:
            cls._original_methods[original_key] = client_class._process_response

        original_prepare_key = f"{client_type}_prepare_options"
        if original_prepare_key not in cls._original_methods and hasattr(
            client_class, "_prepare_options"
        ):
            cls._original_methods[original_prepare_key] = client_class._prepare_options

        # Get reference to original method to avoid recursion
        original_process = cls._original_methods[original_key]

        def patched_process_response(
            self, *, cast_to, options, response, stream, stream_cls, **kwargs
        ):
            # Call original method first with all kwargs
            result = original_process(
                self,
                cast_to=cast_to,
                options=options,
                response=response,
                stream=stream,
                stream_cls=stream_cls,
                **kwargs,
            )

            # Record conversation for enabled Memori instances
            if not stream:  # Don't record streaming here - handle separately
                cls._record_conversation_for_enabled_instances(
                    options, result, client_type, client=self
                )

            return result

        client_class._process_response = patched_process_response

        # Patch prepare_options if it exists
        if original_prepare_key in cls._original_methods:
            original_prepare = cls._original_methods[original_prepare_key]

            def patched_prepare_options(self, options):
                # Call original method first
                options = original_prepare(self, options)

                # Inject context for enabled Memori instances
                options = cls._inject_context_for_enabled_instances(
                    options, client_type, client=self
                )

                return options

            client_class._prepare_options = patched_prepare_options

    @classmethod
    def _patch_async_client_class(cls, client_class, client_type):
        """Patch an async OpenAI client class."""
        # Store the original unbound method
        original_key = f"{client_type}_process_response"
        if original_key not in cls._original_methods:
            cls._original_methods[original_key] = client_class._process_response

        original_prepare_key = f"{client_type}_prepare_options"
        if original_prepare_key not in cls._original_methods and hasattr(
            client_class, "_prepare_options"
        ):
            cls._original_methods[original_prepare_key] = client_class._prepare_options

        # Get reference to original method to avoid recursion
        original_process = cls._original_methods[original_key]

        async def patched_async_process_response(
            self, *, cast_to, options, response, stream, stream_cls, **kwargs
        ):
            # Call original method first with all kwargs
            result = await original_process(
                self,
                cast_to=cast_to,
                options=options,
                response=response,
                stream=stream,
                stream_cls=stream_cls,
                **kwargs,
            )

            # Record conversation for enabled Memori instances
            if not stream:
                cls._record_conversation_for_enabled_instances(
                    options, result, client_type, client=self
                )

            return result

        client_class._process_response = patched_async_process_response

        # Patch prepare_options if it exists
        if original_prepare_key in cls._original_methods:
            original_prepare = cls._original_methods[original_prepare_key]

            def patched_async_prepare_options(self, options):
                # Call original method first
                options = original_prepare(self, options)

                # Inject context for enabled Memori instances
                options = cls._inject_context_for_enabled_instances(
                    options, client_type, client=self
                )

                return options

            client_class._prepare_options = patched_async_prepare_options

    @classmethod
    def _bind_client_to_instance(cls, client, memori_instance):
        try:
            client._memori_instance_id = memori_instance._session_id
        except Exception:
            logger.debug("Failed to bind Memori instance to OpenAI client")

    @classmethod
    def _select_target_instances(cls, client):
        instance_id = None
        if client is not None:
            instance_id = getattr(client, "_memori_instance_id", None)

        if not instance_id:
            current = get_current_memori_instance()
            if current is not None:
                instance_id = getattr(current, "_session_id", None)
                if client is not None and instance_id:
                    cls._bind_client_to_instance(client, current)

        if instance_id:
            matching = [
                memori_instance
                for memori_instance in _enabled_memori_instances
                if getattr(memori_instance, "_session_id", None) == instance_id
            ]
            if matching:
                return matching

        return _enabled_memori_instances.copy()

    @classmethod
    def _inject_context_for_enabled_instances(cls, options, client_type, client=None):
        """Inject context for the Memori instance associated with the current client."""
        if inspect.iscoroutine(options):
            logger.debug(
                "OpenAI: Received coroutine options; skipping context injection"
            )
            return options

        target_instances = cls._select_target_instances(client)
        if not target_instances:
            return options

        for memori_instance in target_instances:
            if not memori_instance.is_enabled or not (
                memori_instance.conscious_ingest or memori_instance.auto_ingest
            ):
                continue

            try:
                json_data = None
                for attr_name in ["json_data", "_json_data", "data"]:
                    if hasattr(options, attr_name):
                        json_data = getattr(options, attr_name, None)
                        if json_data:
                            break

                if not json_data:
                    json_data = {}
                    if hasattr(options, "messages"):
                        json_data["messages"] = options.messages
                    elif hasattr(options, "_messages"):
                        json_data["messages"] = options._messages

                if json_data and "messages" in json_data:
                    logger.debug(
                        f"OpenAI: Injecting context for {client_type} with {len(json_data['messages'])} messages"
                    )
                    updated_data = memori_instance._inject_openai_context(
                        {"messages": json_data["messages"]}
                    )

                    if updated_data.get("messages"):
                        if hasattr(options, "json_data") and options.json_data:
                            options.json_data["messages"] = updated_data["messages"]
                        elif hasattr(options, "messages"):
                            options.messages = updated_data["messages"]

                        logger.debug(
                            f"OpenAI: Successfully injected context for {client_type}"
                        )

                        _safe_setattr(
                            options, "_memori_instance_id", memori_instance._session_id
                        )
                        if client:
                            cls._bind_client_to_instance(client, memori_instance)
                        break
                else:
                    logger.debug(
                        f"OpenAI: No messages found in options for {client_type}, skipping context injection"
                    )

            except Exception as e:
                logger.error(f"Context injection failed for {client_type}: {e}")

        return options

    @classmethod
    def _is_internal_agent_call(cls, json_data):
        """Check if this is an internal agent processing call that should not be recorded."""
        try:
            messages = json_data.get("messages", [])
            for message in messages:
                content = message.get("content", "")
                if isinstance(content, str):
                    # Check for specific internal agent processing patterns
                    # Made patterns more specific to avoid false positives
                    internal_patterns = [
                        "Process this conversation for enhanced memory storage:",
                        "Enhanced memory processing:",
                        "Memory classification:",
                        "Search for relevant memories:",
                        "Analyze conversation for:",
                        "Extract entities from:",
                        "Categorize the following conversation:",
                        # More specific patterns to avoid blocking legitimate conversations
                        "INTERNAL_MEMORY_PROCESSING:",
                        "AGENT_PROCESSING_MODE:",
                        "MEMORY_AGENT_TASK:",
                    ]

                    # Only flag as internal if it matches specific patterns AND has no user role
                    for pattern in internal_patterns:
                        if pattern in content:
                            # Double-check: if this is a user message, don't filter it
                            if message.get("role") == "user":
                                continue
                            return True

            return False

        except Exception as e:
            logger.debug(f"Failed to check internal agent call: {e}")
            return False

    @classmethod
    def _record_conversation_for_enabled_instances(
        cls, options, response, client_type, client=None
    ):
        """Record conversation for the Memori instance bound to the call."""
        if is_recording_suppressed():
            logger.debug("Skipping recording - internal Memori processing detected")
            return

        if inspect.iscoroutine(options):
            logger.debug(
                "OpenAI: Received coroutine options during recording; skipping"
            )
            return

        json_data = getattr(options, "json_data", None) or {}
        if not json_data:
            json_data = {}
            if hasattr(options, "messages"):
                json_data["messages"] = options.messages

        instance_id = getattr(options, "_memori_instance_id", None)
        target_instances = cls._select_target_instances(client)
        if instance_id:
            target_instances = [
                memori_instance
                for memori_instance in target_instances
                if getattr(memori_instance, "_session_id", None) == instance_id
            ]
        elif len(target_instances) > 1:
            logger.debug(
                "Multiple Memori instances matched client but no instance id present; skipping record"
            )
            return

        if not target_instances:
            logger.debug("No Memori instance available for recording")
            return

        for memori_instance in target_instances:
            if not memori_instance.is_enabled:
                continue

            try:
                if "messages" in json_data:
                    if cls._is_internal_agent_call(json_data):
                        logger.debug("Skipping internal agent call (pattern detection)")
                        continue

                    user_messages = [
                        msg
                        for msg in json_data.get("messages", [])
                        if msg.get("role") == "user"
                    ]
                    if user_messages:
                        user_content = user_messages[-1].get("content", "")[:50]
                        logger.debug(
                            f"Recording conversation: '{user_content}...' (client_type={client_type})"
                        )

                    if not instance_id:
                        _safe_setattr(
                            options, "_memori_instance_id", memori_instance._session_id
                        )
                        if client is not None:
                            cls._bind_client_to_instance(client, memori_instance)
                        instance_id = memori_instance._session_id

                    with activate_memori_instance(memori_instance):
                        memori_instance._record_openai_conversation(json_data, response)
                elif "prompt" in json_data:
                    if not instance_id:
                        _safe_setattr(
                            options, "_memori_instance_id", memori_instance._session_id
                        )
                        if client is not None:
                            cls._bind_client_to_instance(client, memori_instance)
                        instance_id = memori_instance._session_id

                    with activate_memori_instance(memori_instance):
                        cls._record_legacy_completion(
                            memori_instance, json_data, response, client_type
                        )

            except Exception as e:
                logger.error(f"Failed to record conversation for {client_type}: {e}")

    @classmethod
    def _record_legacy_completion(
        cls, memori_instance, request_data, response, client_type
    ):
        """Record legacy completion API calls."""
        try:
            prompt = request_data.get("prompt", "")
            model = request_data.get("model", "unknown")

            # Extract AI response
            ai_output = ""
            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                if hasattr(choice, "text"):
                    ai_output = choice.text or ""

            # Calculate tokens
            tokens_used = 0
            if hasattr(response, "usage") and response.usage:
                tokens_used = getattr(response.usage, "total_tokens", 0)

            # Record conversation
            memori_instance.record_conversation(
                user_input=prompt,
                ai_output=ai_output,
                model=model,
                metadata={
                    "integration": "openai_auto_intercept",
                    "client_type": client_type,
                    "api_type": "completions",
                    "tokens_used": tokens_used,
                    "auto_recorded": True,
                },
            )
        except Exception as e:
            logger.error(f"Failed to record legacy completion: {e}")

    @classmethod
    def unpatch_openai(cls):
        """Restore original OpenAI module methods."""
        if not cls._is_patched:
            return

        try:
            import openai

            # Restore sync OpenAI client
            if "sync_process_response" in cls._original_methods:
                openai.OpenAI._process_response = cls._original_methods[
                    "sync_process_response"
                ]

            if "sync_prepare_options" in cls._original_methods:
                openai.OpenAI._prepare_options = cls._original_methods[
                    "sync_prepare_options"
                ]

            # Restore async OpenAI client
            if "async_process_response" in cls._original_methods:
                openai.AsyncOpenAI._process_response = cls._original_methods[
                    "async_process_response"
                ]

            if "async_prepare_options" in cls._original_methods:
                openai.AsyncOpenAI._prepare_options = cls._original_methods[
                    "async_prepare_options"
                ]

            # Restore Azure clients
            if (
                hasattr(openai, "AzureOpenAI")
                and "azure_sync_process_response" in cls._original_methods
            ):
                openai.AzureOpenAI._process_response = cls._original_methods[
                    "azure_sync_process_response"
                ]

            if (
                hasattr(openai, "AzureOpenAI")
                and "azure_sync_prepare_options" in cls._original_methods
            ):
                openai.AzureOpenAI._prepare_options = cls._original_methods[
                    "azure_sync_prepare_options"
                ]

            if (
                hasattr(openai, "AsyncAzureOpenAI")
                and "azure_async_process_response" in cls._original_methods
            ):
                openai.AsyncAzureOpenAI._process_response = cls._original_methods[
                    "azure_async_process_response"
                ]

            if (
                hasattr(openai, "AsyncAzureOpenAI")
                and "azure_async_prepare_options" in cls._original_methods
            ):
                openai.AsyncAzureOpenAI._prepare_options = cls._original_methods[
                    "azure_async_prepare_options"
                ]

            cls._is_patched = False
            cls._original_methods.clear()
            logger.debug("OpenAI module patches removed")

        except ImportError:
            pass  # OpenAI not available
        except Exception as e:
            logger.error(f"Failed to unpatch OpenAI module: {e}")


def register_memori_instance(memori_instance):
    """
    Register a Memori instance for automatic OpenAI interception.

    Args:
        memori_instance: Memori instance to register
    """
    global _enabled_memori_instances

    if memori_instance not in _enabled_memori_instances:
        _enabled_memori_instances.append(memori_instance)
        logger.debug("Registered Memori instance for OpenAI interception")

    try:
        set_current_memori_instance(memori_instance)
    except Exception:
        logger.debug(
            "Failed to set current Memori instance context during registration"
        )

    # Ensure OpenAI is patched
    OpenAIInterceptor.patch_openai()


def unregister_memori_instance(memori_instance):
    """
    Unregister a Memori instance from automatic OpenAI interception.

    Args:
        memori_instance: Memori instance to unregister
    """
    global _enabled_memori_instances

    if memori_instance in _enabled_memori_instances:
        _enabled_memori_instances.remove(memori_instance)
        logger.debug("Unregistered Memori instance from OpenAI interception")

    # If no more instances, unpatch OpenAI
    if not _enabled_memori_instances:
        OpenAIInterceptor.unpatch_openai()
        try:
            set_current_memori_instance(None)
        except Exception:
            logger.debug("Failed to clear Memori context during unregistration")


def get_enabled_instances():
    """Get list of currently enabled Memori instances."""
    return _enabled_memori_instances.copy()


def is_openai_patched():
    """Check if OpenAI module is currently patched."""
    return OpenAIInterceptor._is_patched


# For backward compatibility - keep old classes but mark as deprecated
class MemoriOpenAI:
    """
    DEPRECATED: Legacy wrapper class.

    Use automatic interception instead:
        memori = Memori(...)
        memori.enable()
        client = OpenAI()  # Automatically intercepted
    """

    def __init__(self, memori_instance, **kwargs):
        logger.warning(
            "MemoriOpenAI is deprecated. Use automatic interception instead:\n"
            "memori.enable() then use OpenAI() client directly."
        )

        try:
            import openai

            self._openai = openai.OpenAI(**kwargs)

            # Register for automatic interception
            register_memori_instance(memori_instance)

            # Pass through all attributes
            for attr in dir(self._openai):
                if not attr.startswith("_"):
                    setattr(self, attr, getattr(self._openai, attr))

        except ImportError as err:
            raise ImportError("OpenAI package required: pip install openai") from err


class MemoriOpenAIInterceptor(MemoriOpenAI):
    """DEPRECATED: Use automatic interception instead."""

    def __init__(self, memori_instance, **kwargs):
        logger.warning(
            "MemoriOpenAIInterceptor is deprecated. Use automatic interception instead:\n"
            "memori.enable() then use OpenAI() client directly."
        )
        super().__init__(memori_instance, **kwargs)


def create_openai_client(memori_instance, provider_config=None, **kwargs):
    """
    Create an OpenAI client that automatically records to memori.

    This is the recommended way to create OpenAI clients with memori integration.

    Args:
        memori_instance: Memori instance to record conversations to
        provider_config: Provider configuration (optional)
        **kwargs: Additional arguments for OpenAI client

    Returns:
        OpenAI client instance with automatic recording
    """
    try:
        import openai

        # Register the memori instance for automatic interception
        register_memori_instance(memori_instance)

        # Use provider config if available, otherwise use kwargs
        if provider_config:
            client_kwargs = provider_config.to_openai_kwargs()
            client_kwargs.update(kwargs)  # Allow kwargs to override config
        else:
            client_kwargs = kwargs

        # Create standard OpenAI client - it will be automatically intercepted
        client = openai.OpenAI(**client_kwargs)

        logger.info("Created OpenAI client with automatic memori recording")
        return client

    except ImportError as e:
        logger.error(f"Failed to import OpenAI: {e}")
        raise ImportError("OpenAI package required: pip install openai") from e
    except Exception as e:
        logger.error(f"Failed to create OpenAI client: {e}")
        raise
