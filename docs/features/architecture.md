[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# Architecture Overview

Memori is built with a modular, enterprise-grade architecture focused on simplicity, reliability, and flexible database integration.

## System Architecture

```
┌─────────────────────────────────────────┐
│ APPLICATION LAYER                       │
|                                         |
│  • Your code + LLM client               │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│ MEMORI CORE                             │
|                                         |
│  • LLM provider wrappers                │
│  • Attribution (entity/process/session) │
│  • Recall API                           │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│ STORAGE LAYER                           │
|                                         |
│  • Connection Registry                  │
|  • Schema Builder                       |
│  • Database Adapters                    │
|  • Database Drivers                     |
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│ DATABASE AGNOSTIC STORAGE               │
└─────────────────────────────────────────┘
```

## Core Components

### 1. Memori Core

**Key Responsibilities:**
- Manage attribution (entity, process, session)
- Coordinate storage and Advanced Augmentation
- Provide LLM provider wrappers
- Expose recall API for semantic search

### 2. LLM Provider Wrappers

**How it works:**

- Intercepts LLM client method calls
- Captures user messages and AI responses
- Persists to database via storage manager
- Supports sync, async, streamed, and unstreamed modes
- Works with OpenAI, Anthropic, Google, xAI, LangChain, Pydantic AI

### 3. Attribution System

**Tracking Model:**
- **Entity**: Person, place, or thing (typically a user)
- **Process**: Agent, program, or workflow
- **Session**: Groups related LLM interactions

### 4. Storage System

**Supported Connections:**
- SQLAlchemy sessionmaker
- DB API 2.0 connections
- Django ORM connections
- MongoDB databases

### 5. Advanced Augmentation

**What it does:**
- Extracts facts from conversations
- Generates embeddings for semantic search
- Identifies preferences, skills, attributes
- Runs asynchronously with no latency impact
- Upgrade via MEMORI_API_KEY (free tier available)

## Data Flow

### 1. Conversation Capture

```mermaid
sequenceDiagram
    participant App as Your Application
    participant Wrapper as LLM Wrapper
    participant LLM as LLM Provider
    participant Storage as Storage Manager
    participant DB as Database

    App->>Wrapper: client.chat.completions.create(...)
    Wrapper->>LLM: Forward request
    LLM->>Wrapper: Response
    Wrapper->>Storage: Persist conversation
    Storage->>DB: Write to database
    Wrapper->>App: Return response
```

### 2. Attribution Tracking

```mermaid
sequenceDiagram
    participant App as Application
    participant Memori as Memori Core
    participant Storage as Storage
    participant DB as Database

    App->>Memori: attribution(entity_id, process_id)
    App->>Memori: LLM call
    Memori->>Storage: Store with attribution
    Storage->>DB: INSERT with entity/process/session
```

### 3. Recall API Flow

```mermaid
sequenceDiagram
    participant App as Application
    participant Recall as Recall API
    participant Embed as Embedding Service
    participant DB as Database

    App->>Recall: recall("Mars color", limit=5)
    Recall->>Embed: Embed query
    Embed->>Recall: Query embedding
    Recall->>DB: Vector similarity search
    DB->>Recall: Ranked facts
    Recall->>App: Return facts
```

### 4. Background Augmentation

```mermaid
sequenceDiagram
    participant Storage as Storage
    participant Aug as Augmentation
    participant API as Memori API
    participant DB as Database

    Storage->>Aug: New conversation
    Aug->>API: Send for processing
    API->>API: Extract facts, preferences, etc.
    API->>DB: Store enhanced memories
    Note over Aug,DB: Happens asynchronously
```

## Configuration

### Environment Variables

```bash
# Memori API key for Advanced Augmentation
export MEMORI_API_KEY="your-api-key"
```
