# Integrations

Seamlessly integrate Memori with popular databases, agent frameworks, tools and infra you already use.

## CockroachDB

Memori uses CockroachDB as a distributed, strongly consistent data store for long-term AI memory. CockroachDB provides fault tolerance and global availability, enabling Memori-based applications to preserve state reliably at any scale.

## MongoDB

Memori integrates with MongoDB to store AI memory as flexible JSON documents. Memori structures conversational data into queryable memory objects, while MongoDB provides a schema-flexible, horizontally scalable backend optimized for dynamic or nested data. This combination allows AI applications to maintain evolving long-term state with minimal schema management and efficient document-level operations.

## Neon

Memori works with Neon’s serverless Postgres to provide scalable, cost-efficient storage for AI memory. Memori expresses conversation state as structured SQL data, and Neon handles autoscaling, branching, and compute separation without user-managed infrastructure. This setup makes it easy to prototype, share, and deploy AI applications while maintaining persistent memory and paying only for the resources used.

## Postgres

Memori stores AI memory natively in Postgres using structured tables optimized for retrieval, state tracking, and long-term context. Postgres offers strong consistency, robust indexing, and broad ecosystem support, making it a reliable default for applications that need durable, queryable AI memory without additional operational complexity.

## SQLite

Memori can run on SQLite for lightweight, embedded, or local AI applications. Memory is stored in a single file with zero external dependencies, making this integration ideal for prototyping, edge deployments, offline agents, and resource-constrained environments. SQLite provides predictable performance and simple persistence for smaller-scale or standalone AI workloads.