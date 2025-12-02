[![Memori Labs](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/banner.png)](https://memorilabs.ai/)

# Introduction to Advanced Augmentation

Memori Advanced Augmentation is an AI/ML driven system for using LLM exchanges to improve context.

## How Does It Work

With Memori, you are creating a schema inside of your datastore by executing the following call:

```python
Memori(conn=db_session_factory).config.storage.build()
```

Advanced Augmentation will automatically insert data into this schema as a user (for example) has conversations with an LLM.

Memori is able to process these conversations once you register your LLM client. Here is an example registering an OpenAI client:

```python
from openai import OpenAI
from memori import Memori

client = OpenAI(...)
mem = Memori().openai.register(client)
```

## Conversations

The back and forth questions and statements and responses from the LLM are automatically stored inside your datastore. Memori will recall and add the messages to subsequent LLM calls. We call this conversation tracking.

Tables involved in Conversations:
- memori_conversation
- memori_conversation_message

## Sessions

The back and forth exchanges with the LLM are automatically grouped together into a session. This ensures you can recall entire conversations that were related to a particular exchange (or agentic workflow) between the user and the LLM.

Tables involved in Sessions:
- memori_session

## Entity & Process

Memory has two core components to which data is attributed:
- entity: think person, place, or thing; like a user
- process: think your agent, LLM interaction or program

Advanced Augmentation will "attach" data to each of these while the entity (user) is having a conversation with an LLM (process).

Tables involved in Entity & Process
- memori_entity
- memori_process

## Facts

Facts are extracted from the LLM conversations and attributed to the entity. They include a vector embedding, the number of times they were mentioned and the last time they were mentioned.

The vector embedding is created using a sentence transformer with 768 dimensions and is critical for recalling memories to enhance context.

Using Advanced Augmentation, Memori automatically creates facts and writes them to your datastore.

Tables involved in Facts
- memori_entity_fact

## Attributes

Attributes are extracted from the LLM conversations and attributed to the process. The goal is to learn what your process typically talks about or provides to the user to make sure we match the best facts from the user to the process. This will ensure the most accurate context.

Tables involved in Attributes:
- memori_process_attribute

## Semantic Triples

To create facts, Advanced Augmentation uses named-entity recognition to create semantic triples (subject, predicate, object). Memori will automatically store (and dedupe) the semantic triples in your datastore including building a knowledge graph.

Tables involved in Semantic Triples:
- memori_subject
- memori_predicate
- memori_object
- memori_knowledge_graph

## Context Recall

When a query is being sent to an LLM, we intercept the call and use semantic search to match the best entity facts to the query. Memori will extract the facts attributed to the entity and pass the vector embeddings to FAISS. The N most relevant facts are then added to the system prompt to provide enhanced context to the exchange.

## Attribution

In order for Memori to provide all of the capabilities it's designed for, attribution is critical. You can create attribution by executing the following:

```python
mem.attribution(entity_id="12345", process_id="my-ai-bot")
```

## ERD

![Memori Schema ERD](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/erd.png)

## When to Use It

- Chatbots or AI assistants with returning users
- Use cases that need to remember user preferences across sessions
- You want personalized AI interactions
- With multi-step workflows or agentic systems
- For building relationships between entities

## Comparison

![](https://s3.us-east-1.amazonaws.com/images.memorilabs.ai/comparison.png)
