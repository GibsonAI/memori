from memori import Memori
from tests.database.core import TestDBSession


def init_db():
    try:
        session = TestDBSession()
        mem = Memori(conn=session)
        if mem.config.storage is not None:
            mem.config.storage.build()
        print("Database schema initialized successfully")
        return True
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        return False


if __name__ == "__main__":
    init_db()
