# Supported Databases

Memori supports multiple relational databases for persistent memory storage. Below is a table of supported databases.

## Supported Database Systems

| Database | Website | Example Link |
|----------|---------|--------------|
| **SQLite** | [https://www.sqlite.org/](https://www.sqlite.org/) | [SQLite Example](https://github.com/GibsonAI/memori/tree/main/examples/databases/sqlite_demo.py) |
| **PostgreSQL** | [https://www.postgresql.org/](https://www.postgresql.org/) | [PostgreSQL Example](https://github.com/GibsonAI/memori/tree/main/examples/databases/postgres_demo.py) |
| **MySQL** | [https://www.mysql.com/](https://www.mysql.com/) | [MySQL Example](https://github.com/GibsonAI/memori/tree/main/examples/databases/mysql_demo.py) |
| **Neon** | [https://neon.com/](https://neon.com/) | [Neon Serverless Postgres Example](./examples/databases/neon_demo.py) |
| **Supabase** | [https://supabase.com/](https://supabase.com/) | PostgreSQL-compatible with real-time features |
| **GibsonAI** | [https://gibsonai.com/](https://gibsonai.com/) | [GibsonAI Serverless MySQL Guide](open-source/databases/gibsonai) |
| **MongoDB** | [https://www.mongodb.com/](https://www.mongodb.com/) | [MongoDB Example](https://github.com/GibsonAI/memori/blob/main/examples/databases/mongodb_demo.py) |

## Quick Start Examples

### SQLite (Recommended for Development)
```python
from memori import Memori

# Simple file-based database
memori = Memori(
    database_connect="sqlite:///memori.db",
    conscious_ingest=True,
    auto_ingest=True
)
```

### PostgreSQL
```python
from memori import Memori

# PostgreSQL connection
memori = Memori(
    database_connect="postgresql+psycopg2://user:password@localhost:5432/memori_db",
    conscious_ingest=True,
    auto_ingest=True
)
```

### MySQL
```python
from memori import Memori

# MySQL connection
memori = Memori(
    database_connect="mysql+pymysql://user:password@localhost:3306/memori_db",
    conscious_ingest=True,
    auto_ingest=True
)
```

### GibsonAI (Serverless MySQL)
```python
from memori import Memori

# GibsonAI serverless database
memori = Memori(
    database_connect="mysql+mysqlconnector://username:password@mysql-assembly.gibsonai.com/database_name",
    conscious_ingest=True,
    auto_ingest=True
)
```

### MongoDB
```python
from memori import Memori

# MongoDB connection
memori = Memori(
    database_connect="mongodb://127.0.0.1:56145/memori",
    conscious_ingest=True,
    auto_ingest=True
)
```