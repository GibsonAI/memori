"""
Universal LLM Integration - Plug-and-Play Memory Recording

SIMPLE USAGE (RECOMMENDED):
Just call memori.enable() and use ANY LLM library normally!

```python
from memori import Memori

memori = Memori(...)
memori.enable()  # That's it!

# Now use ANY LLM library normally - all calls will be auto-recorded:

# LiteLLM (native callbacks)
from litellm import completion
completion(model="gpt-4o", messages=[...])  # Auto-recorded

# Direct OpenAI (auto-wrapping)
import openai
client = openai.OpenAI(api_key="...")
client.chat.completions.create(...)  # Auto-recorded

# Direct Anthropic (auto-wrapping)
import anthropic
client = anthropic.Anthropic(api_key="...")
client.messages.create(...)  # Auto-recorded
```

The universal system automatically detects and records ALL LLM providers
without requiring wrapper classes or complex setup.
"""

from typing import Any

from loguru import logger

# Legacy imports (all deprecated)
from . import anthropic_integration, litellm_integration, openai_integration

__all__ = [
    # New interceptor classes (recommended)
    "MemoriOpenAIInterceptor",
    # Wrapper classes for direct SDK usage (legacy)
    "MemoriOpenAI",
    "MemoriAnthropic",
    # Factory functions
    "create_openai_client",
    "setup_openai_interceptor",
]


# For backward compatibility, provide simple passthrough
try:
    from .anthropic_integration import MemoriAnthropic
    from .openai_integration import (
        MemoriOpenAI,
        MemoriOpenAIInterceptor,
        create_openai_client,
        setup_openai_interceptor,
    )

    # But warn users about the better way for deprecated classes
    def __getattr__(name):
        if name == "MemoriOpenAI":
            logger.warning(
                "WARNING: MemoriOpenAI wrapper class is deprecated!\n"
                "RECOMMENDED: Use MemoriOpenAIInterceptor or memori.create_openai_client()"
            )
            return MemoriOpenAI
        elif name == "MemoriAnthropic":
            logger.warning(
                "WARNING: MemoriAnthropic wrapper class is deprecated!\n"
                "RECOMMENDED: Use memori.enable() and import anthropic normally"
            )
            return MemoriAnthropic
        elif name in [
            "MemoriOpenAIInterceptor",
            "create_openai_client",
            "setup_openai_interceptor",
        ]:
            # These are the new recommended classes/functions
            if name == "MemoriOpenAIInterceptor":
                return MemoriOpenAIInterceptor
            elif name == "create_openai_client":
                return create_openai_client
            elif name == "setup_openai_interceptor":
                return setup_openai_interceptor
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

except ImportError:
    # Wrapper classes not available, that's fine
    pass
