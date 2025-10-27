import os
import shutil
import sys
import time

from litellm import completion

from memori import Memori

# Fix imports to work from any directory
if __name__ == "__main__":
    # When running as script, ensure we can import from tests directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.dirname(script_dir)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)

from tests.utils.test_utils import load_inputs


def run_test_scenario(test_name, conscious_ingest, auto_ingest, test_inputs):
    """
    Run a test scenario with specific configuration.

    Args:
        test_name: Name of the test scenario
        conscious_ingest: Boolean for conscious_ingest parameter
        auto_ingest: Boolean for auto_ingest parameter
        test_inputs: List of test inputs to process
    """
    print(f"\n{'=' * 60}")
    print(f"Running Test: {test_name}")
    print(
        f"Configuration: conscious_ingest={conscious_ingest}, auto_ingest={auto_ingest}"
    )
    print(f"{'=' * 60}\n")

    # Create database directory for this test
    db_dir = f"test_databases/{test_name}"
    os.makedirs(db_dir, exist_ok=True)
    db_path = f"{db_dir}/memory.db"

    # Initialize Memori with specific configuration
    memory = Memori(
        database_connect=f"sqlite:///{db_path}",
        conscious_ingest=conscious_ingest,
        auto_ingest=auto_ingest,
        verbose=True,  # Set to True if you want detailed logs
    )

    memory.enable()

    # Run test inputs
    for i, user_input in enumerate(test_inputs, 1):
        try:
            response = completion(
                model="gpt-4o", messages=[{"role": "user", "content": user_input}]
            )

            print(f"[{i}/{len(test_inputs)}] User: {user_input}")
            print(
                f"[{i}/{len(test_inputs)}] AI: {response.choices[0].message['content'][:100]}..."
            )  # Truncate for readability

            # Small delay to avoid rate limiting
            time.sleep(0.5)

        except Exception as e:
            print(f"[{i}/{len(test_inputs)}] Error: {e}")
            if "rate_limit" in str(e).lower():
                print("Rate limit hit, waiting 60 seconds...")
                time.sleep(60)

    # Disable memory after test
    memory.disable()

    print(f"\n✓ Test '{test_name}' completed. Database saved at: {db_path}\n")


def main():
    """
    Main test suite runner.
    """
    # Load test inputs - use absolute path based on script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.dirname(script_dir)
    json_path = os.path.join(tests_dir, "test_inputs.json")
    test_inputs = load_inputs(json_path, limit=5)  # Using fewer inputs for testing

    # Define test scenarios
    test_scenarios = [
        {
            "name": "1_conscious_false_no_auto",
            "conscious_ingest": False,
            "auto_ingest": None,  # Not specifying auto_ingest
            "description": "conscious_ingest=False (no auto_ingest specified)",
        },
        {
            "name": "2_conscious_true_no_auto",
            "conscious_ingest": True,
            "auto_ingest": None,  # Not specifying auto_ingest
            "description": "conscious_ingest=True (no auto_ingest specified)",
        },
        {
            "name": "3_auto_true_only",
            "conscious_ingest": None,  # Not specifying conscious_ingest
            "auto_ingest": True,
            "description": "auto_ingest=True only",
        },
        {
            "name": "4_auto_false_only",
            "conscious_ingest": None,  # Not specifying conscious_ingest
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
    if os.path.exists("test_databases"):
        print("Cleaning up previous test databases...")
        shutil.rmtree("test_databases")

    print("Starting Memori Test Suite")
    print(
        f"Testing {len(test_scenarios)} configurations with {len(test_inputs)} inputs each\n"
    )

    # Run each test scenario
    for scenario in test_scenarios:
        # Handle None values by only passing specified parameters
        kwargs = {}
        if scenario["conscious_ingest"] is not None:
            kwargs["conscious_ingest"] = scenario["conscious_ingest"]
        if scenario["auto_ingest"] is not None:
            kwargs["auto_ingest"] = scenario["auto_ingest"]

        run_test_scenario(
            test_name=scenario["name"],
            conscious_ingest=kwargs.get("conscious_ingest", False),
            auto_ingest=kwargs.get("auto_ingest", False),
            test_inputs=test_inputs,
        )

        # Pause between tests
        print("Pausing for 2 seconds before next test...")
        time.sleep(2)

    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    print("\nTest databases created in 'test_databases/' directory:")
    for scenario in test_scenarios:
        db_path = f"test_databases/{scenario['name']}/memory.db"
        if os.path.exists(db_path):
            size = os.path.getsize(db_path) / 1024  # Size in KB
            print(f"  - {scenario['name']}: {size:.2f} KB")


if __name__ == "__main__":
    main()
