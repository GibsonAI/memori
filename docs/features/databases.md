[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

## Connection Methods

| Method         | Description                              | Use Case                                  |
| -------------- | ---------------------------------------- | ----------------------------------------- |
| **SQLAlchemy** | Industry-standard ORM with sessionmaker  | Production applications, connection pools |
| **DB API 2.0** | Direct Python database drivers (PEP 249) | Lightweight, minimal dependencies         |
| **Django**     | Native Django ORM integration            | Django applications

## Supported Databases

| Database        | Website                                                              | Example Link                                                                             |
| --------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **SQLite**      | [https://www.sqlite.org/](https://www.sqlite.org/)                   | [SQLite Example](https://github.com/MemoriLabs/Memori/tree/main/examples/sqlite)           |
| **PostgreSQL**  | [https://www.postgresql.org/](https://www.postgresql.org/)           | [PostgreSQL Example](https://github.com/MemoriLabs/Memori/tree/main/examples/postgres)     |
| **MySQL**       | [https://www.mysql.com/](https://www.mysql.com/)                     | MySQL-compatible drivers                                                                 |
| **MariaDB**     | [https://mariadb.org/](https://mariadb.org/)                         | MySQL-compatible drivers                                                                 |
| **Neon**        | [https://neon.tech/](https://neon.tech/)                             | [Neon Example](https://github.com/MemoriLabs/Memori/tree/main/examples/neon)               |
| **Supabase**    | [https://supabase.com/](https://supabase.com/)                       | PostgreSQL-compatible with real-time features                                            |
| **CockroachDB** | [https://www.cockroachlabs.com/](https://www.cockroachlabs.com/)     | [CockroachDB Example](https://github.com/MemoriLabs/Memori/tree/main/examples/cockroachdb) |
| **MongoDB**     | [https://www.mongodb.com/](https://www.mongodb.com/)                 | [MongoDB Example](https://github.com/MemoriLabs/Memori/tree/main/examples/mongodb)         |
| **Oracle**      | [https://www.oracle.com/database/](https://www.oracle.com/database/) | Oracle database support                                                                  |

## Quick Start Examples

### SQLite with SQLAlchemy

```python
from memori import Memori
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///memori.db")
SessionLocal = sessionmaker(bind=engine)

mem = Memori(conn=SessionLocal)
```

### PostgreSQL with SQLAlchemy

```python
from memori import Memori
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    "postgresql+psycopg://user:password@host:5432/database",
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine)

mem = Memori(conn=SessionLocal)
```

### MySQL with SQLAlchemy

```python
from memori import Memori
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    "mysql+pymysql://user:password@host:3306/database",
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine)

mem = Memori(conn=SessionLocal)
```

### MongoDB with PyMongo

```python
from memori import Memori
from pymongo import MongoClient

client = MongoClient("mongodb://host:27017/")

def get_db():
    return client["memori"]

mem = Memori(conn=get_db)
```

### CockroachDB with SQLAlchemy

```python
from memori import Memori
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    "postgresql+psycopg://user:password@host:5432/database",
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine)

mem = Memori(conn=SessionLocal)
```

## Connection Patterns

### Connection Factory

Pass a callable that returns a new connection/session:

```python
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)

# Memori calls SessionLocal() when it needs a connection
mem = Memori(conn=SessionLocal)
```

### MongoDB Pattern

MongoDB uses a function that returns the database:

```python
def get_db():
    return mongo_client["database_name"]

mem = Memori(conn=get_db)
```

## Migration and Schema

### Building Schema

Run this command once, via CI/CD or anytime you update Memori:

```python
Memori(conn=db_session_factory).config.storage.build()
```

This creates the schema Memori needs to store structured information.
