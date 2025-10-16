"""
Unit tests for OpenAI Integration - Fix for Issue #106
Tests the infinite loop prevention in message recording.
"""

import unittest

from memori.integrations.openai_integration import OpenAIInterceptor


class TestOpenAIIntegrationInfiniteLoopFix(unittest.TestCase):
    """Test cases for issue #106 - infinite loop prevention."""

    def test_internal_agent_call_with_user_role(self):
        """Test that user messages with internal patterns are not filtered."""
        json_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "Process this conversation for enhanced memory storage: Hello world",
                }
            ]
        }

        # Should NOT be flagged as internal (user messages should be recorded)
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        self.assertFalse(
            result, "User messages with internal patterns should not be filtered"
        )

    def test_internal_agent_call_without_user_role(self):
        """Test that non-user messages with internal patterns ARE filtered."""
        json_data = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "Process this conversation for enhanced memory storage: Analysis...",
                }
            ]
        }

        # Should be flagged as internal
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        self.assertTrue(
            result, "Non-user messages with internal patterns should be filtered"
        )

    def test_normal_user_message(self):
        """Test that normal user messages are not filtered."""
        json_data = {"messages": [{"role": "user", "content": "Hello, how are you?"}]}

        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        self.assertFalse(result, "Normal user messages should not be filtered")

    def test_multiple_messages_with_mixed_roles(self):
        """Test handling of multiple messages with different roles."""
        json_data = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
                {
                    "role": "user",
                    "content": "Process this conversation for enhanced memory storage: test",
                },
                {"role": "system", "content": "INTERNAL_MEMORY_PROCESSING: data"},
            ]
        }

        # Should be flagged as internal due to system message
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        self.assertTrue(result, "Should detect internal patterns in non-user messages")

    def test_no_infinite_loop_on_user_with_pattern(self):
        """Test that the fix prevents infinite loop with user messages containing patterns."""
        json_data = {
            "messages": [
                {
                    "role": "user",
                    "content": "INTERNAL_MEMORY_PROCESSING: user asking about this",
                }
            ]
        }

        # This should complete without hanging (no infinite loop)
        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        self.assertFalse(result, "Should not enter infinite loop with user messages")

    def test_empty_messages(self):
        """Test handling of empty messages list."""
        json_data = {"messages": []}

        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        self.assertFalse(result, "Empty messages should not be flagged as internal")

    def test_missing_messages_key(self):
        """Test handling of missing 'messages' key."""
        json_data = {}

        result = OpenAIInterceptor._is_internal_agent_call(json_data)
        self.assertFalse(
            result, "Missing messages key should not be flagged as internal"
        )


if __name__ == "__main__":
    unittest.main()
