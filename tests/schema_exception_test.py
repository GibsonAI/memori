#!/usr/bin/env python3
"""
A very simple test for schema initialization exception
logging and fallback to the basic schema
"""

from loguru import logger
import sys
import tempfile
from pathlib import Path

# Add the memori package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_schema_exception_logging():
    """Test that schema initialization exceptions are logged with traceback and fallback to the basic schema"""
    print("🧪 Testing schema exception logging and fallback to the basic schema...")

    temp_path = None

    try:
        from memori.core.database import DatabaseManager

        # Create temp database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            temp_path = f.name

        # Create a list to store the log messages
        captured_logs = []

        # Create a handler that captures the log messages
        def capture_log(message):
            captured_logs.append(message.strip())

        # Add the custom handler to the logger
        logger.add(capture_log, level="TRACE")

        # Test with invalid template (this will trigger the fallback)
        db_manager = DatabaseManager(
            database_connect=f"sqlite:///{temp_path}",
            template="basic"
        )

        # Initialize schema (it should fail and log errors then fallback to the basic schema)
        db_manager.initialize_schema()

        # Verify it worked by checking tables exist
        with db_manager._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            assert 'chat_history' in tables, "Fallback schema creation did NOT work"

        assert len(captured_logs) > 0, "No logs captured"

        assert any("Schema execution issue" in log for log in captured_logs), "Schema execution issue log not found"
        assert any("Schema execution error details: Traceback" in log for log in captured_logs), "Schema execution error details: Traceback log not found"

        assert any("Schema statement error" in log for log in captured_logs), "Schema statement error log not found"
        assert any("Schema statement error details: Traceback" in log for log in captured_logs), "Schema statement error details: Traceback log not found"

        print("✅ Schema exception logging and fallback works")
        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    finally:
        if temp_path and Path(temp_path).exists():
            Path(temp_path).unlink(missing_ok=True)


def main():
    """Main test function"""
    print("🚀 Schema Exception Logging Test")
    print("=" * 40)

    success = test_schema_exception_logging()

    if success:
        print("\n✅ Schema exception logging test passed!")
        return 0
    else:
        print("\n❌ Schema exception logging test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
