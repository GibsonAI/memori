"""
Couchbase schema generator for Memori
Defines collections, validation rules, and indexes for Couchbase
"""

from typing import Any

from ..connectors.base_connector import BaseSchemaGenerator, DatabaseType


class CouchbaseSchemaGenerator(BaseSchemaGenerator):
    """Couchbase-specific schema generator"""

    def __init__(self):
        super().__init__(DatabaseType.COUCHBASE)

    def generate_core_schema(self) -> str:
        """
        Generate Couchbase schema documentation
        Note: Couchbase is schemaless, but we provide documentation for expected structure
        """
        return """
# Couchbase Collections Schema for Memori

## Collection: chat_history
Purpose: Store chat interactions between users and AI
Expected Document Structure:
{
    "chat_id": "string (required, unique document key)",
    "user_input": "string",
    "ai_output": "string",
    "model": "string",
    "timestamp": "datetime",
    "session_id": "string",
    "namespace": "string (default: 'default')",
    "tokens_used": "number",
    "metadata": "object (optional)"
}

## Collection: short_term_memory
Purpose: Store temporary memories with expiration
Expected Document Structure:
{
    "memory_id": "string (required, unique document key)",
    "chat_id": "string (optional, reference to chat_history)",
    "processed_data": "object",
    "importance_score": "number (0.0-1.0)",
    "category_primary": "string",
    "retention_type": "string (default: 'short_term')",
    "namespace": "string (default: 'default')",
    "created_at": "datetime",
    "expires_at": "datetime (optional)",
    "access_count": "number (default: 0)",
    "last_accessed": "datetime (optional)",
    "searchable_content": "string",
    "summary": "string",
    "is_permanent_context": "boolean (default: false)"
}

## Collection: long_term_memory
Purpose: Store persistent memories with enhanced metadata
Expected Document Structure:
{
    "memory_id": "string (required, unique document key)",
    "original_chat_id": "string (optional)",
    "processed_data": "object",
    "importance_score": "number (0.0-1.0)",
    "category_primary": "string",
    "retention_type": "string (default: 'long_term')",
    "namespace": "string (default: 'default')",
    "created_at": "datetime",
    "access_count": "number (default: 0)",
    "last_accessed": "datetime (optional)",
    "searchable_content": "string",
    "summary": "string",
    "novelty_score": "number (0.0-1.0, default: 0.5)",
    "relevance_score": "number (0.0-1.0, default: 0.5)",
    "actionability_score": "number (0.0-1.0, default: 0.5)",

    // Enhanced Classification Fields
    "classification": "string (default: 'conversational')",
    "memory_importance": "string (default: 'medium')",
    "topic": "string (optional)",
    "entities_json": "array (default: [])",
    "keywords_json": "array (default: [])",

    // Conscious Context Flags
    "is_user_context": "boolean (default: false)",
    "is_preference": "boolean (default: false)",
    "is_skill_knowledge": "boolean (default: false)",
    "is_current_project": "boolean (default: false)",
    "promotion_eligible": "boolean (default: false)",

    // Memory Management
    "duplicate_of": "string (optional)",
    "supersedes_json": "array (default: [])",
    "related_memories_json": "array (default: [])",

    // Technical Metadata
    "confidence_score": "number (0.0-1.0, default: 0.8)",
    "extraction_timestamp": "datetime",
    "classification_reason": "string (optional)",

    // Processing Status
    "processed_for_duplicates": "boolean (default: false)",
    "conscious_processed": "boolean (default: false)"
}
"""

    def generate_indexes(self) -> str:
        """Generate Couchbase N1QL index creation documentation"""
        return """
# Couchbase Indexes for Memori

## Primary Indexes (Required for N1QL queries)

CREATE PRIMARY INDEX ON `bucket_name`.`_default`.`chat_history`;
CREATE PRIMARY INDEX ON `bucket_name`.`_default`.`short_term_memory`;
CREATE PRIMARY INDEX ON `bucket_name`.`_default`.`long_term_memory`;

## Secondary Indexes for Performance

-- Chat History Indexes
CREATE INDEX idx_chat_namespace_session ON `bucket_name`.`_default`.`chat_history`(namespace, session_id);
CREATE INDEX idx_chat_timestamp ON `bucket_name`.`_default`.`chat_history`(timestamp);
CREATE INDEX idx_chat_model ON `bucket_name`.`_default`.`chat_history`(model);

-- Short-term Memory Indexes
CREATE INDEX idx_short_term_namespace ON `bucket_name`.`_default`.`short_term_memory`(namespace);
CREATE INDEX idx_short_term_category ON `bucket_name`.`_default`.`short_term_memory`(category_primary);
CREATE INDEX idx_short_term_importance ON `bucket_name`.`_default`.`short_term_memory`(importance_score);
CREATE INDEX idx_short_term_expires ON `bucket_name`.`_default`.`short_term_memory`(expires_at);
CREATE INDEX idx_short_term_created ON `bucket_name`.`_default`.`short_term_memory`(created_at);
CREATE INDEX idx_short_term_access ON `bucket_name`.`_default`.`short_term_memory`(access_count, last_accessed);
CREATE INDEX idx_short_term_permanent ON `bucket_name`.`_default`.`short_term_memory`(is_permanent_context);

-- Long-term Memory Indexes
CREATE INDEX idx_long_term_namespace ON `bucket_name`.`_default`.`long_term_memory`(namespace);
CREATE INDEX idx_long_term_category ON `bucket_name`.`_default`.`long_term_memory`(category_primary);
CREATE INDEX idx_long_term_importance ON `bucket_name`.`_default`.`long_term_memory`(importance_score);
CREATE INDEX idx_long_term_created ON `bucket_name`.`_default`.`long_term_memory`(created_at);
CREATE INDEX idx_long_term_access ON `bucket_name`.`_default`.`long_term_memory`(access_count, last_accessed);
CREATE INDEX idx_long_term_classification ON `bucket_name`.`_default`.`long_term_memory`(classification);
CREATE INDEX idx_long_term_topic ON `bucket_name`.`_default`.`long_term_memory`(topic);
CREATE INDEX idx_long_term_scores ON `bucket_name`.`_default`.`long_term_memory`(novelty_score, relevance_score, actionability_score);

## Composite Indexes for Common Queries

CREATE INDEX idx_short_term_namespace_category ON `bucket_name`.`_default`.`short_term_memory`(namespace, category_primary, importance_score);
CREATE INDEX idx_long_term_namespace_category ON `bucket_name`.`_default`.`long_term_memory`(namespace, category_primary, importance_score);
"""

    def generate_search_setup(self) -> str:
        """Generate Couchbase full-text search configuration"""
        return """
# Couchbase Full-Text Search Configuration

## Search Index Definitions

Note: Full-text search indexes in Couchbase are created via the Couchbase Admin API or UI.
Below are the recommended search index configurations for Memori.

### Chat History Search Index

Index Name: idx_chat_history_fts
Type: fulltext-index
Source Type: couchbase
Source Name: memori_bucket
Scope: _default
Collection: chat_history

Index Definition:
{
  "mapping": {
    "types": {
      "chat_history": {
        "properties": {
          "chat_id": {"enabled": true, "index": "no"},
          "user_input": {"enabled": true, "index": "yes"},
          "ai_output": {"enabled": true, "index": "yes"},
          "namespace": {"enabled": true, "index": "no"},
          "session_id": {"enabled": true, "index": "no"}
        }
      }
    }
  },
  "params": {},
  "type": "fulltext-index",
  "name": "idx_chat_history_fts",
  "sourceType": "gocbcore",
  "sourceName": "memori_bucket",
  "sourceUUID": "",
  "planParams": {
    "maxPartitionsPerPIndex": 1024,
    "indexPartitions": 1
  }
}

### Memory Search Index

Index Name: idx_memory_fts
Type: fulltext-index
Source Type: couchbase
Source Name: memori_bucket
Scope: _default
Collections: short_term_memory, long_term_memory

Index Definition:
{
  "mapping": {
    "types": {
      "short_term_memory": {
        "properties": {
          "memory_id": {"enabled": true, "index": "no"},
          "searchable_content": {"enabled": true, "index": "yes", "store": true},
          "summary": {"enabled": true, "index": "yes", "store": true},
          "namespace": {"enabled": true, "index": "no"},
          "category_primary": {"enabled": true, "index": "no"}
        }
      },
      "long_term_memory": {
        "properties": {
          "memory_id": {"enabled": true, "index": "no"},
          "searchable_content": {"enabled": true, "index": "yes", "store": true},
          "summary": {"enabled": true, "index": "yes", "store": true},
          "namespace": {"enabled": true, "index": "no"},
          "category_primary": {"enabled": true, "index": "no"}
        }
      }
    }
  },
  "params": {},
  "type": "fulltext-index",
  "name": "idx_memory_fts",
  "sourceType": "gocbcore",
  "sourceName": "memori_bucket",
  "sourceUUID": "",
  "planParams": {
    "maxPartitionsPerPIndex": 1024,
    "indexPartitions": 1
  }
}
"""

    def generate_collections_schema(self) -> dict[str, dict[str, Any]]:
        """Generate Couchbase collections schema"""
        return {
            "chat_history": {
                "description": "Chat history collection",
                "document_structure": {
                    "chat_id": "string (primary key)",
                    "user_input": "text",
                    "ai_output": "text",
                    "model": "string",
                    "timestamp": "datetime",
                    "session_id": "string",
                    "namespace": "string",
                },
            },
            "short_term_memory": {
                "description": "Short-term memory collection",
                "document_structure": {
                    "memory_id": "string (primary key)",
                    "chat_id": "string (optional)",
                    "processed_data": "object",
                    "importance_score": "number",
                    "category_primary": "string",
                    "namespace": "string",
                    "created_at": "datetime",
                    "expires_at": "datetime (optional)",
                    "searchable_content": "text",
                    "summary": "text",
                },
            },
            "long_term_memory": {
                "description": "Long-term memory collection",
                "document_structure": {
                    "memory_id": "string (primary key)",
                    "original_chat_id": "string (optional)",
                    "processed_data": "object",
                    "importance_score": "number",
                    "category_primary": "string",
                    "namespace": "string",
                    "created_at": "datetime",
                    "searchable_content": "text",
                    "summary": "text",
                    "classification": "string",
                },
            },
        }

    def generate_indexes_schema(self) -> list[dict[str, Any]]:
        """Generate Couchbase indexes schema"""
        bucket = "memori"  # Default bucket name
        return [
            {
                "name": "idx_chat_namespace_session",
                "definition": f"CREATE INDEX idx_chat_namespace_session ON `{bucket}`.`_default`.`chat_history`(namespace, session_id);",
            },
            {
                "name": "idx_chat_timestamp",
                "definition": f"CREATE INDEX idx_chat_timestamp ON `{bucket}`.`_default`.`chat_history`(timestamp);",
            },
            {
                "name": "idx_short_term_namespace",
                "definition": f"CREATE INDEX idx_short_term_namespace ON `{bucket}`.`_default`.`short_term_memory`(namespace);",
            },
            {
                "name": "idx_short_term_category",
                "definition": f"CREATE INDEX idx_short_term_category ON `{bucket}`.`_default`.`short_term_memory`(category_primary);",
            },
            {
                "name": "idx_short_term_importance",
                "definition": f"CREATE INDEX idx_short_term_importance ON `{bucket}`.`_default`.`short_term_memory`(importance_score);",
            },
            {
                "name": "idx_long_term_namespace",
                "definition": f"CREATE INDEX idx_long_term_namespace ON `{bucket}`.`_default`.`long_term_memory`(namespace);",
            },
            {
                "name": "idx_long_term_category",
                "definition": f"CREATE INDEX idx_long_term_category ON `{bucket}`.`_default`.`long_term_memory`(category_primary);",
            },
            {
                "name": "idx_long_term_importance",
                "definition": f"CREATE INDEX idx_long_term_importance ON `{bucket}`.`_default`.`long_term_memory`(importance_score);",
            },
            {
                "name": "idx_long_term_classification",
                "definition": f"CREATE INDEX idx_long_term_classification ON `{bucket}`.`_default`.`long_term_memory`(classification);",
            },
        ]

    def get_data_type_mappings(self) -> dict[str, str]:
        """Get Couchbase-specific data type mappings"""
        return {
            "TEXT": "string",
            "INTEGER": "number",
            "REAL": "number",
            "BOOLEAN": "boolean",
            "TIMESTAMP": "datetime",
            "AUTOINCREMENT": "string (use as document key)",
        }

    def generate_full_schema(self) -> str:
        """Generate complete Couchbase schema documentation"""
        schema_parts = [
            "# Couchbase Schema for Memori v2.0",
            "# Complete database schema with collections, indexes, and search configuration",
            "",
            self.generate_core_schema(),
            "",
            self.generate_indexes(),
            "",
            self.generate_search_setup(),
            "",
            "# Note: Collections should be created via Couchbase Admin UI or REST API.",
            "# Indexes should be created using N1QL queries shown above.",
            "# Full-text search indexes must be created via Couchbase Admin UI or FTS API.",
        ]
        return "\n".join(schema_parts)

