#!/usr/bin/env python3
"""
Memori v1.x to v2.0 Migration Helper Script

This script automates the migration from namespace-based isolation to
multi-tenant architecture (user_id/assistant_id/session_id).

Usage:
    python migrate_v1_to_v2.py --database "postgresql://user:pass@localhost/memori_db"
    python migrate_v1_to_v2.py --database "mysql://user:pass@localhost/memori_db"
    python migrate_v1_to_v2.py --database "sqlite:///path/to/memori.db"

Options:
    --database     Database connection string (required)
    --dry-run      Show what would be migrated without executing
    --backup       Create backup before migration (recommended)
    --skip-backup  Skip backup creation (not recommended)
    --force        Force migration even if validation fails
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

try:
    from sqlalchemy import create_engine, inspect, text
except ImportError:
    print("ERROR: SQLAlchemy is required. Install with: pip install sqlalchemy")
    sys.exit(1)


class MigrationHelper:
    """Helper class for managing Memori v1.x to v2.0 migration"""

    def __init__(self, database_url: str, dry_run: bool = False, force: bool = False):
        self.database_url = database_url
        self.dry_run = dry_run
        self.force = force
        self.db_type = self._detect_db_type(database_url)
        self.engine = None
        self.migration_dir = Path(__file__).parent

    def _detect_db_type(self, url: str) -> str:
        """Detect database type from connection string"""
        if url.startswith("postgresql"):
            return "postgresql"
        elif url.startswith("mysql"):
            return "mysql"
        elif url.startswith("sqlite"):
            return "sqlite"
        else:
            raise ValueError(f"Unsupported database type in URL: {url}")

    def _get_migration_script_path(self) -> Path:
        """Get the appropriate migration script path for database type"""
        script_name = f"migrate_v1_to_v2_{self.db_type}.sql"
        return self.migration_dir / script_name

    def _create_backup(self):
        """Create database backup before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if self.db_type == "sqlite":
            # For SQLite, copy the file
            db_path = self.database_url.replace("sqlite:///", "")
            backup_path = f"{db_path}.backup_{timestamp}"

            if self.dry_run:
                print(f"[DRY RUN] Would create backup: {backup_path}")
                return

            try:
                import shutil

                shutil.copy2(db_path, backup_path)
                print(f"✓ Created SQLite backup: {backup_path}")
            except Exception as e:
                print(f"✗ Failed to create backup: {e}")
                if not self.force:
                    sys.exit(1)

        elif self.db_type == "postgresql":
            print("\nWARNING: IMPORTANT: Create PostgreSQL backup manually:")
            print(f"   pg_dump {self._get_db_name()} > backup_{timestamp}.sql")

            if not self.force:
                response = input("\nHave you created a backup? (yes/no): ")
                if response.lower() != "yes":
                    print("Migration cancelled. Please create a backup first.")
                    sys.exit(1)

        elif self.db_type == "mysql":
            print("\nWARNING: IMPORTANT: Create MySQL backup manually:")
            print(f"   mysqldump {self._get_db_name()} > backup_{timestamp}.sql")

            if not self.force:
                response = input("\nHave you created a backup? (yes/no): ")
                if response.lower() != "yes":
                    print("Migration cancelled. Please create a backup first.")
                    sys.exit(1)

    def _get_db_name(self) -> str:
        """Extract database name from connection string"""
        parsed = urlparse(self.database_url)
        return parsed.path.lstrip("/")

    def validate_schema(self):
        """Validate that the database has the expected v1.x schema"""
        print("\n📋 Validating current schema...")

        try:
            self.engine = create_engine(self.database_url)
            inspector = inspect(self.engine)

            # Check required tables exist
            required_tables = ["chat_history", "short_term_memory", "long_term_memory"]
            existing_tables = inspector.get_table_names()

            missing_tables = [t for t in required_tables if t not in existing_tables]
            if missing_tables:
                print(f"✗ Missing required tables: {missing_tables}")
                return False

            print(f"✓ Found all required tables: {required_tables}")

            # Check if namespace column exists (v1.x schema)
            chat_columns = [c["name"] for c in inspector.get_columns("chat_history")]
            if "namespace" not in chat_columns:
                if "user_id" in chat_columns:
                    print(
                        "WARNING: WARNING: Database appears to already be migrated (has user_id column)"
                    )
                    if not self.force:
                        print("Use --force to run migration anyway")
                        return False
                else:
                    print("✗ Unexpected schema: no namespace or user_id column found")
                    return False

            print("✓ Schema validation passed")
            return True

        except Exception as e:
            print(f"✗ Schema validation failed: {e}")
            return False

    def show_statistics(self):
        """Show current database statistics"""
        print("\nSTATS: Current database statistics:")

        try:
            with self.engine.connect() as conn:
                # Get record counts by namespace
                tables = ["chat_history", "short_term_memory", "long_term_memory"]

                for table in tables:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) as count FROM {table}")
                    )
                    count = result.scalar()
                    print(f"  {table}: {count} records")

                    # Show namespace distribution if column exists
                    try:
                        result = conn.execute(
                            text(
                                f"SELECT namespace, COUNT(*) as count FROM {table} "
                                f"GROUP BY namespace"
                            )
                        )
                        for row in result:
                            print(f"    - namespace '{row[0]}': {row[1]} records")
                    except Exception:
                        pass  # Namespace column doesn't exist or query failed

        except Exception as e:
            print(f"✗ Failed to get statistics: {e}")

    def run_migration(self):
        """Execute the migration script"""
        script_path = self._get_migration_script_path()

        if not script_path.exists():
            print(f"✗ Migration script not found: {script_path}")
            return False

        print(f"\nRUNNING: Running migration script: {script_path.name}")

        if self.dry_run:
            print("[DRY RUN] Would execute migration script")
            print("\nMigration script content preview:")
            with open(script_path) as f:
                lines = f.readlines()[:50]  # Show first 50 lines
                print("".join(lines))
            return True

        try:
            # Read migration script
            with open(script_path) as f:
                migration_sql = f.read()

            # Execute migration
            with self.engine.connect() as conn:
                # Split into statements (handle database-specific syntax)
                if self.db_type == "postgresql":
                    # PostgreSQL can handle multi-statement execution
                    conn.execute(text(migration_sql))
                    conn.commit()
                else:
                    # MySQL/SQLite: execute statement by statement
                    statements = self._split_sql_statements(migration_sql)
                    for stmt in statements:
                        if stmt.strip():
                            try:
                                conn.execute(text(stmt))
                            except Exception as e:
                                print(f"WARNING: Warning executing statement: {e}")
                    conn.commit()

            print("✓ Migration completed successfully!")
            return True

        except Exception as e:
            print(f"✗ Migration failed: {e}")
            print("\nWARNING: Database may be in an inconsistent state!")
            print("   Restore from backup and check error messages above.")
            return False

    def _split_sql_statements(self, sql: str) -> list[str]:
        """
        Split SQL script into individual statements, handling semicolons in strings and DO blocks.

        Properly handles:
        - Single-quoted strings: 'value'
        - Double-quoted identifiers: "column"
        - Dollar-quoted blocks: $$...$$ or $tag$...$tag$
        - DO blocks: DO $$ BEGIN ... END $$;
        """
        # Remove single-line comments
        sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)

        statements = []
        statement = []
        in_single_quote = False
        in_double_quote = False
        in_dollar_quote = False
        dollar_tag = ""
        i = 0
        length = len(sql)

        while i < length:
            c = sql[i]

            # Handle start of dollar-quoted block (e.g., $$ or $tag$)
            if (
                not in_single_quote
                and not in_double_quote
                and not in_dollar_quote
                and c == "$"
            ):
                # Find the full tag
                m = re.match(r"\$([A-Za-z0-9_]*)\$", sql[i:])
                if m:
                    dollar_tag = m.group(0)
                    in_dollar_quote = True
                    statement.append(dollar_tag)
                    i += len(dollar_tag)
                    continue

            # Handle end of dollar-quoted block
            if in_dollar_quote and sql[i : i + len(dollar_tag)] == dollar_tag:
                statement.append(dollar_tag)
                i += len(dollar_tag)
                in_dollar_quote = False
                continue

            # Handle single quotes
            if not in_double_quote and not in_dollar_quote and c == "'":
                in_single_quote = not in_single_quote
                statement.append(c)
                i += 1
                continue

            # Handle double quotes
            if not in_single_quote and not in_dollar_quote and c == '"':
                in_double_quote = not in_double_quote
                statement.append(c)
                i += 1
                continue

            # Split on semicolon only if not inside any quote/block
            if (
                c == ";"
                and not in_single_quote
                and not in_double_quote
                and not in_dollar_quote
            ):
                stmt = "".join(statement).strip()
                if stmt:
                    statements.append(stmt)
                statement = []
                i += 1
                continue

            statement.append(c)
            i += 1

        # Add any trailing statement
        stmt = "".join(statement).strip()
        if stmt:
            statements.append(stmt)

        return statements

    def verify_migration(self):
        """Verify migration completed successfully"""
        print("\nSUCCESS: Verifying migration...")

        try:
            inspector = inspect(self.engine)

            # Check user_id column exists
            tables = ["chat_history", "short_term_memory", "long_term_memory"]
            for table in tables:
                columns = [c["name"] for c in inspector.get_columns(table)]

                if "user_id" not in columns:
                    print(f"✗ {table}: user_id column missing!")
                    return False

                if table == "long_term_memory" and "version" not in columns:
                    print(f"✗ {table}: version column missing!")
                    return False

            # Check data migration
            with self.engine.connect() as conn:
                for table in tables:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table} WHERE user_id IS NULL")
                    )
                    null_count = result.scalar()

                    if null_count > 0:
                        print(
                            f"✗ {table}: Found {null_count} records with NULL user_id!"
                        )
                        return False

            print("✓ Migration verification passed!")

            # Show post-migration statistics
            print("\nSTATS: Post-migration statistics:")
            with self.engine.connect() as conn:
                for table in tables:
                    result = conn.execute(
                        text(
                            f"SELECT user_id, COUNT(*) as count FROM {table} GROUP BY user_id"
                        )
                    )
                    for row in result:
                        print(f"  {table} - user_id '{row[0]}': {row[1]} records")

            return True

        except Exception as e:
            print(f"✗ Verification failed: {e}")
            return False


