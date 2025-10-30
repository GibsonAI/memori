"""
Data validation utilities for Memoriai
"""

import re
from pathlib import Path
from typing import Any

from .exceptions import ValidationError


class DataValidator:
    """Centralized data validation utilities"""

    # Regex patterns
    UUID_PATTERN = re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
    )
    EMAIL_PATTERN = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    API_KEY_PATTERN = re.compile(r"^sk-[a-zA-Z0-9]{48}$")

    @classmethod
    def validate_uuid(cls, value: str, field_name: str = "UUID") -> str:
        """Validate UUID format"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        if not cls.UUID_PATTERN.match(value):
            raise ValidationError(f"{field_name} must be a valid UUID format")

        return value

    @classmethod
    def validate_email(cls, value: str, field_name: str = "email") -> str:
        """Validate email format"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        if not cls.EMAIL_PATTERN.match(value):
            raise ValidationError(f"{field_name} must be a valid email address")

        return value

    @classmethod
    def validate_openai_api_key(cls, value: str, field_name: str = "API key") -> str:
        """Validate OpenAI API key format"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        if not value.startswith("sk-"):
            raise ValidationError(f"{field_name} must start with 'sk-'")

        if len(value) != 51:  # sk- + 48 characters
            raise ValidationError(f"{field_name} must be 51 characters long")

        return value

    @classmethod
    def validate_namespace(cls, value: str, field_name: str = "namespace") -> str:
        """Validate namespace format"""
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return "default"

        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        if len(value) > 64:
            raise ValidationError(f"{field_name} cannot exceed 64 characters")

        # Allow alphanumeric, underscore, hyphen
        if not re.match(r"^[a-zA-Z0-9_-]+$", value):
            raise ValidationError(
                f"{field_name} can only contain letters, numbers, underscores, and hyphens"
            )

        return value.strip()

    @classmethod
    def validate_importance_score(
        cls, value: float, field_name: str = "importance score"
    ) -> float:
        """Validate importance score (0.0 to 1.0)"""
        if not isinstance(value, int | float):
            raise ValidationError(f"{field_name} must be a number")

        if not 0.0 <= value <= 1.0:
            raise ValidationError(f"{field_name} must be between 0.0 and 1.0")

        return float(value)

    @classmethod
    def validate_database_url(cls, value: str, field_name: str = "database URL") -> str:
        """Validate database connection string"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        valid_schemes = ["sqlite://", "sqlite:///", "postgresql://", "mysql://"]
        if not any(value.startswith(scheme) for scheme in valid_schemes):
            raise ValidationError(f"{field_name} must use a supported database scheme")

        return value

    @classmethod
    def validate_file_path(
        cls,
        value: str | Path,
        field_name: str = "file path",
        must_exist: bool = False,
    ) -> Path:
        """Validate file path"""
        if isinstance(value, str):
            path = Path(value)
        elif isinstance(value, Path):
            path = value
        else:
            raise ValidationError(f"{field_name} must be a string or Path object")

        if must_exist and not path.exists():
            raise ValidationError(f"{field_name} does not exist: {path}")

        return path

    @classmethod
    def validate_json_dict(
        cls, value: Any, field_name: str = "JSON data"
    ) -> dict[str, Any]:
        """Validate that value is a JSON-serializable dictionary"""
        if not isinstance(value, dict):
            raise ValidationError(f"{field_name} must be a dictionary")

        try:
            import json

            json.dumps(value)  # Test JSON serialization
        except (TypeError, ValueError) as e:
            raise ValidationError(f"{field_name} must be JSON serializable: {e}") from e

        return value

    @classmethod
    def validate_memory_category(
        cls, value: str, field_name: str = "memory category"
    ) -> str:
        """Validate memory category"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        valid_categories = ["fact", "preference", "skill", "context", "rule"]
        if value not in valid_categories:
            raise ValidationError(
                f"{field_name} must be one of: {', '.join(valid_categories)}"
            )

        return value

    @classmethod
    def validate_retention_type(
        cls, value: str, field_name: str = "retention type"
    ) -> str:
        """Validate retention type"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        valid_types = ["short_term", "long_term", "permanent"]
        if value not in valid_types:
            raise ValidationError(
                f"{field_name} must be one of: {', '.join(valid_types)}"
            )

        return value

    @classmethod
    def validate_entity_type(cls, value: str, field_name: str = "entity type") -> str:
        """Validate entity type"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        valid_types = [
            "person",
            "technology",
            "topic",
            "skill",
            "project",
            "keyword",
            "location",
            "organization",
        ]
        if value not in valid_types:
            raise ValidationError(
                f"{field_name} must be one of: {', '.join(valid_types)}"
            )

        return value

    @classmethod
    def validate_positive_integer(
        cls, value: int, field_name: str = "value", min_value: int = 1
    ) -> int:
        """Validate positive integer"""
        if not isinstance(value, int):
            raise ValidationError(f"{field_name} must be an integer")

        if value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")

        return value

    @classmethod
    def validate_text_length(
        cls,
        value: str,
        field_name: str = "text",
        max_length: int = 1000,
        min_length: int = 1,
    ) -> str:
        """Validate text length"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        if len(value) < min_length:
            raise ValidationError(
                f"{field_name} must be at least {min_length} characters"
            )

        if len(value) > max_length:
            raise ValidationError(f"{field_name} cannot exceed {max_length} characters")

        return value

    @classmethod
    def sanitize_input(cls, value: str, field_name: str = "input") -> str:
        """Sanitize user input for security"""
        if not isinstance(value, str):
            raise ValidationError(f"{field_name} must be a string")

        # Remove potential SQL injection patterns
        dangerous_patterns = [
            r"(\b(DROP|DELETE|UPDATE|INSERT|CREATE|ALTER|EXEC|EXECUTE)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(UNION|SELECT)\b.*\b(FROM|WHERE)\b)",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValidationError(
                    f"{field_name} contains potentially dangerous content"
                )

        # Basic HTML/script tag removal
        value = re.sub(r"<[^>]*>", "", value)

        return value.strip()


class MemoryValidator:
    """Specialized validator for memory-related data"""

    @classmethod
    def validate_memory_data(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Validate complete memory data structure"""
        validated = {}

        # Required fields
        if "memory_id" in data:
            validated["memory_id"] = DataValidator.validate_uuid(
                data["memory_id"], "memory_id"
            )

        if "namespace" in data:
            validated["namespace"] = DataValidator.validate_namespace(data["namespace"])

        if "importance_score" in data:
            validated["importance_score"] = DataValidator.validate_importance_score(
                data["importance_score"]
            )

        if "category_primary" in data:
            validated["category_primary"] = DataValidator.validate_memory_category(
                data["category_primary"]
            )

        if "retention_type" in data:
            validated["retention_type"] = DataValidator.validate_retention_type(
                data["retention_type"]
            )

        # Text fields
        for field in ["summary", "searchable_content"]:
            if field in data:
                validated[field] = DataValidator.validate_text_length(
                    data[field],
                    field,
                    max_length=5000 if field == "searchable_content" else 1000,
                )

        # JSON fields
        for field in ["processed_data", "metadata"]:
            if field in data:
                validated[field] = DataValidator.validate_json_dict(data[field], field)

        return validated

    @classmethod
    def validate_chat_data(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Validate chat data structure"""
        validated = {}

        # Required fields
        required_fields = ["chat_id", "user_input", "ai_output", "model"]
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Required field missing: {field}")

        validated["chat_id"] = DataValidator.validate_uuid(data["chat_id"], "chat_id")
        validated["user_input"] = DataValidator.sanitize_input(
            data["user_input"], "user_input"
        )
        validated["ai_output"] = DataValidator.sanitize_input(
            data["ai_output"], "ai_output"
        )
        validated["model"] = DataValidator.validate_text_length(
            data["model"], "model", max_length=100
        )

        # Optional fields
        if "namespace" in data:
            validated["namespace"] = DataValidator.validate_namespace(data["namespace"])

        if "tokens_used" in data:
            validated["tokens_used"] = DataValidator.validate_positive_integer(
                data["tokens_used"], "tokens_used", min_value=0
            )

        if "metadata" in data:
            validated["metadata"] = DataValidator.validate_json_dict(
                data["metadata"], "metadata"
            )

        return validated
