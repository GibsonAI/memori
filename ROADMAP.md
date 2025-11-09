# Memori OSS Roadmap 2025

This roadmap shows planned and in-progress improvements for **Memori OSS.**

Community contributions are welcome. Please check the roadmap and open issues in the repo. 

## Core Features

| Feature | Description | Status | Notes | Issue Link |
| --- | --- | --- | --- | --- |
| **Ingest Unstructured Data** | Support ingestion from raw text, documents, and URLs to expand input sources. | [PLANNED] Planned | Enables ingestion from multiple unstructured sources. |  |
| **Graph-Based Search in SQL** | Enable hybrid relational + graph queries for contextual recall. | [PLANNED] In Progress | Core for semantic + relational search. |  |
| **Support for Pydantic-AI Framework** | Add native support for Pydantic-AI integration. | [PLANNED] Planned | Smooth integration with typed AI models. |  |
| **Add `user_id` Namespace Feature** | Allow multi-user memory isolation using namespaces. | [IN_PROGRESS] Buggy / Needs Fix | Implemented but has issues; debugging ongoing. |  |
| **Data Ingestion from Gibson DB** | Direct ingestion connector from GibsonAI databases. | [PLANNED] Planned | Needed for GibsonAI-SaaS sync. |  |
| **Image Processing in Memori** | Enable image-based retrieval with multi-turn memory. | [PLANNED] Planned | Use case: “Show me red shoes → under $100”. |  |
| **Methods to Connect with GibsonAI** | Improve linking between Memori OSS and GibsonAI agent infrastructure. | [PLANNED] Planned | Define standard connection methods. |  |
| **AzureOpenAI Auto-Record** | Auto-record short-term memory from Azure OpenAI sessions. | [PLANNED] Planned | Enables automatic session memory capture. |  |
| **Update `memori_schema` for GibsonAI Deployment** | Align schema with GibsonAI SaaS structure. | [PLANNED] Planned | Required for compatibility. |  |

## Developer Experience & Integrations

| Feature | Description | Status | Notes | Issue Link |
| --- | --- | --- | --- | --- |
| Memori REST API | First-class REST interface mirroring Python SDK | [PLANNED] Planned | Implement Fast API Ship OpenAPI spec + examples.  |  |
| **Update Docs** | Refresh documentation with new APIs, architecture, and examples. | [PLANNED] Planned | High priority for OSS visibility. |  |
| **Technical Paper of Memori** | Publish a public technical paper describing architecture and benchmarks. | [PLANNED] In Progress | Draft under review. |  |
| **LoCoMo Benchmark of Memori** | Benchmark Memori’s latency and recall performance. | [PLANNED] Planned | Compare against existing memory solutions. |  |
| **Refactor Codebase** | Clean up and modularize code for better maintainability. | [PLANNED] Planned | Prep for wider community contributions. |  |
| **Improve Error Handling (DB Dependency)** | Add graceful fallbacks for database and schema dependency issues. | [PLANNED] In Progress | Improves reliability across deployments. |  |

## Stability, Testing & Bug Fixes

| Feature | Description | Status | Notes | Issue Link |
| --- | --- | --- | --- | --- |
| **Duplicate Memory Creation** | Fix duplicate entries appearing in both short-term and long-term memory. | [IN_PROGRESS] Known Issue | Observed during testing. |  |
| **Search Recursion Issue** | Resolve recursive memory lookups in remote DB environments. | [CRITICAL] Critical | High-priority fix needed. |  |
| **Postgres FTS (Neon) Issue** | Fix partial search failure with full-text search on Neon Postgres. | [PLANNED] Known Issue | Search works partially but inconsistently. |  |
| **Gibson Issues with Memori** | Debug integration-level issues when used within GibsonAI. | [PLANNED] Planned | Needs collaboration with GibsonAI team. |  |