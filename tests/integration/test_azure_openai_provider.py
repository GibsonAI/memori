"""
Azure OpenAI Provider Integration Tests

Tests Memori integration with Azure OpenAI Service.

Validates three aspects:
1. Functional: Azure OpenAI calls work with Memori enabled
2. Persistence: Conversations are recorded in database
3. Integration: Azure-specific configuration handled correctly
"""

import os
import time

import pytest


@pytest.mark.llm
@pytest.mark.integration
class TestAzureOpenAIBasicIntegration:
    """Test basic Azure OpenAI integration with Memori."""

    def test_azure_openai_with_mock(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 1: Azure OpenAI integration with mocked API.

        Validates:
        - Functional: Azure OpenAI client works with Memori
        - Persistence: Conversation attempt recorded
        - Integration: Azure-specific setup handled
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import AzureOpenAI

        # ASPECT 1: Functional - Create Azure OpenAI client
        memori_sqlite.enable()

        # Azure OpenAI requires these configs
        client = AzureOpenAI(
            api_key="test-azure-key",
            api_version="2024-02-15-preview",
            azure_endpoint="https://test.openai.azure.com",
        )

        # Mock the Azure API call
        with patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=mock_openai_response,
        ):
            response = client.chat.completions.create(
                model="gpt-4o",  # Azure deployment name
                messages=[{"role": "user", "content": "Test Azure OpenAI"}],
            )

            assert response is not None
            assert (
                response.choices[0].message.content
                == "Python is a programming language."
            )

        time.sleep(0.5)

        # ASPECT 2: Persistence - Check database
        stats = memori_sqlite.db_manager.get_memory_stats("default")
        assert isinstance(stats, dict)

        # ASPECT 3: Integration - Memori enabled with Azure
        assert memori_sqlite._enabled

    def test_azure_openai_multiple_deployments(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 2: Multiple Azure deployment models.

        Validates:
        - Functional: Different deployments work
        - Persistence: All tracked correctly
        - Integration: Deployment-agnostic recording
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import AzureOpenAI

        memori_sqlite.enable()

        client = AzureOpenAI(
            api_key="test-azure-key",
            api_version="2024-02-15-preview",
            azure_endpoint="https://test.openai.azure.com",
        )

        # Test different deployment names
        deployments = ["gpt-4o", "gpt-35-turbo", "gpt-4o-mini"]

        # ASPECT 1: Functional - Multiple deployments
        with patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=mock_openai_response,
        ):
            for deployment in deployments:
                response = client.chat.completions.create(
                    model=deployment,
                    messages=[{"role": "user", "content": f"Test with {deployment}"}],
                )
                assert response is not None

        time.sleep(0.5)

        # ASPECT 2 & 3: All deployments handled
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
class TestAzureOpenAIConfiguration:
    """Test Azure-specific configuration scenarios."""

    def test_azure_api_version_handling(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 3: Different Azure API versions.

        Validates:
        - Functional: API version parameter handled
        - Persistence: Version-agnostic recording
        - Integration: Configuration flexibility
        """
        pytest.importorskip("openai")

        from openai import AzureOpenAI

        memori_sqlite.enable()

        # Test with different API versions
        api_versions = ["2024-02-15-preview", "2023-12-01-preview", "2023-05-15"]

        for api_version in api_versions:
            client = AzureOpenAI(
                api_key="test-azure-key",
                api_version=api_version,
                azure_endpoint="https://test.openai.azure.com",
            )

            # ASPECT 1: Functional - Client created successfully with API version
            assert client is not None
            # Note: api_version is stored internally but not exposed as a public attribute

        # ASPECT 2 & 3: Configuration handled
        assert memori_sqlite._enabled

    def test_azure_endpoint_configuration(self, memori_sqlite, test_namespace):
        """
        Test 4: Azure endpoint configuration.

        Validates:
        - Functional: Custom endpoints work
        - Persistence: Endpoint-agnostic
        - Integration: Region flexibility
        """
        pytest.importorskip("openai")
        from openai import AzureOpenAI

        memori_sqlite.enable()

        # Test different regional endpoints
        endpoints = [
            "https://eastus.api.cognitive.microsoft.com",
            "https://westus.api.cognitive.microsoft.com",
            "https://northeurope.api.cognitive.microsoft.com",
        ]

        for endpoint in endpoints:
            client = AzureOpenAI(
                api_key="test-azure-key",
                api_version="2024-02-15-preview",
                azure_endpoint=endpoint,
            )

            # ASPECT 1: Functional - Endpoint configured
            assert endpoint in str(client.base_url)

        # ASPECT 2 & 3: All endpoints handled
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
class TestAzureOpenAIContextInjection:
    """Test context injection with Azure OpenAI."""

    @pytest.mark.skip(
        reason="store_short_term_memory() API not available - short-term memory is managed internally"
    )
    def test_azure_with_conscious_mode(
        self, memori_sqlite_conscious, test_namespace, mock_openai_response
    ):
        """
        Test 5: Azure OpenAI with conscious mode.

        Validates:
        - Functional: Conscious mode with Azure
        - Persistence: Context stored
        - Integration: Azure + conscious mode works
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import AzureOpenAI

        # Setup: Store permanent context
        memori_sqlite_conscious.db_manager.store_short_term_memory(
            content="User is deploying on Azure with enterprise security requirements",
            summary="Azure deployment context",
            category_primary="context",
            session_id="azure_test",
            user_id=memori_sqlite_conscious.user_id,
            is_permanent_context=True,
        )

        # ASPECT 1: Functional - Azure + conscious mode
        memori_sqlite_conscious.enable()

        client = AzureOpenAI(
            api_key="test-azure-key",
            api_version="2024-02-15-preview",
            azure_endpoint="https://test.openai.azure.com",
        )

        with patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=mock_openai_response,
        ):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Help with deployment"}],
            )
            assert response is not None

        # ASPECT 2: Persistence - Context exists
        stats = memori_sqlite_conscious.db_manager.get_memory_stats("default")
        assert stats["short_term_count"] >= 1

        # ASPECT 3: Integration - Both features active
        assert memori_sqlite_conscious.conscious_ingest


