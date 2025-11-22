"""
Provider configuration for different LLM providers (OpenAI, Azure, custom)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

from loguru import logger


class ProviderType(Enum):
    """Supported LLM provider types"""

    OPENAI = "openai"
    AZURE = "azure"
    CUSTOM = "custom"
    OPENAI_COMPATIBLE = "openai_compatible"  # For OpenAI-compatible APIs


@dataclass
class ProviderConfig:
    """
    Configuration for LLM providers with support for OpenAI, Azure, and custom endpoints.

    This class provides a unified interface for configuring different LLM providers
    while maintaining backward compatibility with existing OpenAI-only configuration.
    """

    # Common parameters
    api_key: str | None = None
    api_type: str | None = None  # "openai", "azure", or custom
    base_url: str | None = None  # Custom endpoint URL
    timeout: float | None = 60.0  # Default 60 second timeout for API calls
    max_retries: int | None = 2  # Default 2 retries

    # Azure-specific parameters
    azure_endpoint: str | None = None
    azure_deployment: str | None = None
    api_version: str | None = None
    azure_ad_token: str | None = None

    # OpenAI-specific parameters
    organization: str | None = None
    project: str | None = None

    # Model configuration
    model: str | None = None  # User can specify model, defaults to gpt-4o if not set

    # Additional headers for custom providers
    default_headers: dict[str, str] | None = None
    default_query: dict[str, Any] | None = None

    # HTTP client configuration
    http_client: Any | None = None

    @classmethod
    def from_openai(
        cls, api_key: str | None = None, model: str | None = None, **kwargs
    ):
        """Create configuration for standard OpenAI"""
        return cls(api_key=api_key, api_type="openai", model=model, **kwargs)

    @classmethod
    def from_azure(
        cls,
        api_key: str | None = None,
        azure_endpoint: str | None = None,
        azure_deployment: str | None = None,
        api_version: str | None = None,
        model: str | None = None,
        **kwargs,
    ):
        """Create configuration for Azure OpenAI"""
        return cls(
            api_key=api_key,
            api_type="azure",
            azure_endpoint=azure_endpoint,
            azure_deployment=azure_deployment,
            api_version=api_version,
            model=model,
            **kwargs,
        )

    @classmethod
    def from_custom(
        cls,
        base_url: str,
        api_key: str | None = None,
        model: str | None = None,
        **kwargs,
    ):
        """Create configuration for custom OpenAI-compatible endpoints"""
        return cls(
            api_key=api_key, api_type="custom", base_url=base_url, model=model, **kwargs
        )

    def get_openai_client_kwargs(self) -> dict[str, Any]:
        """
        Get kwargs for OpenAI client initialization based on provider type.

        Returns:
            Dictionary of parameters to pass to OpenAI client constructor
        """
        kwargs = {}

        # Always include API key if provided
        if self.api_key:
            kwargs["api_key"] = self.api_key

        if self.api_type == "azure":
            # Azure OpenAI configuration
            if self.azure_endpoint:
                kwargs["azure_endpoint"] = self.azure_endpoint
            if self.azure_deployment:
                kwargs["azure_deployment"] = self.azure_deployment
            if self.api_version:
                kwargs["api_version"] = self.api_version
            if self.azure_ad_token:
                kwargs["azure_ad_token"] = self.azure_ad_token
            # For Azure, we need to use AzureOpenAI client
            kwargs["_use_azure_client"] = True

        elif self.api_type == "custom" or self.api_type == "openai_compatible":
            # Custom endpoint configuration
            if self.base_url:
                kwargs["base_url"] = self.base_url

        elif self.api_type == "openai":
            # Standard OpenAI configuration
            if self.organization:
                kwargs["organization"] = self.organization
            if self.project:
                kwargs["project"] = self.project

        # Common parameters
        if self.timeout:
            kwargs["timeout"] = self.timeout
        if self.max_retries:
            kwargs["max_retries"] = self.max_retries
        if self.default_headers:
            kwargs["default_headers"] = self.default_headers
        if self.default_query:
            kwargs["default_query"] = self.default_query
        if self.http_client:
            kwargs["http_client"] = self.http_client

        return kwargs

    def create_client(self):
        """
        Create the appropriate OpenAI client based on configuration.

        Returns:
            OpenAI or AzureOpenAI client instance
        """
        import openai

        kwargs = self.get_openai_client_kwargs()

        # Check if we should use Azure client
        if kwargs.pop("_use_azure_client", False):
            # Use Azure OpenAI client
            from openai import AzureOpenAI

            return AzureOpenAI(**kwargs)
        else:
            # Use standard OpenAI client (works for OpenAI and custom endpoints)
            return openai.OpenAI(**kwargs)

    def create_async_client(self):
        """
        Create the appropriate async OpenAI client based on configuration.

        Returns:
            AsyncOpenAI or AsyncAzureOpenAI client instance
        """
        import openai

        kwargs = self.get_openai_client_kwargs()

        # Check if we should use Azure client
        if kwargs.pop("_use_azure_client", False):
            # Use Azure OpenAI async client
            from openai import AsyncAzureOpenAI

            return AsyncAzureOpenAI(**kwargs)
        else:
            # Use standard async OpenAI client
            return openai.AsyncOpenAI(**kwargs)


def detect_provider_from_env() -> ProviderConfig:
    """
    Create provider configuration from environment variables WITHOUT automatic detection.

    This function ONLY uses standard OpenAI configuration by default.
    It does NOT automatically detect or prioritize Azure or custom providers.

    Only use specific providers if explicitly configured via Memori constructor parameters.

    Returns:
        Standard OpenAI ProviderConfig instance (never auto-detects other providers)
    """
    import os

    # Get model from environment (optional, defaults to gpt-4o if not set)
    model = os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL") or "gpt-4o"

    # ALWAYS default to standard OpenAI - no automatic detection
    logger.info("Provider configuration: Using standard OpenAI (no auto-detection)")
    return ProviderConfig.from_openai(
        api_key=os.getenv("OPENAI_API_KEY"),
        organization=os.getenv("OPENAI_ORGANIZATION"),
        project=os.getenv("OPENAI_PROJECT"),
        model=model,
    )
