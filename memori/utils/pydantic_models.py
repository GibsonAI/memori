"""
Pydantic Models for Structured Memory Processing
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class MemoryCategoryType(str, Enum):
    """Primary memory categories"""

    fact = "fact"
    preference = "preference"
    skill = "skill"
    context = "context"
    rule = "rule"


class MemoryClassification(str, Enum):
    """Enhanced memory classification for long-term storage"""

    ESSENTIAL = "essential"  # Core facts, preferences, skills
    CONTEXTUAL = "contextual"  # Project context, ongoing work
    CONVERSATIONAL = "conversational"  # Regular chat, questions, discussions
    REFERENCE = "reference"  # Code examples, technical references
    PERSONAL = "personal"  # User details, relationships, life events
    CONSCIOUS_INFO = "conscious-info"  # Direct promotion to short-term context


class MemoryImportanceLevel(str, Enum):
    """Memory importance levels"""

    CRITICAL = "critical"  # Must never be lost
    HIGH = "high"  # Very important for context
    MEDIUM = "medium"  # Useful to remember
    LOW = "low"  # Nice to have context


class RetentionType(str, Enum):
    """Memory retention types"""

    short_term = "short_term"
    long_term = "long_term"
    permanent = "permanent"


class EntityType(str, Enum):
    """Types of entities that can be extracted"""

    person = "person"
    technology = "technology"
    topic = "topic"
    skill = "skill"
    project = "project"
    keyword = "keyword"


# Define constrained types using Annotated
ConfidenceScore = Annotated[float, Field(ge=0.0, le=1.0)]
ImportanceScore = Annotated[float, Field(ge=0.0, le=1.0)]
RelevanceScore = Annotated[float, Field(ge=0.0, le=1.0)]
PriorityLevel = Annotated[int, Field(ge=1, le=10)]


class MemoryCategory(BaseModel):
    """Memory categorization with confidence and reasoning"""

    primary_category: MemoryCategoryType
    confidence_score: ConfidenceScore = Field(
        description="Confidence in categorization (0.0-1.0)"
    )
    reasoning: str = Field(
        description="Brief explanation for why this category was chosen"
    )


class ExtractedEntity(BaseModel):
    """Individual extracted entity with metadata"""

    entity_type: EntityType
    value: str = Field(description="The actual entity value")
    relevance_score: RelevanceScore = Field(
        description="How relevant this entity is to the memory"
    )
    context: str | None = Field(
        default=None, description="Additional context about this entity"
    )


class ExtractedEntities(BaseModel):
    """All entities extracted from a conversation"""

    people: list[str] = Field(
        default_factory=list, description="Names of people mentioned"
    )
    technologies: list[str] = Field(
        default_factory=list, description="Technologies, tools, libraries mentioned"
    )
    topics: list[str] = Field(
        default_factory=list, description="Main topics or subjects discussed"
    )
    skills: list[str] = Field(
        default_factory=list, description="Skills, abilities, or competencies mentioned"
    )
    projects: list[str] = Field(
        default_factory=list,
        description="Projects, repositories, or initiatives mentioned",
    )
    keywords: list[str] = Field(
        default_factory=list, description="Important keywords for search"
    )

    # Structured entities with metadata
    structured_entities: list[ExtractedEntity] = Field(
        default_factory=list, description="Detailed entity extraction"
    )


class MemoryImportance(BaseModel):
    """Importance scoring and retention decisions"""

    importance_score: ImportanceScore = Field(
        description="Overall importance score (0.0-1.0)"
    )
    retention_type: RetentionType = Field(description="Recommended retention type")
    reasoning: str = Field(
        description="Explanation for the importance level and retention decision"
    )

    # Additional scoring factors
    novelty_score: RelevanceScore = Field(
        default=0.5, description="How novel/new this information is"
    )
    relevance_score: RelevanceScore = Field(
        default=0.5, description="How relevant to user's interests"
    )
    actionability_score: RelevanceScore = Field(
        default=0.5, description="How actionable this information is"
    )


class MemorySearchQuery(BaseModel):
    """Structured query for memory search"""

    # Query components
    query_text: str = Field(description="Original query text")
    intent: str = Field(description="Interpreted intent of the query")

    # Search parameters
    entity_filters: list[str] = Field(
        default_factory=list, description="Specific entities to search for"
    )
    category_filters: list[MemoryCategoryType] = Field(
        default_factory=list, description="Memory categories to include"
    )
    time_range: str | None = Field(
        default=None, description="Time range for search (e.g., 'last_week')"
    )
    min_importance: ImportanceScore = Field(
        default=0.0, description="Minimum importance score"
    )

    # Search strategy
    search_strategy: list[str] = Field(
        default_factory=list, description="Recommended search strategies"
    )
    expected_result_types: list[str] = Field(
        default_factory=list, description="Expected types of results"
    )


class MemoryRelationship(BaseModel):
    """Relationship between memories"""

    source_memory_id: str
    target_memory_id: str
    relationship_type: Literal[
        "builds_on", "contradicts", "supports", "related_to", "prerequisite"
    ]
    strength: RelevanceScore = Field(description="Strength of the relationship")
    reasoning: str = Field(description="Why these memories are related")


class UserRule(BaseModel):
    """User preferences and rules"""

    rule_text: str = Field(description="The rule or preference in natural language")
    rule_type: Literal["preference", "instruction", "constraint", "goal"]
    priority: PriorityLevel = Field(default=5, description="Priority level (1-10)")
    context: str | None = Field(default=None, description="When this rule applies")
    active: bool = Field(
        default=True, description="Whether this rule is currently active"
    )


class ConversationContext(BaseModel):
    """Context information for memory processing"""

    model_config = {"protected_namespaces": ()}

    user_id: str | None = Field(default=None)
    session_id: str  # Session/conversation grouping
    chat_id: str  # Specific chat message ID
    model_used: str

    # User context
    user_preferences: list[str] = Field(default_factory=list)
    current_projects: list[str] = Field(default_factory=list)
    relevant_skills: list[str] = Field(default_factory=list)

    # Conversation metadata
    conversation_length: int = Field(
        default=1, description="Number of exchanges in this conversation"
    )
    topic_thread: str | None = Field(
        default=None, description="Main topic thread being discussed"
    )

    # Memory context
    recent_memories: list[str] = Field(
        default_factory=list, description="IDs of recently accessed memories"
    )
    applied_rules: list[str] = Field(
        default_factory=list, description="Rules that were applied"
    )


class ProcessedMemory(BaseModel):
    """Legacy processed memory model for backward compatibility"""

    content: str = Field(description="The actual memory content")
    summary: str = Field(description="Concise summary for search")
    searchable_content: str = Field(description="Optimized content for search")
    should_store: bool = Field(description="Whether this memory should be stored")
    storage_reasoning: str = Field(
        description="Why this memory should or shouldn't be stored"
    )
    timestamp: datetime = Field(default_factory=datetime.now)
    processing_metadata: dict[str, str] | None = Field(default=None)


class ProcessedLongTermMemory(BaseModel):
    """Enhanced long-term memory with classification and conscious context"""

    # Core Memory Content
    content: str = Field(description="The actual memory content")
    summary: str = Field(description="Concise summary for search")
    classification: MemoryClassification = Field(description="Type classification")
    importance: MemoryImportanceLevel = Field(description="Importance level")

    # Context Information
    topic: str | None = Field(default=None, description="Main topic/subject")
    entities: list[str] = Field(
        default_factory=list, description="People, places, technologies mentioned"
    )
    keywords: list[str] = Field(
        default_factory=list, description="Key terms for search"
    )

    # Conscious Context Flags
    is_user_context: bool = Field(
        default=False, description="Contains user personal info"
    )
    is_preference: bool = Field(default=False, description="User preference/opinion")
    is_skill_knowledge: bool = Field(
        default=False, description="User's abilities/expertise"
    )
    is_current_project: bool = Field(default=False, description="Current work context")

    # Memory Management
    duplicate_of: str | None = Field(
        default=None, description="Links to original if duplicate"
    )
    supersedes: list[str] = Field(
        default_factory=list, description="Previous memories this replaces"
    )
    related_memories: list[str] = Field(
        default_factory=list, description="Connected memory IDs"
    )

    # Technical Metadata
    session_id: str = Field(description="Source session/conversation")
    confidence_score: float = Field(
        default=0.8, description="AI confidence in extraction"
    )
    extraction_timestamp: datetime = Field(default_factory=datetime.now)
    last_accessed: datetime | None = Field(default=None)
    access_count: int = Field(default=0)

    # Classification Reasoning
    classification_reason: str = Field(description="Why this classification was chosen")
    promotion_eligible: bool = Field(
        default=False, description="Should be promoted to short-term"
    )

    @property
    def importance_score(self) -> float:
        """Convert importance level to numeric score"""
        return {"critical": 0.9, "high": 0.7, "medium": 0.5, "low": 0.3}.get(
            self.importance, 0.5
        )


class UserContextProfile(BaseModel):
    """Permanent user context for conscious ingestion"""

    # Core Identity
    name: str | None = None
    pronouns: str | None = None
    location: str | None = None
    timezone: str | None = None

    # Professional Context
    job_title: str | None = None
    company: str | None = None
    industry: str | None = None
    experience_level: str | None = None
    specializations: list[str] = Field(default_factory=list)

    # Technical Stack
    primary_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    environment: str | None = None

    # Behavioral Preferences
    communication_style: str | None = None
    technical_depth: str | None = None
    response_preference: str | None = None

    # Current Context
    active_projects: list[str] = Field(default_factory=list)
    learning_goals: list[str] = Field(default_factory=list)
    domain_expertise: list[str] = Field(default_factory=list)

    # Values & Constraints
    code_standards: list[str] = Field(default_factory=list)
    time_constraints: str | None = None
    technology_preferences: list[str] = Field(default_factory=list)

    # Metadata
    last_updated: datetime = Field(default_factory=datetime.now)
    version: int = 1


class MemoryStats(BaseModel):
    """Statistics about stored memories"""

    total_memories: int
    memories_by_category: dict[str, int]
    memories_by_retention: dict[str, int]
    average_importance: float
    total_entities: int
    most_common_entities: list[tuple[str, int]]
    storage_size_mb: float
    oldest_memory_date: datetime | None
    newest_memory_date: datetime | None
