"""
Tests for the _is_internal_agent_call method in OpenAIInterceptor.

This test module focuses on testing the logic that determines whether
an OpenAI API call is an internal agent processing call that should
not be recorded to memory.
"""

import os
import sys

# Fix imports to work from any directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest  # noqa: E402

from memori.integrations.openai_integration import OpenAIInterceptor  # noqa: E402


class TestIsInternalAgentCall:
    """Test cases for the _is_internal_agent_call method."""

    def test_empty_json_data(self):
        """Test with empty json_data - should return False."""
        json_data = {}
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_no_metadata(self):
        """Test with json_data that has no metadata field - should return False."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_empty_metadata(self):
        """Test with empty metadata list - should return False."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "metadata": [],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_non_list_metadata(self):
        """Test with metadata that is not a list - should return False."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "metadata": "not_a_list",
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_metadata_dict_instead_of_list(self):
        """Test with metadata as dict instead of list - should return False."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Hello"}],
            "metadata": {"type": "regular_call"},
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_internal_memory_processing_flag(self):
        """Test with INTERNAL_MEMORY_PROCESSING flag - should return True."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Process this memory"}],
            "metadata": ["INTERNAL_MEMORY_PROCESSING"],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is True

    def test_agent_processing_mode_flag(self):
        """Test with AGENT_PROCESSING_MODE flag - should return True."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "system", "content": "Agent processing task"}],
            "metadata": ["AGENT_PROCESSING_MODE"],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is True

    def test_memory_agent_task_flag(self):
        """Test with MEMORY_AGENT_TASK flag - should return True."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Memory agent task"}],
            "metadata": ["MEMORY_AGENT_TASK"],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is True

    def test_multiple_flags_with_internal(self):
        """Test with multiple flags including internal ones - should return True."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Complex processing"}],
            "metadata": [
                "SOME_OTHER_FLAG",
                "INTERNAL_MEMORY_PROCESSING",
                "ANOTHER_FLAG",
            ],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is True

    def test_multiple_internal_flags(self):
        """Test with multiple internal flags - should return True."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Multi-flag processing"}],
            "metadata": [
                "INTERNAL_MEMORY_PROCESSING",
                "AGENT_PROCESSING_MODE",
                "MEMORY_AGENT_TASK",
            ],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is True

    def test_non_internal_flags(self):
        """Test with non-internal flags only - should return False."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Regular user request"}],
            "metadata": ["USER_REQUEST", "REGULAR_PROCESSING", "EXTERNAL_API_CALL"],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_case_sensitive_flags(self):
        """Test that flag matching is case sensitive - should return False for wrong case."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Case test"}],
            "metadata": [
                "internal_memory_processing",  # lowercase
                "agent_processing_mode",  # lowercase
                "memory_agent_task",  # lowercase
            ],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_partial_flag_matches(self):
        """Test with flags that are substrings of internal flags - should return False."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Partial match test"}],
            "metadata": [
                "INTERNAL_MEMORY",  # partial match
                "AGENT_PROCESSING",  # partial match
                "MEMORY_AGENT",  # partial match
            ],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_exception_handling(self):
        """Test that exceptions are handled gracefully and return False."""
        # Pass None instead of dict to trigger exception
        result = OpenAIInterceptor._is_internal_agent_call(None)
        assert result is False

    def test_malformed_json_data(self):
        """Test with malformed json_data - should handle gracefully."""
        # Test with circular reference that might cause issues
        json_data = {"metadata": []}
        json_data["self_reference"] = json_data  # Circular reference

        # Should still work for basic metadata check
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_real_world_user_request(self):
        """Test with realistic user request data - should return False."""
        json_data = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"},
            ],
            "temperature": 0.7,
            "max_tokens": 150,
            "metadata": [],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_real_world_internal_agent_request(self):
        """Test with realistic internal agent request data - should return True."""
        json_data = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": "You are processing memories for the Memori system.",
                },
                {
                    "role": "user",
                    "content": "Process and summarize the following conversation memories...",
                },
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
            "metadata": ["INTERNAL_MEMORY_PROCESSING", "AUTO_PROCESSING"],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is True

    def test_edge_case_empty_string_in_metadata(self):
        """Test with empty strings in metadata - should return False."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
            "metadata": ["", "   ", "SOME_FLAG"],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is False

    def test_edge_case_none_values_in_metadata(self):
        """Test with None values in metadata list - should handle gracefully."""
        json_data = {
            "model": "gpt-4",
            "messages": [{"role": "user", "content": "Test"}],
            "metadata": [None, "INTERNAL_MEMORY_PROCESSING", None],
        }
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        assert result is True


def run_manual_tests():
    """Run tests manually if pytest is not available."""
    test_class = TestIsInternalAgentCall()

    test_methods = [
        method
        for method in dir(test_class)
        if method.startswith("test_") and callable(getattr(test_class, method))
    ]

    passed = 0
    failed = 0

    print("Running _is_internal_agent_call tests manually...")
    print("=" * 60)

    for method_name in test_methods:
        try:
            method = getattr(test_class, method_name)
            method()
            print(f"✓ {method_name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {method_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {method_name}: Unexpected error - {e}")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed!")
    else:
        print(f"❌ {failed} tests failed")

    return failed == 0


if __name__ == "__main__":
    # Try to run with pytest first, fall back to manual testing
    try:
        import pytest

        print("Running tests with pytest...")
        exit_code = pytest.main([__file__, "-v"])
        exit(exit_code)
    except ImportError:
        print("pytest not available, running manual tests...")
        success = run_manual_tests()
        exit(0 if success else 1)
