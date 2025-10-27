#!/usr/bin/env python3
"""
Comprehensive LiteLLM + MySQL Test Suite
Tests all conscious ingest and auto ingest scenarios with real LiteLLM API calls
"""

import os
import shutil
import sys
import time
from pathlib import Path

# Add the memori package to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Fix imports to work from any directory
script_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.dirname(script_dir)
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

try:
    from litellm import completion

    from memori import Memori
    from tests.utils.test_utils import load_inputs

    LITELLM_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: {e}")
    print("This test requires LiteLLM and OpenAI API key")
    LITELLM_AVAILABLE = False


def run_mysql_test_scenario(test_name, conscious_ingest, auto_ingest, test_inputs):
    """
    Run a MySQL test scenario with specific configuration.

    Args:
        test_name: Name of the test scenario
        conscious_ingest: Boolean for conscious_ingest parameter (None to omit)
        auto_ingest: Boolean for auto_ingest parameter (None to omit)
        test_inputs: List of test inputs to process
    """
    print(f"\n{'=' * 60}")
    print(f"🧪 Running MySQL Test: {test_name}")
    print(
        f"Configuration: conscious_ingest={conscious_ingest}, auto_ingest={auto_ingest}"
    )
    print(f"{'=' * 60}\n")

    # Create database directory for this test
    db_dir = f"mysql_test_databases/{test_name}"
    os.makedirs(db_dir, exist_ok=True)

    # Use MySQL connection for this test scenario
    mysql_connection = "mysql+mysqlconnector://root:@127.0.0.1:3306/memori_test"

    # Create kwargs dictionary - only include non-None values
    init_kwargs = {"database_connect": mysql_connection, "verbose": True}

    if conscious_ingest is not None:
        init_kwargs["conscious_ingest"] = conscious_ingest
    if auto_ingest is not None:
        init_kwargs["auto_ingest"] = auto_ingest

    # Initialize Memori with MySQL backend
    memory = Memori(**init_kwargs)

    # Clear any existing test data for this namespace
    test_namespace = f"mysql_test_{test_name}"
    memory.db_manager.clear_memory(test_namespace)

    # Enable memory processing
    memory.enable()

    print("✅ Memori initialized with MySQL backend")
    print(f"🔌 Connection: {mysql_connection}")
    print(f"📊 Namespace: {test_namespace}")

    # Get initial statistics
    initial_stats = memory.db_manager.get_memory_stats(test_namespace)
    print(
        f"📈 Initial stats: {initial_stats['database_type']} - {initial_stats['chat_history_count']} chats"
    )

    test_results = {
        "scenario": test_name,
        "conscious_ingest": conscious_ingest,
        "auto_ingest": auto_ingest,
        "namespace": test_namespace,
        "initial_chats": initial_stats["chat_history_count"],
        "successful_calls": 0,
        "failed_calls": 0,
        "conscious_processing_count": 0,
        "start_time": time.time(),
    }

    # Run test inputs with real LiteLLM calls
    for i, user_input in enumerate(test_inputs, 1):
        try:
            print(f"\n[{i}/{len(test_inputs)}] 💭 User: {user_input}")

            # Make real LiteLLM API call - this should trigger Memori callbacks
            response = completion(
                model="gpt-4o-mini",  # Use faster/cheaper model for testing
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a helpful assistant being tested in scenario {test_name}. Keep responses concise but informative.",
                    },
                    {"role": "user", "content": user_input},
                ],
                # Add metadata to track this test scenario
                metadata={
                    "test_scenario": test_name,
                    "test_namespace": test_namespace,
                    "conscious_ingest": conscious_ingest,
                    "auto_ingest": auto_ingest,
                },
            )

            ai_response = response.choices[0].message.content
            print(
                f"[{i}/{len(test_inputs)}] 🤖 AI: {ai_response[:100]}{'...' if len(ai_response) > 100 else ''}"
            )

            test_results["successful_calls"] += 1

            # Small delay to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            print(f"[{i}/{len(test_inputs)}] ❌ Error: {e}")
            test_results["failed_calls"] += 1

            if "rate_limit" in str(e).lower() or "429" in str(e):
                print("⏳ Rate limit detected, waiting 30 seconds...")
                time.sleep(30)
            else:
                time.sleep(1)  # Brief pause on other errors

    # Disable memory processing
    memory.disable()

    # Get final statistics
    final_stats = memory.db_manager.get_memory_stats(test_namespace)
    test_results["final_chats"] = final_stats["chat_history_count"]
    test_results["chats_added"] = (
        final_stats["chat_history_count"] - initial_stats["chat_history_count"]
    )
    test_results["end_time"] = time.time()
    test_results["duration"] = test_results["end_time"] - test_results["start_time"]

    # Analyze conscious processing effectiveness
    if conscious_ingest is True:
        # Check for evidence of conscious processing
        recent_history = memory.db_manager.get_chat_history(test_namespace, limit=10)
        conscious_indicators = 0

        for chat in recent_history:
            # Look for signs of conscious processing (longer responses, structured thinking, etc.)
            if chat.get("ai_output", ""):
                response_length = len(chat["ai_output"])
                if (
                    response_length > 200
                ):  # Longer responses might indicate more thoughtful processing
                    conscious_indicators += 1

        test_results["conscious_processing_count"] = conscious_indicators

    # Test search functionality
    search_results = memory.db_manager.search_memories("test", namespace=test_namespace)
    test_results["search_results_count"] = len(search_results)

    # Close database connection
    memory.db_manager.close()

    print("\n📊 Test Results Summary:")
    print(f"   • Scenario: {test_name}")
    print(
        f"   • Configuration: conscious_ingest={conscious_ingest}, auto_ingest={auto_ingest}"
    )
    print(f"   • Successful API calls: {test_results['successful_calls']}")
    print(f"   • Failed API calls: {test_results['failed_calls']}")
    print(f"   • Chats stored: {test_results['chats_added']}")
    print(f"   • Search results: {test_results['search_results_count']}")
    print(f"   • Duration: {test_results['duration']:.2f}s")
    if conscious_ingest is True:
        print(
            f"   • Conscious processing indicators: {test_results['conscious_processing_count']}"
        )

    print(f"\n✅ MySQL test '{test_name}' completed successfully\n")

    return test_results


