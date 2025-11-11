"""
LiteLLM Integration - Native Callback System

This module handles LiteLLM native callback registration for automatic
memory recording. It uses LiteLLM's official callback mechanism instead
of monkey-patching.

Usage:
    from memori import Memori

    memori = Memori(...)
    memori.enable()  # Automatically registers LiteLLM callbacks

    # Now use LiteLLM normally - conversations are auto-recorded
    from litellm import completion
    response = completion(model="gpt-4o", messages=[...])
"""

from loguru import logger

try:
    import litellm

    LITELLM_AVAILABLE = True

    # Check for modifying input callbacks (for context injection)
    HAS_MODIFYING_ROUTER = hasattr(litellm, "Router") and hasattr(
        litellm.Router, "pre_call_hook"
    )

except ImportError:
    LITELLM_AVAILABLE = False
    HAS_MODIFYING_ROUTER = False
    logger.debug("LiteLLM not available - native callback system disabled")


class LiteLLMCallbackManager:
    """
    Manages LiteLLM native callback registration and integration with Memori.

    This class provides a clean interface for registering and managing
    LiteLLM callbacks that automatically record conversations into Memori.
    """

    def __init__(self, memori_instance):
        """
        Initialize LiteLLM callback manager.

        Args:
            memori_instance: The Memori instance to record conversations to
        """
        self.memori_instance = memori_instance
        self._callback_registered = False
        self._original_callbacks = None
        self._original_completion = None  # For context injection

    def register_callbacks(self) -> bool:
        """
        Register LiteLLM native callbacks for automatic memory recording.

        Returns:
            True if registration successful, False otherwise
        """
        if not LITELLM_AVAILABLE:
            logger.debug("LiteLLM not available - cannot register callbacks")
            return False

        if self._callback_registered:
            logger.warning("LiteLLM callbacks already registered")
            return True

        try:
            # Store original callbacks for restoration
            self._original_callbacks = getattr(litellm, "success_callback", [])

            # Register our success callback
            if not hasattr(litellm, "success_callback"):
                litellm.success_callback = []
            elif not isinstance(litellm.success_callback, list):
                litellm.success_callback = [litellm.success_callback]

            # Add our callback function
            litellm.success_callback.append(self._litellm_success_callback)

            # For context injection, we need to monkey-patch the completion function
            # This is the only reliable way to inject context before requests in LiteLLM
            if (
                self.memori_instance.conscious_ingest
                or self.memori_instance.auto_ingest
            ):
                self._setup_context_injection()

            self._callback_registered = True
            logger.info("LiteLLM native callbacks registered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to register LiteLLM callbacks: {e}")
            return False

    def unregister_callbacks(self) -> bool:
        """
        Unregister LiteLLM callbacks and restore original state.

        Returns:
            True if unregistration successful, False otherwise
        """
        if not LITELLM_AVAILABLE:
            return False

        if not self._callback_registered:
            logger.warning("LiteLLM callbacks not registered")
            return True

        try:
            # Remove our callback
            if hasattr(litellm, "success_callback") and isinstance(
                litellm.success_callback, list
            ):
                # Remove all instances of our callback
                litellm.success_callback = [
                    cb
                    for cb in litellm.success_callback
                    if cb != self._litellm_success_callback
                ]

                # If no callbacks left, restore original state
                if not litellm.success_callback:
                    if self._original_callbacks:
                        litellm.success_callback = self._original_callbacks
                    else:
                        delattr(litellm, "success_callback")

            # Restore original completion function if we modified it
            if self._original_completion is not None:
                litellm.completion = self._original_completion
                self._original_completion = None

            self._callback_registered = False
            logger.info("LiteLLM native callbacks unregistered successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister LiteLLM callbacks: {e}")
            return False

    def _litellm_success_callback(self, kwargs, response, start_time, end_time):
        """
        LiteLLM success callback that records conversations in Memori.

        This function is automatically called by LiteLLM after successful completions.

        Args:
            kwargs: Original request parameters
            response: LiteLLM response object
            start_time: Request start time
            end_time: Request end time
        """
        try:
            if not self.memori_instance or not self.memori_instance.is_enabled:
                return

            # Handle context injection for conscious_ingest and auto_ingest
            if (
                self.memori_instance.conscious_ingest
                or self.memori_instance.auto_ingest
            ):
                # Note: Context injection happens BEFORE the request in LiteLLM
                # This callback is for recording AFTER the response
                pass

            # Extract user input
            user_input = ""
            messages = kwargs.get("messages", [])
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_input = msg.get("content", "")
                    break

            # Extract AI output
            ai_output = ""
            if hasattr(response, "choices") and response.choices:
                choice = response.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    ai_output = choice.message.content or ""

            # Debug logging to help diagnose recording issues
            if user_input:
                logger.debug(
                    f"LiteLLM callback: Recording conversation '{user_input[:50]}...'"
                    if len(user_input) > 50
                    else f"LiteLLM callback: Recording conversation '{user_input}'"
                )
            else:
                logger.warning(
                    f"LiteLLM callback: No user input found in messages: {[msg.get('role') for msg in messages]}"
                )

            # Extract model
            model = kwargs.get("model", "litellm-unknown")

            # Calculate timing
            duration_ms = 0
            if start_time is not None and end_time is not None:
                try:
                    if isinstance(start_time, int | float) and isinstance(
                        end_time, int | float
                    ):
                        duration_ms = (end_time - start_time) * 1000
                except Exception:
                    pass

            # Extract token usage
            tokens_used = 0
            if hasattr(response, "usage") and response.usage:
                tokens_used = getattr(response.usage, "total_tokens", 0)

            # Prepare metadata
            metadata = {
                "integration": "litellm_native",
                "api_type": "completion",
                "tokens_used": tokens_used,
                "auto_recorded": True,
                "duration_ms": duration_ms,
            }

            # Add token details if available
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                metadata.update(
                    {
                        "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                        "completion_tokens": getattr(usage, "completion_tokens", 0),
                    }
                )

            # Record the conversation
            if user_input and ai_output:
                self.memori_instance.record_conversation(
                    user_input=user_input,
                    ai_output=ai_output,
                    model=model,
                    metadata=metadata,
                )
                logger.debug(
                    f"LiteLLM callback: Successfully recorded conversation for model {model}"
                )
            else:
                logger.warning(
                    f"LiteLLM callback: Skipping record - user_input='{bool(user_input)}' ai_output='{bool(ai_output)}'"
                )

        except Exception as e:
            logger.error(f"LiteLLM callback failed: {e}")
            import traceback

            logger.error(f"LiteLLM callback error details: {traceback.format_exc()}")

    def _setup_context_injection(self):
        """Set up context injection by wrapping LiteLLM's completion function."""
        try:
            if self._original_completion is not None:
                # Already set up
                return

            # Store original completion function
            self._original_completion = litellm.completion

            # Create wrapper function that injects context
            def completion_with_context(*args, **kwargs):
                # DEDUPLICATION FIX: Mark this as a LiteLLM call
                # This prevents OpenAI interception from recording the same conversation
                if "metadata" not in kwargs:
                    kwargs["metadata"] = {}
                elif kwargs["metadata"] is None:
                    kwargs["metadata"] = {}

                # Ensure metadata is a dict (LiteLLM accepts dict metadata)
                if isinstance(kwargs["metadata"], dict):
                    kwargs["metadata"]["_memori_source"] = "litellm"

                # Inject context if needed
                kwargs = self._inject_context(kwargs)
                # Call original completion function
                return self._original_completion(*args, **kwargs)

            # Replace LiteLLM's completion function
            litellm.completion = completion_with_context

            logger.debug("Context injection wrapper set up for LiteLLM")

        except Exception as e:
            logger.error(f"Failed to set up context injection: {e}")

    def _inject_context(self, kwargs):
        """Inject memory context into LiteLLM request kwargs."""
        try:
            if not self.memori_instance:
                return kwargs

            # Use the existing context injection methods from the Memori instance
            if (
                self.memori_instance.conscious_ingest
                or self.memori_instance.auto_ingest
            ):
                logger.debug("LiteLLM: Starting context injection")

                # Determine mode
                if self.memori_instance.conscious_ingest:
                    mode = "conscious"
                elif self.memori_instance.auto_ingest:
                    mode = "auto"
                else:
                    mode = "auto"  # fallback

                # Extract user input first to debug what we're working with
                messages = kwargs.get("messages", [])
                user_input = ""
                for msg in reversed(messages):
                    if msg.get("role") == "user":
                        user_input = msg.get("content", "")
                        break

                logger.debug(
                    f"LiteLLM: Injecting context in {mode} mode for input: {user_input[:100]}..."
                )

                # Use the existing _inject_litellm_context method
                kwargs = self.memori_instance._inject_litellm_context(kwargs, mode=mode)

                # Verify injection worked
                updated_messages = kwargs.get("messages", [])
                if len(updated_messages) > len(messages):
                    logger.debug(
                        f"LiteLLM: Context injection successful, message count increased from {len(messages)} to {len(updated_messages)}"
                    )
                else:
                    logger.debug(
                        "LiteLLM: Context injection completed, no new messages added (may be intended)"
                    )

        except Exception as e:
            logger.error(f"Context injection failed in LiteLLM wrapper: {e}")
            import traceback

            logger.debug(f"LiteLLM injection stack trace: {traceback.format_exc()}")

        return kwargs

    @property
    def is_registered(self) -> bool:
        """Check if callbacks are registered."""
        return self._callback_registered


def setup_litellm_callbacks(memori_instance) -> LiteLLMCallbackManager | None:
    """
    Convenience function to set up LiteLLM callbacks for a Memori instance.

    Args:
        memori_instance: The Memori instance to record conversations to

    Returns:
        LiteLLMCallbackManager instance if successful, None otherwise
    """
    if not LITELLM_AVAILABLE:
        logger.debug("LiteLLM not available - cannot set up callbacks")
        return None

    callback_manager = LiteLLMCallbackManager(memori_instance)
    if callback_manager.register_callbacks():
        return callback_manager
    return None
