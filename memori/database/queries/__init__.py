"""
Database queries module for centralized SQL management
"""

from .base_queries import BaseQueries
from .chat_queries import ChatQueries

# from .entity_queries import EntityQueries  # REMOVED: Entity/relationship tables removed from simplified schema
from .memory_queries import MemoryQueries

__all__ = [
    "BaseQueries",
    "MemoryQueries",
    "ChatQueries",
    # "EntityQueries",  # REMOVED: Entity/relationship tables removed from simplified schema
]
