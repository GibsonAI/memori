import os
from pathlib import Path

import pytest

from memori.database.export_import import ExportManager, ImportManager
from memori.database.models import ChatHistory
from memori.database.sqlalchemy_manager import SQLAlchemyDatabaseManager

POSTGRES_URL = os.getenv("MEMORI_TEST_POSTGRES_URL")

if not POSTGRES_URL:
    pytest.skip(
        "Set MEMORI_TEST_POSTGRES_URL to run cross-database export/import tests",
        allow_module_level=True,
    )


def _seed_sqlite(manager):
    session = manager.get_session()
    try:
        session.add(
            ChatHistory(
                chat_id="cross-chat",
                user_input="ping",
                ai_output="pong",
                model="gpt-test",
                session_id="cross-session",
                user_id="cross-user",
                assistant_id="cross-assistant",
            )
        )
        session.commit()
    finally:
        session.close()


@pytest.mark.integration
def test_sqlite_export_postgres_import(tmp_path: Path):
    sqlite_manager = SQLAlchemyDatabaseManager(f"sqlite:///{tmp_path/'cross.db'}")
    sqlite_manager.initialize_schema()
    _seed_sqlite(sqlite_manager)

    export_path = tmp_path / "cross.json"
    ExportManager(sqlite_manager).export(
        export_path=str(export_path),
        format="json",
    )

    postgres_manager = SQLAlchemyDatabaseManager(POSTGRES_URL)
    import_result = ImportManager(postgres_manager).import_data(
        import_path=str(export_path),
        target_user_id="cross-user",
        target_assistant_id="cross-assistant",
    )

    assert import_result["imported"]["chat_history"] == 1
    assert import_result["errors"] == []
    sqlite_manager.close()
    postgres_manager.close()


@pytest.mark.integration
def test_postgres_export_sqlite_import(tmp_path: Path):
    """Validate reverse direction: Postgres → SQLite."""
    # Set up Postgres source
    postgres_manager = SQLAlchemyDatabaseManager(POSTGRES_URL)
    postgres_manager.initialize_schema()
    _seed_sqlite(postgres_manager)

    export_path = tmp_path / "pg_to_sqlite.json"
    ExportManager(postgres_manager).export(
        export_path=str(export_path),
        format="json",
    )

    sqlite_manager = SQLAlchemyDatabaseManager(f"sqlite:///{tmp_path/'pg_import.db'}")
    sqlite_manager.initialize_schema()

    import_result = ImportManager(sqlite_manager).import_data(
        import_path=str(export_path),
        target_user_id="cross-user",
        target_assistant_id="cross-assistant",
    )

    assert import_result["imported"]["chat_history"] == 1
    assert import_result["errors"] == []
    sqlite_manager.close()
    postgres_manager.close()