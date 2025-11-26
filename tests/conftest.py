from __future__ import annotations

from typing import Any, Dict

from memori.utils.pydantic_models import ProcessedLongTermMemory


def create_simple_memory(
    content: str,
    summary: str,
    classification: str,
    importance: str = "medium",
    metadata: Dict[str, Any] | None = None,
) -> ProcessedLongTermMemory:
    """
    Helper used by integration tests to construct a minimal
    ProcessedLongTermMemory instance.

    This intentionally sets only the fields required by the schema and
    leaves the rest to their defaults so tests stay resilient to model
    evolution.
    """
    metadata = metadata or {}

    return ProcessedLongTermMemory(
        content=content,
        summary=summary,
        classification=classification,
        importance=importance,
        # Optional contextual fields – populated from metadata when present
        topic=metadata.get("topic"),
        entities=[],
        keywords=[],
        is_user_context=classification == "context",
        is_preference=classification == "preference",
        is_skill_knowledge=classification == "knowledge",
        is_current_project=bool(metadata.get("project")),
        duplicate_of=None,
        supersedes=[],
        related_memories=[],
        # Technical / required metadata
        session_id="test_session",
        classification_reason="test-fixture",
    )

