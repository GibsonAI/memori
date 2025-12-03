[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

<p align="center">
  <strong>The memory fabric for enterprise AI</strong>
</p>

<p align="center">
  <i>Memori plugs into the software and infrastructure you already use. It is LLM, datastore and framework agnostic and seamlessly integrates into the architecture you've already designed.</i>
</p>
<p align="center">
  <a href="https://trendshift.io/repositories/15418">
    <img src="https://trendshift.io/_next/image?url=https%3A%2F%2Ftrendshift.io%2Fapi%2Fbadge%2Frepositories%2F15418&w=640&q=75" alt="Memori%2fLabs%2FMemori | Trendshif">
  </a>
</p>

<p align="center">
  <a href="https://badge.fury.io/py/memori">
    <img src="https://badge.fury.io/py/memori.svg" alt="PyPI version">
  </a>
  <a href="https://pepy.tech/projects/memori">
    <img src="https://static.pepy.tech/badge/memori" alt="Downloads">
  </a>
  <a href="https://opensource.org/license/apache-2-0">
    <img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="License">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="Python 3.8+">
  </a>
  <a href="https://discord.gg/abD4eGym6v">
    <img src="https://img.shields.io/discord/1042405378304004156?logo=discord" alt="Discord">
  </a>
</p>

<p align="center">
  <a href="https://github.com/MemoriLabs/Memori/stargazers">
    <img src="https://img.shields.io/badge/⭐%20Give%20a%20Star-Support%20the%20project-orange?style=for-the-badge" alt="Give a Star">
  </a>
</p>

---

## Getting Started

Install Memori:

```bash
pip install memori
```

## What's New In v3?

- Significant performance improvements using Advanced Augmentation.
- Threaded, zero latency replacement for the v2 extraction agent.
- LLM agnostic with support for all of the major foundational models.
- Datastore agnostic with support for all major databases and document stores.
- Adapter/driver architecture to make contributions easier.
- Vectorized memories and in-memory semantic search for more accurate context.
- Third normal form schema including storage of semantic triples for a knowledge graph.
- Reduced development overhead to a single line of code.
- Automatic schema migrations.

## Example with OpenAI

```python
from openai import OpenAI
from memori import Memori

client = OpenAI(...)
mem = Memori().openai.register(client)
```

## Attribution

To get the most out of Memori, you want to attribute your LLM interactions to an entity (think person, place or thing; like a user) and a process (think your agent, LLM interaction or program).

If you do not provide any attribution, Memori cannot make memories for you.

```python
mem.attribution(entity_id="12345", process_id="my-ai-bot")
```

## Session Management

Memori uses sessions to group your LLM interactions together. For example, if you have an agent that executes multiple steps you want those to be recorded in a single session.

By default, Memori handles setting the session for you but you can start a new session or override the session by executing the following:

```python
mem.new_session()
```

or

```python
session_id = mem.config.session_id

# ...

mem.set_session(session_id)
```

## Suggested Setup

To make sure everything is installed in the most efficient manner, we suggest you execute the following once:

```bash
python -m memori setup
```

This step is not necessary but will prep your environment for faster execution. If you do not perform this step, it will be executed the first time Memori is run which will cause the first execution (and only the first one) to be a little slower.

## Configure Your Database

1. Run this command once, via CI/CD or anytime you update Memori.

    ```python
    Memori(conn=db_session_factory).config.storage.build()
    ```

2. Instantiate Memori with the connection factory.

    ```python
    from openai import OpenAI
    from memori import Memori

    client = OpenAI(...)
    mem = Memori(conn=db_session_factory).openai.register(client)
    ```

## Quickstart Example

```python
import os

from memori import Memori
from openai import OpenAI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Setup SQLite
engine = create_engine("sqlite:///memori.db")
Session = sessionmaker(bind=engine)

# Setup Memori - that's it!
mem = Memori(conn=Session).openai.register(client)
mem.attribution(entity_id="user-123", process_id="my-app")
mem.config.storage.build()

# First conversation - establish facts
response1 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "My favorite color is blue"}],
)
print(response1.choices[0].message.content)

# Second conversation - Memori recalls context automatically
response2 = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What's my favorite color?"}],
)
print(response2.choices[0].message.content)  # AI remembers: "blue"!
```

## Supported LLM

- Anthropic
- Bedrock
- Gemini
- Grok (xAI)
- OpenAI

_(unstreamed, streamed, synchronous and asynchronous)_

## Supported Frameworks

- LangChain
- Pydantic AI

## Supported Database Integrations

- **DB API 2.0** - Direct support for any Python database driver that implements the [PEP 249 Database API Specification v2.0](https://peps.python.org/pep-0249/). This includes drivers like `psycopg`, `pymysql`, `MySQLdb`, `cx_Oracle`, `oracledb`, and `sqlite3`.
- **Django** - Native integration with Django's ORM and database layer
- SQLAlchemy

## Supported Datastores

- [CockroachDB](https://github.com/MemoriLabs/Memori/tree/main/examples/cockroachdb) - Full example with setup instructions
- MariaDB
- [MongoDB](https://github.com/MemoriLabs/Memori/tree/main/examples/mongodb) - Full example with setup instructions
- MySQL
- [Neon](https://github.com/MemoriLabs/Memori/tree/main/examples/neon) - Full example with setup instructions
- Oracle
- [PostgreSQL](https://github.com/MemoriLabs/Memori/tree/main/examples/postgres) - Full example with setup instructions
- [SQLite](https://github.com/MemoriLabs/Memori/tree/main/examples/sqlite) - Full example with setup instructions
- Supabase

## Memori Advanced Augmentation

Memories are tracked at several different levels:

- entity: think person, place, or thing; like a user
- process: think your agent, LLM interaction or program
- session: the current interactions between the entity, process and the LLM

[Memori's Advanced Augmentation](https://github.com/MemoriLabs/Memori/blob/main/docs/advanced-augmentation.md) enhances memories at each of these levels with:

- attributes
- events
- facts
- people
- preferences
- relationships
- rules
- skills

Memori knows who your user is, what tasks your agent handles and creates unparalleled context between the two. Augmentation occurs in the background incurring no latency.

By default, Memori Advanced Augmentation is available without an account but rate limited. When you need increased limits, [sign up for Memori Advanced Augmentation](https://app.memorilabs.ai/signup) or execute the following:

```bash
python -m memori sign-up <email_address>
```

Memori Advanced Augmentation is always free for developers!

Once you've obtained an API key, simply set the following environment variable:

```bash
export MEMORI_API_KEY=[api_key]
```

## Managing Your Quota

At any time, you can check your quota by executing the following:

```bash
python -m memori quota
```

Or by checking your account at [https://memorilabs.ai/](https://memorilabs.ai/). If you have reached your IP address quota, sign up and get an API key for increased limits.

If your API key exceeds its quota limits we will email you and let you know.

## Command Line Interface (CLI)

To use the Memori CLI, execute the following from the command line:

```bash
python -m memori
```

This will display a menu of the available options. For more information about what you can do with the Memori CLI, please reference [Command Line Interface](https://github.com/MemoriLabs/Memori/blob/main/docs/cli.md).

## Contributing

We welcome contributions from the community! Please see our [Contributing Guidelines](https://github.com/MemoriLabs/Memori/blob/main/CONTRIBUTING.md) for details on:

- Setting up your development environment
- Code style and standards
- Submitting pull requests
- Reporting issues

---

## Support

- **Documentation**: [https://memorilabs.ai/docs](https://memorilabs.ai/docs)
- **Discord**: [https://discord.gg/abD4eGym6v](https://discord.gg/abD4eGym6v)
- **Issues**: [GitHub Issues](https://github.com/MemoriLabs/Memori/issues)

---

## License

Apache 2.0 - see [LICENSE](https://github.com/MemoriLabs/Memori/blob/main/LICENSE)

---

**Star us on GitHub** to support the project

[![Star History](https://api.star-history.com/svg?repos=MemoriLabs/memori&type=date)](https://star-history.com/#MemoriLabs/memori)
