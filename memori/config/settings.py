"""
Pydantic-based configuration settings for Memoriai
"""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, validator


class LogLevel(str, Enum):
    """Logging levels"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DatabaseType(str, Enum):
    """Supported database types"""

    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"


class RetentionPolicy(str, Enum):
    """Memory retention policies"""

    DAYS_7 = "7_days"
    DAYS_30 = "30_days"
    DAYS_90 = "90_days"
    PERMANENT = "permanent"


class DatabaseSettings(BaseModel):
    """Database configuration settings"""

    connection_string: str = Field(
        default="sqlite:///memori.db", description="Database connection string"
    )
    database_type: DatabaseType = Field(
        default=DatabaseType.SQLITE, description="Type of database backend"
    )
    template: str = Field(default="basic", description="Database template to use")

    # Connection pool configuration
    pool_size: int = Field(default=5, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(
        default=10, ge=0, le=100, description="Max overflow connections"
    )
    pool_timeout: int = Field(
        default=30, ge=1, le=300, description="Pool timeout in seconds"
    )
    pool_recycle: int = Field(
        default=3600, ge=300, le=7200, description="Recycle connections after seconds"
    )
    pool_pre_ping: bool = Field(default=True, description="Test connections before use")

    echo_sql: bool = Field(default=False, description="Echo SQL statements to logs")
    migration_auto: bool = Field(
        default=True, description="Automatically run migrations"
    )
    backup_enabled: bool = Field(default=False, description="Enable automatic backups")
    backup_interval_hours: int = Field(
        default=24, ge=1, description="Backup interval in hours"
    )

    @validator("connection_string")
    def validate_connection_string(cls, v):
        """Validate database connection string"""
        if not v:
            raise ValueError("Connection string cannot be empty")

        # Basic validation for supported protocols
        valid_prefixes = [
            "sqlite://",
            "sqlite:///",
            "postgresql://",
            "mysql://",
            "mongodb://",
        ]
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(f"Unsupported database type in connection string: {v}")

        return v


class AgentSettings(BaseModel):
    """AI agent configuration settings"""

    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key for memory processing"
    )
    default_model: str = Field(
        default="gpt-4o", description="Default model for memory processing"
    )
    fallback_model: str = Field(
        default="gpt-3.5-turbo", description="Fallback model if default fails"
    )
    max_tokens: int = Field(
        default=2000, ge=100, le=8000, description="Maximum tokens per API call"
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="Model temperature for memory processing",
    )
    timeout_seconds: int = Field(
        default=30, ge=5, le=300, description="API timeout in seconds"
    )
    retry_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of retry attempts for failed API calls",
    )
    conscious_ingest: bool = Field(
        default=True, description="Enable intelligent memory filtering"
    )

    @validator("openai_api_key")
    def validate_api_key(cls, v):
        """Validate OpenAI API key format"""
        if v and not v.startswith("sk-"):
            raise ValueError("OpenAI API key must start with 'sk-'")
        return v


class LoggingSettings(BaseModel):
    """Logging configuration settings"""

    level: LogLevel = Field(default=LogLevel.INFO, description="Logging level")
    format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Log message format",
    )
    log_to_file: bool = Field(default=False, description="Enable logging to file")
    log_file_path: str = Field(default="logs/memori.log", description="Log file path")
    log_rotation: str = Field(default="10 MB", description="Log rotation size")
    log_retention: str = Field(default="30 days", description="Log retention period")
    log_compression: str = Field(default="gz", description="Log compression format")
    structured_logging: bool = Field(
        default=False, description="Enable structured JSON logging"
    )


class MemorySettings(BaseModel):
    """Memory processing configuration"""

    namespace: str = Field(
        default="default", description="Default namespace for memory isolation"
    )
    shared_memory: bool = Field(
        default=False, description="Enable shared memory across agents"
    )
    retention_policy: RetentionPolicy = Field(
        default=RetentionPolicy.DAYS_30, description="Default memory retention policy"
    )
    auto_cleanup: bool = Field(
        default=True, description="Enable automatic cleanup of expired memories"
    )
    cleanup_interval_hours: int = Field(
        default=24, ge=1, description="Cleanup interval in hours"
    )
    importance_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum importance score for memory retention",
    )
    max_short_term_memories: int = Field(
        default=1000, ge=10, description="Maximum number of short-term memories"
    )
    max_long_term_memories: int = Field(
        default=10000, ge=100, description="Maximum number of long-term memories"
    )
    context_injection: bool = Field(
        default=True, description="Enable context injection in conversations"
    )
    context_limit: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of context memories to inject",
    )


class IntegrationSettings(BaseModel):
    """Integration configuration"""

    litellm_enabled: bool = Field(
        default=True, description="Enable LiteLLM integration"
    )
    openai_wrapper_enabled: bool = Field(
        default=False, description="Enable OpenAI wrapper integration"
    )
    anthropic_wrapper_enabled: bool = Field(
        default=False, description="Enable Anthropic wrapper integration"
    )
    auto_enable_on_import: bool = Field(
        default=False, description="Automatically enable integrations on import"
    )
    callback_timeout: int = Field(
        default=5, ge=1, le=30, description="Callback timeout in seconds"
    )


class MemoriSettings(BaseModel):
    """Main Memoriai configuration"""

    version: str = Field(default="1.0.0", description="Configuration version")
    debug: bool = Field(default=False, description="Enable debug mode")
    verbose: bool = Field(
        default=False, description="Enable verbose logging (loguru only)"
    )

    # Component settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    agents: AgentSettings = Field(default_factory=AgentSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    integrations: IntegrationSettings = Field(default_factory=IntegrationSettings)

    # Custom settings
    custom_settings: dict[str, Any] = Field(
        default_factory=dict, description="Custom user-defined settings"
    )

    class Config:
        """Pydantic configuration"""

        env_prefix = "MEMORI_"
        env_nested_delimiter = "__"
        case_sensitive = False

    @classmethod
    def from_env(cls) -> "MemoriSettings":
        """Create settings from environment variables"""
        return cls()

    @classmethod
    def from_file(cls, config_path: str | Path) -> "MemoriSettings":
        """Load settings from JSON/YAML file"""
        import json
        from pathlib import Path

        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path) as f:
            if config_path.suffix.lower() == ".json":
                data = json.load(f)
            elif config_path.suffix.lower() in [".yml", ".yaml"]:
                try:
                    import yaml

                    data = yaml.safe_load(f)
                except ImportError:
                    raise ImportError("PyYAML is required for YAML configuration files")
            else:
                raise ValueError(
                    f"Unsupported configuration file format: {config_path.suffix}"
                )

        return cls(**data)

    def to_file(self, config_path: str | Path, format: str = "json") -> None:
        """Save settings to file"""
        import json
        from pathlib import Path

        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = self.dict()

        with open(config_path, "w") as f:
            if format.lower() == "json":
                json.dump(data, f, indent=2, default=str)
            elif format.lower() in ["yml", "yaml"]:
                try:
                    import yaml

                    yaml.safe_dump(data, f, default_flow_style=False)
                except ImportError:
                    raise ImportError("PyYAML is required for YAML configuration files")
            else:
                raise ValueError(f"Unsupported format: {format}")

    def get_database_url(self) -> str:
        """Get the database connection URL"""
        return self.database.connection_string

    def is_production(self) -> bool:
        """Check if running in production mode"""
        return not self.debug and self.logging.level in [
            LogLevel.INFO,
            LogLevel.WARNING,
            LogLevel.ERROR,
        ]