def main():
    """Main migration script"""
    parser = argparse.ArgumentParser(
        description="Memori v1.x to v2.0 Migration Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--database", required=True, help="Database connection string")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip backup creation (not recommended)",
    )
    parser.add_argument(
        "--force", action="store_true", help="Force migration even if validation fails"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Memori v1.x → v2.0 Migration Helper")
    print("=" * 70)
    print(f"\nDatabase: {args.database}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")

    # Initialize migration helper
    helper = MigrationHelper(args.database, dry_run=args.dry_run, force=args.force)
    print(f"Detected database type: {helper.db_type}")

    # Step 1: Validate schema
    if not helper.validate_schema():
        print("\nERROR: Schema validation failed. Migration cancelled.")
        sys.exit(1)

    # Step 2: Show current statistics
    helper.show_statistics()

    # Step 3: Create backup
    if not args.skip_backup and not args.dry_run:
        helper._create_backup()
    elif args.skip_backup:
        print("\nWARNING: WARNING: Skipping backup creation!")

    # Step 4: Confirm migration
    if not args.dry_run and not args.force:
        print("\n" + "=" * 70)
        print("WARNING: IMPORTANT: This migration will make breaking changes!")
        print("=" * 70)
        response = input("\nProceed with migration? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled.")
            sys.exit(0)

    # Step 5: Run migration
    success = helper.run_migration()
    if not success:
        print("\nERROR: Migration failed!")
        sys.exit(1)

    # Step 6: Verify migration
    if not args.dry_run:
        if helper.verify_migration():
            print("\n" + "=" * 70)
            print("SUCCESS: MIGRATION COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print("\nNext steps:")
            print("1. Test your application with the new multi-tenant schema")
            print("2. Update code to use user_id instead of namespace")
            print("3. After confirming everything works, drop namespace_legacy columns")
            print("\nTo drop legacy columns:")
            print("  ALTER TABLE chat_history DROP COLUMN namespace_legacy;")
            print("  ALTER TABLE short_term_memory DROP COLUMN namespace_legacy;")
            print("  ALTER TABLE long_term_memory DROP COLUMN namespace_legacy;")
        else:
            print("\nWARNING: Migration completed but verification found issues.")
            print("   Please review the output above.")
            sys.exit(1)
    else:
        print("\nSUCCESS: DRY RUN COMPLETE - No changes made")


if __name__ == "__main__":
    main()
