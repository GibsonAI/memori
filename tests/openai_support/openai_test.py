import os
import shutil
import sys
import time

from memori import Memori
from openai import OpenAI

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

    is_valid = config["api_key"] and not config["api_key"].startswith("sk-your-")

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
    print(f"\n{'=' * 60}")
    print(f"Running OpenAI Test: {test_name}")
    print(
        f"Configuration: conscious_ingest={conscious_ingest}, auto_ingest={auto_ingest}"
    )
    print(f"Model: {openai_config['model']}")
    if openai_config["base_url"]:
        print(f"Base URL: {openai_config['base_url']}")
    if openai_config["organization"]:
        print(f"Organization: {openai_config['organization']}")
    print(f"{'=' * 60}\n")

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

    # Create OpenAI client
    try:
        client_kwargs = {"api_key": openai_config["api_key"]}

        if openai_config["base_url"]:
            client_kwargs["base_url"] = openai_config["base_url"]
        if openai_config["organization"]:
            client_kwargs["organization"] = openai_config["organization"]

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

            # Small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"[{i}/{len(test_inputs)}] Error: {e}")
            error_count += 1

            if "rate_limit" in str(e).lower() or "429" in str(e):
                print("Rate limit hit, waiting 60 seconds...")
                time.sleep(60)
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
    print(
        f"  Success rate: {success_count}/{len(test_inputs)} ({100 * success_count / len(test_inputs):.1f}%)\n"
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


if __name__ == "__main__":
    main()
