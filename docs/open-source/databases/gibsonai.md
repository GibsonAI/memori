# GibsonAI Database Integration

Learn how to use Memori with a serverless database in GibsonAI platform for persistent memory storage.

## Overview

[GibsonAI](https://gibsonai.com/) provides a serverless MySQL/PostgreSQL compatible database platform that seamlessly integrates with Memori for persistent memory storage. This integration allows you to maintain conversation memory across sessions with zero database management overhead.

## Quick Setup

### 1. Create a GibsonAI Account

1. Visit [https://app.gibsonai.com/](https://app.gibsonai.com/)
2. Sign up for a FREE account

### 2. Create a Database Project

1. Click "Create New Project" in the GibsonAI dashboard
2. Use a prompt like: "Create an empty database"

### 3. Get Your Connection String

1. Navigate to the **Databases** tab in your GibsonAI project
2. Choose your environment:
   - **Development**: For testing and development
   - **Production**: For live applications
3. Copy the MySQL connection string provided

The connection string format looks like:
```
mysql+mysqlconnector://username:password@mysql-assembly.gibsonai.com/database_name
```

### 4. Install Dependencies

```bash
pip install memorisdk openai mysql-connector-python
```

### 5. Set Environment Variables

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

## Basic Usage

### Simple Integration

```python
from openai import OpenAI
from memori import Memori

# Initialize OpenAI client
openai_client = OpenAI()

# Initialize Memori with GibsonAI database
memori = Memori(
    database_connect="mysql+mysqlconnector://your_username:your_password@mysql-assembly.gibsonai.com/your_database",
    conscious_ingest=True,
    auto_ingest=True,
)

# Enable memory tracking
memori.enable()

# Use with any LLM conversation
response = openai_client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Hello, I'm learning Python!"}]
)

print(response.choices[0].message.content)
```