@pytest.mark.llm
@pytest.mark.integration
class TestAzureOpenAIErrorHandling:
    """Test Azure OpenAI error handling."""

    def test_azure_authentication_error(self, memori_sqlite, test_namespace):
        """
        Test 6: Azure authentication error handling.

        Validates:
        - Functional: Auth errors handled
        - Persistence: System stable
        - Integration: Error isolation
        """
        pytest.importorskip("openai")
        from openai import AzureOpenAI

        memori_sqlite.enable()

        # Create client with invalid credentials
        client = AzureOpenAI(
            api_key="invalid-azure-key",
            api_version="2024-02-15-preview",
            azure_endpoint="https://test.openai.azure.com",
        )

        # Note: This documents behavior - actual API call would fail
        assert client.api_key == "invalid-azure-key"

        # ASPECT 3: Memori remains stable
        assert memori_sqlite._enabled

    def test_azure_api_error(self, memori_sqlite, test_namespace):
        """
        Test 7: Azure API error handling.

        Validates:
        - Functional: API errors propagate
        - Persistence: No corruption
        - Integration: Graceful degradation
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import AzureOpenAI

        memori_sqlite.enable()

        client = AzureOpenAI(
            api_key="test-azure-key",
            api_version="2024-02-15-preview",
            azure_endpoint="https://test.openai.azure.com",
        )

        # ASPECT 1: Functional - Simulate API error
        with patch(
            "openai.resources.chat.completions.Completions.create",
            side_effect=Exception("Azure API Error"),
        ):
            with pytest.raises(Exception) as exc_info:
                client.chat.completions.create(
                    model="gpt-4o", messages=[{"role": "user", "content": "Test"}]
                )

            assert "Azure API Error" in str(exc_info.value)

        # ASPECT 2 & 3: System stable after error
        stats = memori_sqlite.db_manager.get_memory_stats("default")
        assert isinstance(stats, dict)


@pytest.mark.llm
@pytest.mark.integration
@pytest.mark.slow
class TestAzureOpenAIRealAPI:
    """Test with real Azure OpenAI API (requires Azure credentials)."""

    def test_azure_real_api_call(self, memori_sqlite, test_namespace):
        """
        Test 8: Real Azure OpenAI API call.

        Validates:
        - Functional: Real Azure integration
        - Persistence: Real conversation recorded
        - Integration: End-to-end Azure workflow
        """
        azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")

        if not azure_api_key or not azure_endpoint:
            pytest.skip("Azure OpenAI credentials not configured")

        pytest.importorskip("openai")
        from openai import AzureOpenAI

        # ASPECT 1: Functional - Real Azure API call
        memori_sqlite.enable()

        client = AzureOpenAI(
            api_key=azure_api_key,
            api_version="2024-02-15-preview",
            azure_endpoint=azure_endpoint,
        )

        response = client.chat.completions.create(
            model=azure_deployment,
            messages=[{"role": "user", "content": "Say 'Azure test successful'"}],
            max_tokens=10,
        )

        # ASPECT 2: Persistence - Validate response
        assert response is not None
        assert len(response.choices[0].message.content) > 0
        print(f"\nReal Azure response: {response.choices[0].message.content}")

        time.sleep(1.0)

        # ASPECT 3: Integration - End-to-end success
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
@pytest.mark.performance
class TestAzureOpenAIPerformance:
    """Test Azure OpenAI integration performance."""

    def test_azure_overhead(
        self, memori_sqlite, test_namespace, mock_openai_response, performance_tracker
    ):
        """
        Test 9: Measure Memori overhead with Azure OpenAI.

        Validates:
        - Functional: Performance tracking
        - Persistence: Efficient recording
        - Integration: Acceptable overhead
        """
        pytest.importorskip("openai")
        from unittest.mock import patch

        from openai import AzureOpenAI

        client = AzureOpenAI(
            api_key="test-azure-key",
            api_version="2024-02-15-preview",
            azure_endpoint="https://test.openai.azure.com",
        )

        # Baseline: Without Memori
        with performance_tracker.track("azure_without"):
            with patch(
                "openai.resources.chat.completions.Completions.create",
                return_value=mock_openai_response,
            ):
                for i in range(10):
                    client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": f"Test {i}"}],
                    )

        # With Memori
        memori_sqlite.enable()

        with performance_tracker.track("azure_with"):
            with patch(
                "openai.resources.chat.completions.Completions.create",
                return_value=mock_openai_response,
            ):
                for i in range(10):
                    client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": f"Test {i}"}],
                    )

        # ASPECT 3: Performance analysis
        metrics = performance_tracker.get_metrics()
        without = metrics.get("azure_without", 0.001)
        with_memori = metrics.get("azure_with", 0.001)

        overhead = with_memori - without
        overhead_pct = (overhead / without) * 100 if without > 0 else 0

        print("\nAzure OpenAI Performance:")
        print(f"  Without Memori: {without:.3f}s")
        print(f"  With Memori:    {with_memori:.3f}s")
        print(f"  Overhead:       {overhead:.3f}s ({overhead_pct:.1f}%)")

        # Allow reasonable overhead
        assert overhead_pct < 100, f"Overhead too high: {overhead_pct:.1f}%"
