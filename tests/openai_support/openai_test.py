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
    Test that auto-ingest mode uses user_input for intelligent context retrieval.
    This tests the fix for the TODO at line 2641 in memori/core/memory.py
    """
    from unittest.mock import MagicMock, patch
    
    print("\n" + "=" * 60)
    print("Testing Auto-Ingest Intelligent Retrieval")
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
    test_total = 7
    
    # Test 1: Happy path - search returns 3 items, verify they appear (not fallback)
    print("\n[Test 1/7] Happy path: 3 search results appear, no fallback...")
    mock_search_results = [
        {"searchable_content": "Result A from search", "category_primary": "fact"},
        {"searchable_content": "Result B from search", "category_primary": "preference"},
        {"searchable_content": "Result C from search", "category_primary": "skill"},
    ]
    mock_conscious_fallback = [
        {"searchable_content": "Conscious fallback item", "category_primary": "context"},
    ]
    
    with patch.object(
        memori.db_manager, "search_memories", return_value=mock_search_results
    ) as mock_search:
        with patch.object(
            memori, "_get_conscious_context", return_value=mock_conscious_fallback
        ):
            result = memori.get_auto_ingest_system_prompt("What do I know?")
            
            # Assert all 3 search results are present
            has_all_search = all(item["searchable_content"] in result for item in mock_search_results)
            # Assert fallback is NOT present
            has_no_fallback = "Conscious fallback item" not in result
            
            if has_all_search and has_no_fallback:
                print("[OK] Test 1 passed: 3 search results present, no fallback")
                test_passed += 1
            else:
                print(f"[FAIL] Test 1 failed: has_all_search={has_all_search}, has_no_fallback={has_no_fallback}")
    
    # Test 2: No hits → fallback test
    print("\n[Test 2/7] No hits: empty search triggers fallback...")
    mock_fallback_items = [
        {"searchable_content": "Fallback item 1", "category_primary": "fact"},
        {"searchable_content": "Fallback item 2", "category_primary": "preference"},
    ]
    
    with patch.object(
        memori.db_manager, "search_memories", return_value=[]
    ) as mock_search:
        with patch.object(
            memori, "_get_conscious_context", return_value=mock_fallback_items
        ):
            result = memori.get_auto_ingest_system_prompt("query with no results")
            
            # Assert both fallback items are present
            has_fallback_1 = "Fallback item 1" in result
            has_fallback_2 = "Fallback item 2" in result
            
            if has_fallback_1 and has_fallback_2:
                print("[OK] Test 2 passed: Both fallback items appear when search empty")
                test_passed += 1
            else:
                print(f"[FAIL] Test 2 failed: fallback_1={has_fallback_1}, fallback_2={has_fallback_2}")
    
    # Test 3: Deduplication - duplicate searchable_content should appear only once
    print("\n[Test 3/7] Deduplication: duplicate content appears once...")
    duplicates = [
        {"searchable_content": "Unique content here", "category_primary": "fact"},
        {"searchable_content": "Unique content here", "category_primary": "fact"},  # Exact duplicate
        {"searchable_content": "Another unique item", "category_primary": "skill"},
        {"searchable_content": "UNIQUE CONTENT HERE", "category_primary": "preference"},  # Case variation
    ]
    
    with patch.object(
        memori.db_manager, "search_memories", return_value=duplicates
    ):
        result = memori.get_auto_ingest_system_prompt("test dedup")
        
        # Count occurrences (case-insensitive dedup in implementation)
        unique_count = result.count("Unique content here")
        another_count = result.count("Another unique item")
        
        # Should have exactly 1 occurrence after dedup (case-insensitive)
        if unique_count == 1 and another_count == 1:
            print("[OK] Test 3 passed: Duplicates properly deduplicated")
            test_passed += 1
        else:
            print(f"[FAIL] Test 3 failed: unique_count={unique_count}, another_count={another_count}")
    
    # Test 4: Exception handling
    print("\n[Test 4/7] Exception handling: graceful fallback on error...")
    with patch.object(
        memori.db_manager, "search_memories",
        side_effect=Exception("Database connection error")
    ):
        with patch.object(
            memori, "_get_conscious_context",
            return_value=[{"searchable_content": "Safe fallback", "category_primary": "fact"}]
        ):
            try:
                result = memori.get_auto_ingest_system_prompt("test exception")
                if "Safe fallback" in result:
                    print("[OK] Test 4 passed: Exception handled, fallback used")
                    test_passed += 1
                else:
                    print("[FAIL] Test 4 failed: Fallback not used after exception")
            except Exception as e:
                print(f"[FAIL] Test 4 failed: Exception not handled: {e}")
    
    # Test 5: Empty user_input
    print("\n[Test 5/7] Empty input: skips search, uses conscious context...")
    with patch.object(memori.db_manager, "search_memories") as mock_search:
        with patch.object(
            memori, "_get_conscious_context",
            return_value=[{"searchable_content": "Default conscious", "category_primary": "fact"}]
        ):
            result = memori.get_auto_ingest_system_prompt("")
            
            if not mock_search.called and "Default conscious" in result:
                print("[OK] Test 5 passed: Empty input skips search, uses conscious")
                test_passed += 1
            else:
                print(f"[FAIL] Test 5 failed: search_called={mock_search.called}")
    
    # Test 6: 5-item limit
    print("\n[Test 6/7] 5-item limit: only first 5 items included...")
    many_items = [
        {"searchable_content": f"Memory item number {i}", "category_primary": "fact"}
        for i in range(10)
    ]
    
    with patch.object(
        memori.db_manager, "search_memories", return_value=many_items
    ):
        result = memori.get_auto_ingest_system_prompt("show me everything")
        
        # Count how many items appear (should be max 5)
        item_count = sum(1 for i in range(10) if f"Memory item number {i}" in result)
        
        if item_count <= 5:
            print(f"[OK] Test 6 passed: {item_count} items (<=5 limit enforced)")
            test_passed += 1
        else:
            print(f"[FAIL] Test 6 failed: {item_count} items exceed 5-item limit")
    
    # Test 7: Verify search is called with correct parameters
    print("\n[Test 7/7] Verify search called with correct query parameters...")
    with patch.object(
        memori.db_manager, "search_memories", return_value=[
            {"searchable_content": "Test result", "category_primary": "fact"}
        ]
    ) as mock_search:
        user_query = "merge last 3 commits"
        result = memori.get_auto_ingest_system_prompt(user_query)
        
        # Verify search_memories was called with correct parameters
        if mock_search.called:
            call = mock_search.call_args
            # Supports both args and kwargs usage across mock versions
            called_query = (call.kwargs.get("query") 
                           if call.kwargs else call.args[0])
            called_namespace = (call.kwargs.get("namespace") 
                               if call.kwargs else None)
            called_limit = (call.kwargs.get("limit") 
                           if call.kwargs else None)
            
            query_match = called_query == user_query
            namespace_match = called_namespace == "test_namespace"
            limit_match = called_limit == 10
            
            if query_match and namespace_match and limit_match:
                print("[OK] Test 7 passed: search_memories called with correct params")
                test_passed += 1
            else:
                print(f"[FAIL] Test 7 failed: query={query_match}, ns={namespace_match}, limit={limit_match}")
        else:
            print("[FAIL] Test 7 failed: search_memories not called")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Auto-Ingest Tests: {test_passed}/{test_total} passed")
    print("=" * 60 + "\n")
    
    return test_passed == test_total


if __name__ == "__main__":
    main()
