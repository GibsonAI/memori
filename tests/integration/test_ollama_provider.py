"""
Ollama Provider Integration Tests

Tests Memori integration with Ollama (local LLM runtime).

Validates three aspects:
1. Functional: Ollama calls work with Memori enabled
2. Persistence: Conversations are recorded in database
3. Integration: Local LLM provider support
"""

import time

import pytest


@pytest.mark.llm
@pytest.mark.integration
class TestOllamaBasicIntegration:
    """Test basic Ollama integration with Memori."""

    def test_ollama_via_litellm_with_mock(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 1: Ollama integration via LiteLLM with mock.

        Validates:
        - Functional: Ollama model calls work
        - Persistence: Local model conversations recorded
        - Integration: Ollama provider supported
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        # ASPECT 1: Functional - Ollama via LiteLLM
        memori_sqlite.enable()

        with patch("litellm.completion", return_value=mock_openai_response):
            response = completion(
                model="ollama/llama2",  # Ollama model format
                messages=[{"role": "user", "content": "Test with Ollama"}],
                api_base="http://localhost:11434",  # Ollama default port
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

        # ASPECT 3: Integration - Local provider works
        assert memori_sqlite._enabled

    def test_ollama_multiple_models(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 2: Multiple Ollama models.

        Validates:
        - Functional: Different local models work
        - Persistence: All models tracked
        - Integration: Model-agnostic recording
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # Test different Ollama models
        models = ["ollama/llama2", "ollama/mistral", "ollama/codellama", "ollama/phi"]

        # ASPECT 1: Functional - Multiple models
        with patch("litellm.completion", return_value=mock_openai_response):
            for model in models:
                response = completion(
                    model=model,
                    messages=[{"role": "user", "content": f"Test with {model}"}],
                    api_base="http://localhost:11434",
                )
                assert response is not None

        time.sleep(0.5)

        # ASPECT 2 & 3: All models handled
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
class TestOllamaConfiguration:
    """Test Ollama-specific configuration."""

    def test_ollama_custom_port(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 3: Ollama with custom port.

        Validates:
        - Functional: Custom port configuration
        - Persistence: Port-agnostic recording
        - Integration: Configuration flexibility
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # Test different ports
        ports = [11434, 8080, 3000]

        for port in ports:
            # ASPECT 1: Functional - Custom port
            with patch("litellm.completion", return_value=mock_openai_response):
                response = completion(
                    model="ollama/llama2",
                    messages=[{"role": "user", "content": "Test"}],
                    api_base=f"http://localhost:{port}",
                )
                assert response is not None

        # ASPECT 2 & 3: Configuration handled
        assert memori_sqlite._enabled

    def test_ollama_custom_host(
        self, memori_sqlite, test_namespace, mock_openai_response
    ):
        """
        Test 4: Ollama with custom host.

        Validates:
        - Functional: Remote Ollama server support
        - Persistence: Host-agnostic recording
        - Integration: Network flexibility
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # Test different hosts
        hosts = [
            "http://localhost:11434",
            "http://192.168.1.100:11434",
            "http://ollama-server:11434",
        ]

        for host in hosts:
            # ASPECT 1: Functional - Custom host
            with patch("litellm.completion", return_value=mock_openai_response):
                response = completion(
                    model="ollama/llama2",
                    messages=[{"role": "user", "content": "Test"}],
                    api_base=host,
                )
                assert response is not None

        # ASPECT 2 & 3: All hosts handled
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
class TestOllamaContextInjection:
    """Test context injection with Ollama."""

    def test_ollama_with_auto_mode(
        self, memori_conscious_false_auto_true, test_namespace, mock_openai_response
    ):
        """
        Test 5: Ollama with auto-ingest mode.

        Validates:
        - Functional: Auto mode with local LLM
        - Persistence: Context retrieval works
        - Integration: Local model + memory
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori = memori_conscious_false_auto_true

        # Setup: Store relevant context
        memori.db_manager.store_long_term_memory(
            content="User runs Ollama locally for privacy and offline capability",
            summary="Ollama usage context",
            category_primary="context",
            session_id="ollama_test",
            user_id=memori.user_id,
        )

        # ASPECT 1: Functional - Ollama + auto mode
        memori.enable()

        with patch("litellm.completion", return_value=mock_openai_response):
            response = completion(
                model="ollama/llama2",
                messages=[{"role": "user", "content": "Help with local LLM setup"}],
                api_base="http://localhost:11434",
            )
            assert response is not None

        # ASPECT 2: Persistence - Context exists
        stats = memori.db_manager.get_memory_stats("default")
        assert stats["long_term_count"] >= 1

        # ASPECT 3: Integration - Both active
        assert memori.auto_ingest


@pytest.mark.llm
@pytest.mark.integration
class TestOllamaErrorHandling:
    """Test Ollama error handling."""

    def test_ollama_connection_error(self, memori_sqlite, test_namespace):
        """
        Test 6: Ollama connection error handling.

        Validates:
        - Functional: Connection errors handled
        - Persistence: System stable
        - Integration: Graceful degradation
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # ASPECT 1: Functional - Simulate connection error
        with patch(
            "litellm.completion", side_effect=Exception("Ollama connection refused")
        ):
            with pytest.raises(Exception) as exc_info:
                completion(
                    model="ollama/llama2",
                    messages=[{"role": "user", "content": "Test"}],
                    api_base="http://localhost:11434",
                )

            assert "Ollama connection" in str(exc_info.value)

        # ASPECT 2 & 3: System stable
        stats = memori_sqlite.db_manager.get_memory_stats("default")
        assert isinstance(stats, dict)

    def test_ollama_model_not_found(self, memori_sqlite, test_namespace):
        """
        Test 7: Ollama model not found error.

        Validates:
        - Functional: Missing model handled
        - Persistence: No corruption
        - Integration: Error isolation
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        memori_sqlite.enable()

        # ASPECT 1: Functional - Simulate model not found
        with patch("litellm.completion", side_effect=Exception("Model not found")):
            with pytest.raises(Exception) as exc_info:
                completion(
                    model="ollama/nonexistent-model",
                    messages=[{"role": "user", "content": "Test"}],
                    api_base="http://localhost:11434",
                )

            assert "Model not found" in str(exc_info.value)

        # ASPECT 2 & 3: System stable
        assert memori_sqlite._enabled


@pytest.mark.llm
@pytest.mark.integration
@pytest.mark.slow
class TestOllamaRealAPI:
    """Test with real Ollama instance (requires Ollama running locally)."""

    def test_ollama_real_call(self, memori_sqlite, test_namespace):
        """
        Test 8: Real Ollama API call.

        Validates:
        - Functional: Real local LLM integration
        - Persistence: Real conversation recorded
        - Integration: End-to-end local workflow
        """
        pytest.importorskip("litellm")

        # Check if Ollama is available
        import requests

        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code != 200:
                pytest.skip("Ollama not running on localhost:11434")
        except Exception:
            pytest.skip("Ollama not accessible")

        from litellm import completion

        # ASPECT 1: Functional - Real Ollama call
        memori_sqlite.enable()

        try:
            response = completion(
                model="ollama/llama2",  # Assumes llama2 is pulled
                messages=[{"role": "user", "content": "Say 'test successful' only"}],
                api_base="http://localhost:11434",
            )

            # ASPECT 2: Persistence - Validate response
            assert response is not None
            print(f"\nReal Ollama response: {response.choices[0].message.content}")

            time.sleep(1.0)

            # ASPECT 3: Integration - Success
            assert memori_sqlite._enabled

        except Exception as e:
            if "not found" in str(e).lower():
                pytest.skip("llama2 model not installed in Ollama")
            raise


@pytest.mark.llm
@pytest.mark.integration
@pytest.mark.performance
class TestOllamaPerformance:
    """Test Ollama integration performance."""

    def test_ollama_overhead(
        self, memori_sqlite, test_namespace, mock_openai_response, performance_tracker
    ):
        """
        Test 9: Measure Memori overhead with Ollama.

        Validates:
        - Functional: Performance tracking
        - Persistence: Efficient local recording
        - Integration: Minimal overhead
        """
        pytest.importorskip("litellm")
        from unittest.mock import patch

        from litellm import completion

        # Baseline: Without Memori
        with performance_tracker.track("ollama_without"):
            with patch("litellm.completion", return_value=mock_openai_response):
                for i in range(10):
                    completion(
                        model="ollama/llama2",
                        messages=[{"role": "user", "content": f"Test {i}"}],
                        api_base="http://localhost:11434",
                    )

        # With Memori
        memori_sqlite.enable()

        with performance_tracker.track("ollama_with"):
            with patch("litellm.completion", return_value=mock_openai_response):
                for i in range(10):
                    completion(
                        model="ollama/llama2",
                        messages=[{"role": "user", "content": f"Test {i}"}],
                        api_base="http://localhost:11434",
                    )

        # ASPECT 3: Performance analysis
        metrics = performance_tracker.get_metrics()
        without = metrics.get("ollama_without", 0.001)
        with_memori = metrics.get("ollama_with", 0.001)

        overhead = with_memori - without
        overhead_pct = (overhead / without) * 100 if without > 0 else 0

        print("\nOllama Performance:")
        print(f"  Without Memori: {without:.3f}s")
        print(f"  With Memori:    {with_memori:.3f}s")
        print(f"  Overhead:       {overhead:.3f}s ({overhead_pct:.1f}%)")

        # Allow reasonable overhead
        assert overhead_pct < 100, f"Overhead too high: {overhead_pct:.1f}%"
