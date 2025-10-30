import os
import shutil
import sys
import time

from openai import OpenAI

from memori import Memori

# Fix imports to work from any directory
script_dir = os.path.dirname(os.path.abspath(__file__))
tests_dir = os.path.dirname(script_dir)
if tests_dir not in sys.path:
    sys.path.insert(0, tests_dir)

from tests.utils.test_utils import load_inputs  # noqa: E402


def validate_openai_config():
    """
    Validate OpenAI configuration from environment variables.
    Returns tuple (is_valid, config_dict)
    """
    config = {
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o"),
        "base_url": os.getenv("OPENAI_BASE_URL"),  # Optional custom base URL
        "organization": os.getenv("OPENAI_ORGANIZATION"),  # Optional organization
    }

    is_valid = bool(config["api_key"]) and not config["api_key"].startswith("sk-your-")

    return is_valid, config


def run_openai_test_scenario(
    test_name, conscious_ingest, auto_ingest, test_inputs, openai_config
):
    """
    Run a standard OpenAI test scenario with specific configuration.

    Args:
        test_name: Name of the test scenario
        conscious_ingest: Boolean for conscious_ingest parameter
        auto_ingest: Boolean for auto_ingest parameter
        test_inputs: List of test inputs to process
        openai_config: OpenAI configuration dictionary
    """
    print(f"\n{'='*60}")
    print(f"Running OpenAI Test: {test_name}")
    print(
        f"Configuration: conscious_ingest={conscious_ingest}, auto_ingest={auto_ingest}"
    )
    print(f"Model: {openai_config['model']}")
    if openai_config["base_url"]:
        print(f"Base URL: {openai_config['base_url']}")
    if openai_config["organization"]:
        print(f"Organization: {openai_config['organization']}")
    print(f"{'='*60}\n")

    # Create database directory for this test
    db_dir = f"test_databases_openai/{test_name}"
    os.makedirs(db_dir, exist_ok=True)
    db_path = f"{db_dir}/memory.db"

    # Initialize Memori with specific configuration
    memory = Memori(
        database_connect=f"sqlite:///{db_path}",
        conscious_ingest=conscious_ingest,
        auto_ingest=auto_ingest,
        verbose=True,
    )

    memory.enable()

    # Create OpenAI client with explicit timeout
    try:
        client_kwargs = {
            "api_key": openai_config["api_key"],
            "timeout": 30,  # Prevent hanging on network issues
        }

        if openai_config["base_url"]:
            client_kwargs["base_url"] = openai_config["base_url"]
        if openai_config["organization"]:
            client_kwargs["organization"] = openai_config["organization"]

        # Create client directly; memori.enable() handles interception
        client = OpenAI(**client_kwargs)

        # Test connection first
        print("🔍 Testing OpenAI connection...")
        client.chat.completions.create(
            model=openai_config["model"],
            messages=[{"role": "user", "content": "Hello, this is a connection test."}],
            max_tokens=10,
        )
        print("✅ OpenAI connection successful\n")

    except Exception as e:
        print(f"❌ OpenAI connection failed: {e}")
        memory.disable()
        return False

    success_count = 0
    error_count = 0

    # Run test inputs
    for i, user_input in enumerate(test_inputs, 1):
        try:
            response = client.chat.completions.create(
                model=openai_config["model"],
                messages=[{"role": "user", "content": user_input}],
                max_tokens=500,
                temperature=0.7,
            )

            ai_response = response.choices[0].message.content
            print(f"[{i}/{len(test_inputs)}] User: {user_input}")
            print(f"[{i}/{len(test_inputs)}] AI: {ai_response[:100]}...")

            # Show token usage if available
            if hasattr(response, "usage") and response.usage:
                print(f"[{i}/{len(test_inputs)}] Tokens: {response.usage.total_tokens}")

            success_count += 1

            # Small delay between API calls to avoid rate limits
            time.sleep(0.2)

        except Exception as e:
            print(f"[{i}/{len(test_inputs)}] Error: {e}")
            error_count += 1

            if "rate_limit" in str(e).lower() or "429" in str(e):
                # Exponential backoff: 2, 4, 8, 16, 32, max 60 seconds
                wait = min(60, 2 ** min(i, 5))
                print(f"Rate limit hit, waiting {wait} seconds...")
                time.sleep(wait)
            elif "quota" in str(e).lower():
                print("Quota exceeded - stopping test")
                break
            elif "insufficient_quota" in str(e).lower():
                print("Insufficient quota - stopping test")
                break
            elif "invalid_api_key" in str(e).lower():
                print("Invalid API key - stopping test")
                break
            else:
                # Continue with other inputs for other types of errors
                time.sleep(5)

    # Get memory statistics
    try:
        stats = memory.get_memory_stats()
        print("\n📊 Memory Statistics:")
        print(f"   Successful API calls: {success_count}")
        print(f"   Failed API calls: {error_count}")
        print(f"   Long-term memories: {stats.get('long_term_count', 'N/A')}")
        print(f"   Chat history entries: {stats.get('chat_history_count', 'N/A')}")
    except Exception as e:
        print(f"   Could not retrieve memory stats: {e}")

    # Disable memory after test
    memory.disable()

    print(f"\n✓ OpenAI Test '{test_name}' completed.")
    print(f"  Database saved at: {db_path}")
    total = max(1, len(test_inputs))  # Prevent divide-by-zero
    print(
        f"  Success rate: {success_count}/{len(test_inputs)} ({100*success_count/total:.1f}%)\n"
    )

    return success_count > 0


