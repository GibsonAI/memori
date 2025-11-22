import os
import shutil
import sys
import time

# Fix imports to work from any directory
if __name__ == "__main__":
    # When running as script, ensure we can import from tests directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.dirname(script_dir)
    project_root = os.path.dirname(tests_dir)

    # Add both project root and tests directory to path
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    if tests_dir not in sys.path:
        sys.path.insert(0, tests_dir)

# Import individual test modules
from tests.openai_support import openai_test

from . import azure_openai_test, ollama_test


class OpenAITestSuite:
    """
    Comprehensive OpenAI Provider Test Suite.

    Tests multiple OpenAI-compatible providers with all combinations of
    conscious_ingest and auto_ingest parameters, following the same
    testing patterns as LiteLLM tests.
    """

    def __init__(self):
        self.results = {}
        self.start_time = None
        self.end_time = None

    def run_provider_tests(self, provider_name: str, test_module) -> tuple[bool, str]:
        """
        Run tests for a specific provider.

        Args:
            provider_name: Name of the provider (e.g., 'OpenAI', 'Azure OpenAI', 'Ollama')
            test_module: The test module to run

        Returns:
            Tuple of (success, error_message)
        """
        print(f"\n🔄 Starting {provider_name} tests...")

        try:
            success = test_module.main()
            if success:
                print(f"✅ {provider_name} tests completed successfully")
                return True, ""
            else:
                print(f"⚠️ {provider_name} tests completed with issues")
                return False, "Tests completed but some scenarios failed"

        except Exception as e:
            error_msg = f"Failed to run {provider_name} tests: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def cleanup_old_databases(self):
        """Clean up old test databases from all providers."""
        db_dirs = [
            "test_databases_openai",
            "test_databases_azure_openai",
            "test_databases_ollama",
        ]

        print("🧹 Cleaning up old test databases...")
        for db_dir in db_dirs:
            if os.path.exists(db_dir):
                try:
                    shutil.rmtree(db_dir)
                    print(f"   Removed {db_dir}")
                except Exception as e:
                    print(f"   Warning: Could not remove {db_dir}: {e}")

    def collect_database_stats(self) -> dict[str, list[dict]]:
        """Collect statistics from all created test databases."""
        stats = {}

        db_dirs = {
            "OpenAI": "test_databases_openai",
            "Azure OpenAI": "test_databases_azure_openai",
            "Ollama": "test_databases_ollama",
        }

        for provider, db_dir in db_dirs.items():
            if os.path.exists(db_dir):
                provider_stats = []
                for scenario_dir in os.listdir(db_dir):
                    scenario_path = os.path.join(db_dir, scenario_dir)
                    if os.path.isdir(scenario_path):
                        db_file = os.path.join(scenario_path, "memory.db")
                        if os.path.exists(db_file):
                            size_kb = os.path.getsize(db_file) / 1024
                            provider_stats.append(
                                {
                                    "scenario": scenario_dir,
                                    "size_kb": size_kb,
                                    "path": db_file,
                                }
                            )

                if provider_stats:
                    stats[provider] = sorted(
                        provider_stats, key=lambda x: x["scenario"]
                    )

        return stats

    def display_summary(
        self, results: dict[str, tuple[bool, str]], db_stats: dict[str, list[dict]]
    ):
        """Display comprehensive test summary with detailed validation results."""

        duration = (
            self.end_time - self.start_time if self.end_time and self.start_time else 0
        )

        print("\n" + "=" * 80)
        print("🎯 OPENAI PROVIDER TEST SUITE - COMPREHENSIVE RESULTS")
        print("=" * 80)

        print(f"⏱️  Total Duration: {duration:.1f} seconds")
        print(f"📅 Test Completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Provider Results Summary
        print("\n📊 PROVIDER TEST RESULTS:")
        successful_providers = 0
        total_providers = len(results)

        for provider, (success, error_msg) in results.items():
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"   {provider:15} {status}")
            if not success and error_msg:
                print(f"   {'':<15} └─ {error_msg}")
            if success:
                successful_providers += 1

        print(
            f"\n🏆 Success Rate: {successful_providers}/{total_providers} providers ({100 * successful_providers / total_providers:.1f}%)"
        )

        # Database Statistics
        if db_stats:
            print("\n💾 DATABASE STATISTICS:")
            total_databases = 0
            total_size_kb = 0

            for provider, scenarios in db_stats.items():
                if scenarios:
                    print(f"\n   {provider}:")
                    for scenario in scenarios:
                        print(
                            f"     {scenario['scenario']:25} {scenario['size_kb']:6.2f} KB"
                        )
                        total_databases += 1
                        total_size_kb += scenario["size_kb"]

            print(
                f"\n   📈 Summary: {total_databases} databases created, {total_size_kb:.2f} KB total"
            )

        # Test Configuration Details
        print("\n⚙️  TEST CONFIGURATION:")
        print("   • Each provider tested with 6 scenarios")
        print("   • Scenarios test all combinations of conscious_ingest/auto_ingest")
        print("   • 5 test inputs per scenario (total: 30 API calls per provider)")
        print("   • Memory behavior validated for each configuration")
        print("   • Provider connection and authentication validated")
        print("   • Error handling and edge cases tested")
        print("   • Conversation storage and retrieval verified")

        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if successful_providers == total_providers:
            print(
                "   ✨ All providers working perfectly! Your OpenAI integrations are solid."
            )
        else:
            failed_providers = [p for p, (s, _) in results.items() if not s]
            print(f"   🔧 Check configuration for: {', '.join(failed_providers)}")
            print(
                "   📖 Review provider-specific setup instructions in test output above"
            )

        print("\n" + "=" * 80)

    def run_all_tests(self):
        """Run the complete OpenAI provider test suite."""
        print("🚀 MEMORI OPENAI PROVIDER TEST SUITE")
        print("=" * 60)
        print("Testing comprehensive OpenAI provider compatibility")
        print("with memory ingestion behavior validation")
        print("=" * 60)

        self.start_time = time.time()

        # Clean up old databases
        self.cleanup_old_databases()

        # Define providers to test
        providers = [
            ("OpenAI", openai_test),
            ("Azure OpenAI", azure_openai_test),
            ("Ollama", ollama_test),
        ]

        # Run tests for each provider
        results = {}
        for provider_name, test_module in providers:
            success, error_msg = self.run_provider_tests(provider_name, test_module)
            results[provider_name] = (success, error_msg)

            # Pause between provider tests
            if provider_name != providers[-1][0]:  # Not the last provider
                print("\n⏸️  Pausing 5 seconds before next provider...")
                time.sleep(5)

        self.end_time = time.time()

        # Collect database statistics
        db_stats = self.collect_database_stats()

        # Display comprehensive summary
        self.display_summary(results, db_stats)

        # Return overall success
        return all(success for success, _ in results.values())


def main():
    """
    Main test suite entry point.
    """
    suite = OpenAITestSuite()
    overall_success = suite.run_all_tests()

    if overall_success:
        print("\n🎉 All OpenAI provider tests completed successfully!")
        return 0
    else:
        print("\n⚠️  Some OpenAI provider tests had issues. Check the summary above.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