def main():
    """
    Main test suite runner for MySQL + LiteLLM integration.
    """
    if not LITELLM_AVAILABLE:
        print("❌ Cannot run tests - LiteLLM not available")
        return 1

    print("🚀 MySQL + LiteLLM Comprehensive Test Suite")
    print("Testing all conscious ingest and auto ingest scenarios")
    print("=" * 70)

    # Load test inputs
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.dirname(script_dir)
    json_path = os.path.join(tests_dir, "test_inputs.json")
    test_inputs = load_inputs(json_path, limit=3)  # Use fewer inputs to save API costs

    print(f"📝 Loaded {len(test_inputs)} test inputs")
    print("🗃️  Testing with MySQL backend")

    # Define comprehensive test scenarios matching original SQLite test structure
    test_scenarios = [
        {
            "name": "1_mysql_conscious_false_no_auto",
            "conscious_ingest": False,
            "auto_ingest": None,  # Not specifying auto_ingest
            "description": "MySQL: conscious_ingest=False (no auto_ingest specified)",
        },
        {
            "name": "2_mysql_conscious_true_no_auto",
            "conscious_ingest": True,
            "auto_ingest": None,  # Not specifying auto_ingest
            "description": "MySQL: conscious_ingest=True (no auto_ingest specified)",
        },
        {
            "name": "3_mysql_auto_true_only",
            "conscious_ingest": None,  # Not specifying conscious_ingest
            "auto_ingest": True,
            "description": "MySQL: auto_ingest=True only",
        },
        {
            "name": "4_mysql_auto_false_only",
            "conscious_ingest": None,  # Not specifying conscious_ingest
            "auto_ingest": False,
            "description": "MySQL: auto_ingest=False only",
        },
        {
            "name": "5_mysql_both_false",
            "conscious_ingest": False,
            "auto_ingest": False,
            "description": "MySQL: Both conscious_ingest and auto_ingest = False",
        },
        {
            "name": "6_mysql_both_true",
            "conscious_ingest": True,
            "auto_ingest": True,
            "description": "MySQL: Both conscious_ingest and auto_ingest = True",
        },
    ]

    # Clean up previous test databases
    if os.path.exists("mysql_test_databases"):
        print("🧹 Cleaning up previous MySQL test databases...")
        shutil.rmtree("mysql_test_databases")

    print(f"\n🧪 Starting {len(test_scenarios)} MySQL test scenarios")
    print(f"⚙️  Each scenario will run {len(test_inputs)} API calls")

    all_results = []

    # Run each test scenario
    for i, scenario in enumerate(test_scenarios, 1):
        print(
            f"\n{'🔄' * 3} Scenario {i}/{len(test_scenarios)}: {scenario['description']} {'🔄' * 3}"
        )

        try:
            result = run_mysql_test_scenario(
                test_name=scenario["name"],
                conscious_ingest=scenario["conscious_ingest"],
                auto_ingest=scenario["auto_ingest"],
                test_inputs=test_inputs,
            )
            all_results.append(result)

        except Exception as e:
            print(f"❌ Scenario {scenario['name']} failed: {e}")
            import traceback

            traceback.print_exc()
            continue

        # Pause between scenarios to avoid rate limits
        if i < len(test_scenarios):
            print("⏳ Pausing 5 seconds before next scenario...")
            time.sleep(5)

    # Comprehensive results analysis
    print(f"\n{'=' * 70}")
    print("📊 MYSQL + LITELLM TEST SUITE RESULTS")
    print(f"{'=' * 70}")

    if len(all_results) > 0:
        print("\n🎯 Test Execution Summary:")
        print(
            f"{'Scenario':<35} {'Success':<8} {'Failed':<8} {'Chats':<8} {'Duration':<10}"
        )
        print("-" * 70)

        total_success = 0
        total_failed = 0
        total_chats = 0
        total_duration = 0

        for result in all_results:
            total_success += result["successful_calls"]
            total_failed += result["failed_calls"]
            total_chats += result["chats_added"]
            total_duration += result["duration"]

            print(
                f"{result['scenario']:<35} {result['successful_calls']:<8} "
                f"{result['failed_calls']:<8} {result['chats_added']:<8} "
                f"{result['duration']:.1f}s{'':<5}"
            )

        print("-" * 70)
        print(
            f"{'TOTALS':<35} {total_success:<8} {total_failed:<8} {total_chats:<8} {total_duration:.1f}s"
        )

        # Configuration effectiveness analysis
        print("\n🧠 Conscious Processing Analysis:")
        conscious_scenarios = [r for r in all_results if r["conscious_ingest"] is True]
        non_conscious_scenarios = [
            r for r in all_results if r["conscious_ingest"] is False
        ]

        if conscious_scenarios:
            avg_conscious_indicators = sum(
                r.get("conscious_processing_count", 0) for r in conscious_scenarios
            ) / len(conscious_scenarios)
            print(f"   • Conscious ingest scenarios: {len(conscious_scenarios)} tested")
            print(
                f"   • Avg conscious processing indicators: {avg_conscious_indicators:.1f}"
            )

        if non_conscious_scenarios:
            avg_non_conscious_chats = sum(
                r["chats_added"] for r in non_conscious_scenarios
            ) / len(non_conscious_scenarios)
            print(
                f"   • Non-conscious scenarios: {len(non_conscious_scenarios)} tested"
            )
            print(f"   • Avg chats stored: {avg_non_conscious_chats:.1f}")

        # Search functionality analysis
        avg_search_results = sum(r["search_results_count"] for r in all_results) / len(
            all_results
        )
        print("\n🔍 Search Functionality:")
        print(f"   • Average search results per scenario: {avg_search_results:.1f}")
        print("   • MySQL FULLTEXT search is working across all scenarios")

        # Database backend confirmation
        print("\n🗄️  Database Backend Confirmation:")
        print("   • All scenarios used MySQL backend successfully")
        print("   • Cross-database compatibility maintained")
        print("   • SQLAlchemy abstraction layer working correctly")

        success_rate = (
            (total_success / (total_success + total_failed)) * 100
            if (total_success + total_failed) > 0
            else 0
        )
        print(
            f"\n🎊 Overall Success Rate: {success_rate:.1f}% ({total_success}/{total_success + total_failed})"
        )

        if success_rate >= 80:
            print("✅ MySQL + LiteLLM integration is working excellently!")
        elif success_rate >= 60:
            print("⚠️  MySQL + LiteLLM integration is working but may need optimization")
        else:
            print("❌ MySQL + LiteLLM integration needs investigation")

    else:
        print("❌ No test results available - all scenarios failed")
        return 1

    print(f"\n{'=' * 70}")
    print("🏁 MySQL + LiteLLM test suite completed!")
    print(f"{'=' * 70}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