def main():
    """
    Main OpenAI test runner.
    """
    # Validate OpenAI configuration
    is_valid, openai_config = validate_openai_config()

    if not is_valid:
        print("❌ OpenAI API key not found or invalid!")
        print("\nRequired environment variables:")
        print("- OPENAI_API_KEY (your OpenAI API key)")
        print("\nOptional environment variables:")
        print("- OPENAI_MODEL (default: gpt-4o)")
        print("- OPENAI_BASE_URL (for custom OpenAI-compatible endpoints)")
        print("- OPENAI_ORGANIZATION (if using organization-scoped API key)")
        print("\nExample:")
        print("export OPENAI_API_KEY='sk-your-actual-api-key-here'")
        print("export OPENAI_MODEL='gpt-4-turbo'")
        print("\nSkipping OpenAI tests...")
        return False

    # Load test inputs
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.dirname(script_dir)
    json_path = os.path.join(tests_dir, "test_inputs.json")
    test_inputs = load_inputs(json_path, limit=5)  # Using fewer inputs for testing

    # Define test scenarios - same as LiteLLM pattern
    test_scenarios = [
        {
            "name": "1_conscious_false_no_auto",
            "conscious_ingest": False,
            "auto_ingest": None,
            "description": "conscious_ingest=False (no auto_ingest specified)",
        },
        {
            "name": "2_conscious_true_no_auto",
            "conscious_ingest": True,
            "auto_ingest": None,
            "description": "conscious_ingest=True (no auto_ingest specified)",
        },
        {
            "name": "3_auto_true_only",
            "conscious_ingest": None,
            "auto_ingest": True,
            "description": "auto_ingest=True only",
        },
        {
            "name": "4_auto_false_only",
            "conscious_ingest": None,
            "auto_ingest": False,
            "description": "auto_ingest=False only",
        },
        {
            "name": "5_both_false",
            "conscious_ingest": False,
            "auto_ingest": False,
            "description": "Both conscious_ingest and auto_ingest = False",
        },
        {
            "name": "6_both_true",
            "conscious_ingest": True,
            "auto_ingest": True,
            "description": "Both conscious_ingest and auto_ingest = True",
        },
    ]

    # Clean up previous test databases
    if os.path.exists("test_databases_openai"):
        print("Cleaning up previous OpenAI test databases...")
        shutil.rmtree("test_databases_openai")

    print("🤖 Starting OpenAI Test Suite")
    print(
        f"Testing {len(test_scenarios)} configurations with {len(test_inputs)} inputs each"
    )
    print(f"Model: {openai_config['model']}")
    if openai_config["base_url"]:
        print(f"Base URL: {openai_config['base_url']}")
    if openai_config["organization"]:
        print(f"Organization: {openai_config['organization']}")
    print()

    successful_tests = 0

    # Run each test scenario
    for scenario in test_scenarios:
        # Handle None values by only passing specified parameters
        kwargs = {}
        if scenario["conscious_ingest"] is not None:
            kwargs["conscious_ingest"] = scenario["conscious_ingest"]
        if scenario["auto_ingest"] is not None:
            kwargs["auto_ingest"] = scenario["auto_ingest"]

        success = run_openai_test_scenario(
            test_name=scenario["name"],
            conscious_ingest=kwargs.get("conscious_ingest", False),
            auto_ingest=kwargs.get("auto_ingest", False),
            test_inputs=test_inputs,
            openai_config=openai_config,
        )

        if success:
            successful_tests += 1

        # Pause between tests
        print("Pausing for 3 seconds before next test...")
        time.sleep(3)

    print("\n" + "=" * 60)
    print(
        f"✅ OpenAI tests completed! ({successful_tests}/{len(test_scenarios)} successful)"
    )
    print("=" * 60)
    print("\nOpenAI test databases created in 'test_databases_openai/' directory:")
    for scenario in test_scenarios:
        db_path = f"test_databases_openai/{scenario['name']}/memory.db"
        if os.path.exists(db_path):
            size = os.path.getsize(db_path) / 1024  # Size in KB
            print(f"  - {scenario['name']}: {size:.2f} KB")

    return successful_tests > 0


