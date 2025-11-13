"""
Memori CLI - Command-line interface for memori package

Provides commands for initialization, version checking, and health validation.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def get_version() -> str:
    """Get the memori package version."""
    try:
        from importlib.metadata import version
        return version("memorisdk")
    except Exception:
        # Fallback to __init__.py version if metadata not available
        try:
            from memori import __version__
            return __version__
        except ImportError:
            return "unknown"


def cmd_version(args: argparse.Namespace) -> int:
    """Handle --version command."""
    version = get_version()
    print(f"memori version {version}")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """
    Handle init command - creates a starter memori.json config.
    
    Returns:
        0 on success, 1 on failure
    """
    config_path = Path("memori.json")
    
    # Check if file exists and --force not used
    if config_path.exists() and not args.force:
        print(f"Error: {config_path} already exists. Use --force to overwrite.")
        return 1
    
    # Default configuration template
    default_config = {
        "database": {
            "connection_string": "sqlite:///memori.db",
            "pool_size": 5,
            "echo_sql": False
        },
        "agents": {
            "openai_api_key": "sk-your-openai-key-here",
            "default_model": "gpt-4o-mini",
            "conscious_ingest": True,
            "max_tokens": 2000,
            "temperature": 0.1
        },
        "memory": {
            "namespace": "default",
            "retention_policy": "30_days",
            "importance_threshold": 0.3,
            "context_limit": 3,
            "auto_cleanup": True
        },
        "logging": {
            "level": "INFO",
            "log_to_file": False,
            "structured_logging": False
        }
    }
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)
        
        action = "Overwritten" if config_path.exists() and args.force else "Created"
        print(f"✓ {action} {config_path}")
        print("\nNext steps:")
        print("  1. Edit memori.json with your configuration")
        print("  2. Set your OpenAI API key (or use environment variable OPENAI_API_KEY)")
        print("  3. Import and use memori in your Python code:")
        print("\n     from memori import Memori")
        print("     memory = Memori(config_path='memori.json')")
        return 0
    except Exception as e:
        print(f"Error: Failed to create {config_path}: {e}")
        return 1


def cmd_health(args: argparse.Namespace) -> int:
    """
    Handle health command - validates environment and configuration.
    
    Returns:
        0 if all checks pass, non-zero otherwise
    """
    print("Memori Health Check")
    print("=" * 50)
    
    exit_code = 0
    
    # Check 1: Package import
    print("\n1. Package Import Check...")
    try:
        import memori
        version = get_version()
        print(f"   ✓ memori {version} imported successfully")
    except ImportError as e:
        print(f"   ✗ Failed to import memori: {e}")
        exit_code = 1
    
    # Check 2: Core dependencies
    print("\n2. Core Dependencies Check...")
    required_deps = [
        ("pydantic", "Pydantic"),
        ("sqlalchemy", "SQLAlchemy"),
        ("openai", "OpenAI"),
        ("litellm", "LiteLLM"),
        ("loguru", "Loguru"),
        ("dotenv", "python-dotenv")
    ]
    
    for module_name, display_name in required_deps:
        try:
            __import__(module_name)
            print(f"   ✓ {display_name} available")
        except ImportError:
            print(f"   ✗ {display_name} not installed")
            exit_code = 1
    
    # Check 3: Configuration file validation
    print("\n3. Configuration File Check...")
    config_path = Path(args.config if args.config else "memori.json")
    
    if not config_path.exists():
        print(f"   ⚠ Config file not found: {config_path}")
        print(f"     Run 'memori init' to create a starter configuration")
    else:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Validate required sections
            required_sections = ["database", "agents", "memory", "logging"]
            missing_sections = [s for s in required_sections if s not in config]
            
            if missing_sections:
                print(f"   ✗ Missing required sections: {', '.join(missing_sections)}")
                exit_code = 1
            else:
                print(f"   ✓ Config file valid: {config_path}")
                
                # Check database connection string
                if "database" in config and "connection_string" in config["database"]:
                    conn_str = config["database"]["connection_string"]
                    print(f"   ✓ Database: {conn_str.split(':')[0]}")
                
                # Check namespace
                if "memory" in config and "namespace" in config["memory"]:
                    namespace = config["memory"]["namespace"]
                    print(f"   ✓ Namespace: {namespace}")
        
        except json.JSONDecodeError as e:
            print(f"   ✗ Invalid JSON in config file: {e}")
            exit_code = 1
        except Exception as e:
            print(f"   ✗ Error reading config: {e}")
            exit_code = 1
    
    # Check 4: Database connectivity (optional, only if config exists)
    if args.check_db and config_path.exists():
        print("\n4. Database Connectivity Check...")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            conn_str = config.get("database", {}).get("connection_string")
            if conn_str:
                from memori.core.database import DatabaseManager
                
                try:
                    db = DatabaseManager(connection_string=conn_str)
                    print(f"   ✓ Database connection successful")
                except Exception as e:
                    print(f"   ✗ Database connection failed: {e}")
                    exit_code = 1
            else:
                print(f"   ⚠ No connection string in config")
        except Exception as e:
            print(f"   ✗ Database check failed: {e}")
            exit_code = 1
    
    # Summary
    print("\n" + "=" * 50)
    if exit_code == 0:
        print("✓ All health checks passed!")
    else:
        print("✗ Some health checks failed. Please review the output above.")
    
    return exit_code


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="memori",
        description="Memori - The Open-Source Memory Layer for AI Agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  memori --version              Show version information
  memori init                   Create a starter memori.json config
  memori init --force           Overwrite existing memori.json
  memori health                 Check environment and configuration
  memori health --check-db      Include database connectivity check
  memori health --config path/to/config.json
        """
    )
    
    # Version flag (can be used standalone)
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # init command
    init_parser = subparsers.add_parser(
        "init",
        help="Create a starter memori.json configuration file"
    )
    init_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing configuration file"
    )
    
    # health command
    health_parser = subparsers.add_parser(
        "health",
        help="Check environment, dependencies, and configuration"
    )
    health_parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to configuration file (default: memori.json)"
    )
    health_parser.add_argument(
        "--check-db",
        action="store_true",
        help="Include database connectivity check"
    )
    
    args = parser.parse_args()
    
    # Handle --version flag
    if args.version:
        return cmd_version(args)
    
    # Handle subcommands
    if args.command == "init":
        return cmd_init(args)
    elif args.command == "health":
        return cmd_health(args)
    else:
        # No command provided, show help
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
