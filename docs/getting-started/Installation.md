[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# Installation

```bash
pip install memori
```

## Examples

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

## API Key Setup (Optional)

Advanced Augmentation enhances your memories in the background. It's rate limited by IP address without an API key, or you can sign up for increased limits.

### Option 1: Environment Variable

```bash
export MEMORI_API_KEY="your-api-key-here"
```

### Option 2: .env File

Create `.env` file in your project:

```
MEMORI_API_KEY=your-api-key-here
```

### Option 3: Sign Up via CLI

```bash
python3 -m memori sign-up your-email@example.com
```

### Check Your Quota

```bash
python3 -m memori quota
```

Or you can visit [https://memorilabs.ai/](https://memorilabs.ai/) to manage your account.