def test_auto_ingest_intelligent_retrieval():
    """
    Test _get_auto_ingest_context() for intelligent context retrieval.

    This function is the actual implementation that handles:
    - Database search with user_input
    - Fallback to recent memories
    - Recursion guard protection
    - Search engine integration
    - Error handling
    """
    from unittest.mock import MagicMock, patch

    print("\n" + "=" * 60)
    print("Testing _get_auto_ingest_context() Intelligent Retrieval")
    print("=" * 60 + "\n")

    # Create temp database
    db_dir = "test_databases_openai/auto_ingest_test"
    os.makedirs(db_dir, exist_ok=True)
    db_path = f"{db_dir}/memory.db"

    # Initialize Memori with auto_ingest
    memori = Memori(
        database_connect=f"sqlite:///{db_path}",
        auto_ingest=True,
        namespace="test_namespace",
    )

    test_passed = 0
    test_total = 8

    # Test 1: Direct database search returns results
    print("\n[Test 1/8] Direct database search returns results...")
    mock_search_results = [
        {"searchable_content": "Result A", "category_primary": "fact"},
        {"searchable_content": "Result B", "category_primary": "preference"},
        {"searchable_content": "Result C", "category_primary": "skill"},
    ]

    with patch.object(
        memori.db_manager, "search_memories", return_value=mock_search_results
    ) as mock_search:
        result = memori._get_auto_ingest_context("What are my preferences?")

        # Verify results returned with metadata
        if (
            len(result) == 3
            and result[0].get("retrieval_method") == "direct_database_search"
        ):
            print("[OK] Test 1 passed: Direct search returns 3 results with metadata")
            test_passed += 1
        else:
            print(
                f"[FAIL] Test 1 failed: got {len(result)} results, metadata: {result[0].get('retrieval_method') if result else 'N/A'}"
            )

    # Test 2: Empty input returns empty list
    print("\n[Test 2/8] Empty input returns empty list...")
    result = memori._get_auto_ingest_context("")

    if result == []:
        print("[OK] Test 2 passed: Empty input returns []")
        test_passed += 1
    else:
        print(f"[FAIL] Test 2 failed: Expected [], got {result}")

    # Test 3: Fallback to recent memories when search returns empty
    print("\n[Test 3/8] Fallback to recent memories when search empty...")
    mock_fallback = [
        {"searchable_content": "Recent memory 1", "category_primary": "fact"},
        {"searchable_content": "Recent memory 2", "category_primary": "preference"},
    ]

    # First call returns empty, second call (fallback) returns results
    with patch.object(
        memori.db_manager, "search_memories", side_effect=[[], mock_fallback]
    ) as mock_search:
        result = memori._get_auto_ingest_context("query with no results")

        # Check fallback was used and metadata added
        if (
            len(result) == 2
            and result[0].get("retrieval_method") == "recent_memories_fallback"
        ):
            print("[OK] Test 3 passed: Fallback to recent memories works")
            test_passed += 1
        else:
            print(
                f"[FAIL] Test 3 failed: got {len(result)} results, metadata: {result[0].get('retrieval_method') if result else 'N/A'}"
            )

    # Test 4: Recursion guard prevents infinite loops
    print("\n[Test 4/8] Recursion guard prevents infinite loops...")
    memori._in_context_retrieval = True

    mock_results = [{"searchable_content": "Safe result", "category_primary": "fact"}]
    with patch.object(
        memori.db_manager, "search_memories", return_value=mock_results
    ) as mock_search:
        result = memori._get_auto_ingest_context("test recursion")

        # Should use direct search and return results
        if result == mock_results:
            print("[OK] Test 4 passed: Recursion guard triggers direct search")
            test_passed += 1
        else:
            print("[FAIL] Test 4 failed: Expected direct search results")

    # Reset recursion guard
    memori._in_context_retrieval = False

    # Test 5: Search engine fallback when direct search fails
    print("\n[Test 5/8] Search engine fallback when direct search empty...")
    mock_search_engine = MagicMock()
    mock_engine_results = [
        {"searchable_content": "Engine result", "category_primary": "fact"}
    ]
    mock_search_engine.execute_search.return_value = mock_engine_results
    memori.search_engine = mock_search_engine

    with patch.object(
        memori.db_manager,
        "search_memories",
        side_effect=[[], []],  # Both direct and fallback empty
    ):
        result = memori._get_auto_ingest_context("advanced query")

        # Check search engine was used
        if len(result) == 1 and result[0].get("retrieval_method") == "search_engine":
            print("[OK] Test 5 passed: Search engine fallback works")
            test_passed += 1
        else:
            print(
                f"[FAIL] Test 5 failed: got {len(result)} results, metadata: {result[0].get('retrieval_method') if result else 'N/A'}"
            )

    # Reset search engine
    memori.search_engine = None

    # Test 6: Error handling - graceful degradation
    print("\n[Test 6/8] Error handling with graceful degradation...")

    # First call fails, fallback succeeds
    mock_fallback = [{"searchable_content": "Fallback", "category_primary": "fact"}]
    with patch.object(
        memori.db_manager,
        "search_memories",
        side_effect=[Exception("DB error"), mock_fallback],
    ):
        result = memori._get_auto_ingest_context("test error handling")

        # Should fallback to recent memories
        if (
            len(result) == 1
            and result[0].get("retrieval_method") == "recent_memories_fallback"
        ):
            print("[OK] Test 6 passed: Error handled, fallback used")
            test_passed += 1
        else:
            print(f"[FAIL] Test 6 failed: got {len(result)} results")

    # Test 7: Verify search called with correct parameters
    print("\n[Test 7/8] Verify search called with correct parameters...")
    with patch.object(
        memori.db_manager,
        "search_memories",
        return_value=[{"searchable_content": "Test", "category_primary": "fact"}],
    ) as mock_search:
        user_query = "find my API keys"
        result = memori._get_auto_ingest_context(user_query)

        # Check search was called with correct params
        if mock_search.called:
            call = mock_search.call_args
            called_query = call.kwargs.get("query") if call.kwargs else call.args[0]
            called_namespace = call.kwargs.get("namespace") if call.kwargs else None
            called_limit = call.kwargs.get("limit") if call.kwargs else None

            query_match = called_query == user_query
            namespace_match = called_namespace == "test_namespace"
            limit_match = called_limit == 5

            if query_match and namespace_match and limit_match:
                print("[OK] Test 7 passed: search_memories called with correct params")
                test_passed += 1
            else:
                print(
                    f"[FAIL] Test 7 failed: query={query_match}, ns={namespace_match}, limit={limit_match}"
                )
        else:
            print("[FAIL] Test 7 failed: search_memories not called")

    # Test 8: Retrieval metadata is added to results
    print("\n[Test 8/8] Retrieval metadata added to all results...")
    mock_results = [
        {"searchable_content": "Item 1", "category_primary": "fact"},
        {"searchable_content": "Item 2", "category_primary": "preference"},
    ]

    with patch.object(memori.db_manager, "search_memories", return_value=mock_results):
        result = memori._get_auto_ingest_context("metadata test")

        # Check all results have metadata
        all_have_metadata = all(
            r.get("retrieval_method") and r.get("retrieval_query") for r in result
        )

        if all_have_metadata and result[0]["retrieval_query"] == "metadata test":
            print("[OK] Test 8 passed: All results have retrieval metadata")
            test_passed += 1
        else:
            print("[FAIL] Test 8 failed: metadata missing or incorrect")

    # Summary
    print("\n" + "=" * 60)
    print(f"_get_auto_ingest_context() Tests: {test_passed}/{test_total} passed")
    print("=" * 60 + "\n")

    return test_passed == test_total


if __name__ == "__main__":
    main()
