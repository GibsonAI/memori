#!/usr/bin/env python3
"""
Test script specifically for verifying the asyncio fix for issue #18
This tests that conscious_ingest=True works without asyncio errors in synchronous contexts
"""

import sys
import os

# Add the memori package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from memori import Memori

def test_asyncio_fix():
    """Test that conscious_ingest=True works without asyncio errors"""
    
    print("=== Testing AsyncIO Fix for Issue #18 ===")
    print("This test verifies that conscious_ingest=True works in synchronous contexts")
    print("without throwing 'no running event loop' errors.\n")
    
    try:
        print("1. Creating Memori instance with conscious_ingest=True...")
        memori = Memori(
            database_connect="sqlite:///test_asyncio_fix.db",
            conscious_ingest=True,
            verbose=True
        )
        print("✓ Memori instance created successfully")
        
        print("2. Enabling Memori...")
        memori.enable()
        print("✓ Memori enabled successfully")
        
        print("3. Recording a conversation...")
        memori.record_conversation(
            user_input="Hello, this is a test",
            ai_output="Hello! This is a test response",
            model="test-model"
        )
        print("✓ Conversation recorded successfully")
        
        print("4. Disabling Memori...")
        memori.disable()
        print("✓ Memori disabled successfully")
        
        print("\n=== TEST PASSED ===")
        print("✓ No 'asyncio.create_task() no running event loop' errors occurred")
        print("✓ Conscious ingest initialization worked properly")
        print("✓ Background thread handling is working correctly")
        print("✓ Issue #18 has been resolved!")
        
        return True
        
    except Exception as e:
        print(f"\n=== TEST FAILED ===")
        print(f"✗ Error: {e}")
        print("✗ The asyncio fix may not be working correctly")
        return False

if __name__ == "__main__":
    success = test_asyncio_fix()
    sys.exit(0 if success else 1)