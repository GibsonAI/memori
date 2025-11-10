"""Database connection pool configuration"""


class PoolConfig:
    """Centralized database pool configuration"""

    # Default pool settings
    DEFAULT_POOL_SIZE = 5
    DEFAULT_MAX_OVERFLOW = 10
    DEFAULT_POOL_TIMEOUT = 30  # seconds
    DEFAULT_POOL_RECYCLE = 3600  # seconds (1 hour)
    DEFAULT_POOL_PRE_PING = True

    # Per-environment overrides
    DEVELOPMENT = {
        "pool_size": 2,
        "max_overflow": 5,
        "pool_pre_ping": True,
    }

    TESTING = {
        "pool_size": 1,
        "max_overflow": 2,
        "pool_timeout": 5,
    }

    PRODUCTION = {
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    @classmethod
    def get_config(cls, environment: str = "development") -> dict:
        """Get configuration for environment"""
        base = {
            "pool_size": cls.DEFAULT_POOL_SIZE,
            "max_overflow": cls.DEFAULT_MAX_OVERFLOW,
            "pool_timeout": cls.DEFAULT_POOL_TIMEOUT,
            "pool_recycle": cls.DEFAULT_POOL_RECYCLE,
            "pool_pre_ping": cls.DEFAULT_POOL_PRE_PING,
        }

        env_overrides = getattr(cls, environment.upper(), {})
        base.update(env_overrides)
        return base


# Create a module-level instance for convenience
pool_config = PoolConfig()
