"""
Universal LLM Integration - Plug-and-Play Memory Recording

🎯 SIMPLE USAGE (RECOMMENDED):
Just call memori.enable() and use ANY LLM library normally!

```python
from memori import Memori

memori = Memori(...)
memori.enable()  # 🎉 That's it!

# Now use ANY LLM library normally - all calls will be auto-recorded:

# LiteLLM (native callbacks)
from litellm import completion
completion(model="gpt-4o", messages=[...])  # ✅ Auto-recorded

# Direct OpenAI (auto-wrapping)
import openai
client = openai.OpenAI(api_key="...")
client.chat.completions.create(...)  # ✅ Auto-recorded

# Direct Anthropic (auto-wrapping)
import anthropic
client = anthropic.Anthropic(api_key="...")
client.messages.create(...)  # ✅ Auto-recorded

# Direct Google GenAI (auto-wrapping)
import google.generativeai as genai
genai.configure(api_key="...")
model = genai.GenerativeModel("gemini-pro")
model.generate_content(...)  # ✅ Auto-recorded
```

The universal system automatically detects and records ALL LLM providers
without requiring wrapper classes or complex setup.
"""

from typing import Any

from loguru import logger

# Legacy imports (all deprecated)
from . import anthropic_integration, google_genai_integration, litellm_integration, openai_integration

__all__ = [
    # New interceptor classes (recommended)
    "MemoriOpenAIInterceptor",
    # Wrapper classes for direct SDK usage (legacy)
    
    "MemoriOpenAI",
    "MemoriAnthropic",
    # Factory functions
    "create_openai_client",
    "setup_openai_interceptor",
    "create_genai_model",
    "setup_genai_interceptor",
]


# For backward compatibility, provide simple passthrough
try:
    from .anthropic_integration import MemoriAnthropic
    from .google_genai_integration import (
        create_genai_model,
        setup_genai_interceptor,
    )
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
                "🚨 MemoriOpenAI wrapper class is deprecated!\n"
                "✅ NEW RECOMMENDED WAY: Use MemoriOpenAIInterceptor or memori.create_openai_client()"
            )
            return MemoriOpenAI
        elif name == "MemoriAnthropic":
            logger.warning(
                "🚨 MemoriAnthropic wrapper class is deprecated!\n"
                "✅ NEW SIMPLE WAY: Use memori.enable() and import anthropic normally"
            )
            return MemoriAnthropic
        elif name in [
            "MemoriOpenAIInterceptor",
            "create_openai_client",
            "setup_openai_interceptor",
            "create_genai_model",
            "setup_genai_interceptor",
        ]:
            # These are the new recommended classes/functions
            if name == "MemoriOpenAIInterceptor":
                return MemoriOpenAIInterceptor
            elif name == "create_openai_client":
                return create_openai_client
            elif name == "setup_openai_interceptor":
                return setup_openai_interceptor
            elif name == "create_genai_model":
                return create_genai_model
            elif name == "setup_genai_interceptor":
                return setup_genai_interceptor
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

except ImportError as e:
    # Wrapper classes not available, that's fine
    logger.debug(f"Some integrations not available: {e}")
    pass