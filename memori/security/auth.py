"""
Authentication and Authorization Framework for Memori

This module provides a pluggable authentication/authorization system to prevent
unauthorized access to tenant data.

SECURITY: This is a CRITICAL security component. All Memori instances should
validate that callers are authorized to access the specified user_id, assistant_id,
and session_id.

Usage:
    from memori.security.auth import JWTAuthProvider
    from memori import Memori

    # Create auth provider
    auth = JWTAuthProvider(secret_key=os.getenv("JWT_SECRET"))

    # Create Memori with auth
    memori = Memori(
        database_connect="postgresql://...",
        user_id="user123",
        auth_token=request.headers["Authorization"],
        auth_provider=auth,
    )
"""

from abc import ABC, abstractmethod
from typing import Any

from loguru import logger


class AuthenticationError(Exception):
    """Raised when authentication fails"""

    pass


class AuthorizationError(Exception):
    """Raised when authorization check fails"""

    pass


class AuthProvider(ABC):
    """
    Abstract base class for authentication providers.

    Implement this interface to integrate with your authentication system
    (JWT, OAuth, API keys, etc.)
    """

    @abstractmethod
    def validate_user(self, user_id: str, auth_token: str) -> bool:
        """
        Validate that the auth_token belongs to the specified user_id.

        Args:
            user_id: The user ID being accessed
            auth_token: Authentication token (JWT, API key, etc.)

        Returns:
            True if authentication is valid, False otherwise

        Example:
            # JWT token validation
            payload = jwt.decode(token, secret, algorithms=["HS256"])
            return payload.get("user_id") == user_id
        """
        pass

    @abstractmethod
    def validate_assistant_access(
        self, user_id: str, assistant_id: str, auth_token: str
    ) -> bool:
        """
        Validate that the user has access to the specified assistant.

        Args:
            user_id: The user ID
            assistant_id: The assistant ID being accessed
            auth_token: Authentication token

        Returns:
            True if user has access to this assistant, False otherwise
        """
        pass

    @abstractmethod
    def validate_session_access(
        self, user_id: str, session_id: str, auth_token: str
    ) -> bool:
        """
        Validate that the user has access to the specified session.

        Args:
            user_id: The user ID
            session_id: The session ID being accessed
            auth_token: Authentication token

        Returns:
            True if user has access to this session, False otherwise
        """
        pass

    def extract_user_id(self, auth_token: str) -> str | None:
        """
        Extract user_id from auth token (optional, for convenience).

        Args:
            auth_token: Authentication token

        Returns:
            User ID if extractable, None otherwise
        """
        return None


class NoAuthProvider(AuthProvider):
    """
    No-op auth provider that allows all access.

    WARNING: Only use this for development/testing!
    DO NOT use in production!
    """

    def __init__(self):
        logger.warning(
            "WARNING: NoAuthProvider is being used - ALL ACCESS IS ALLOWED! "
            "This should ONLY be used in development. "
            "Use a proper AuthProvider in production!"
        )

    def validate_user(self, user_id: str, auth_token: str) -> bool:
        return True

    def validate_assistant_access(
        self, user_id: str, assistant_id: str, auth_token: str
    ) -> bool:
        return True

    def validate_session_access(
        self, user_id: str, session_id: str, auth_token: str
    ) -> bool:
        return True


class JWTAuthProvider(AuthProvider):
    """
    JWT-based authentication provider.

    Validates JWTs and checks permissions encoded in token claims.

    Example token structure:
        {
            "user_id": "user123",
            "assistants": ["assistant1", "assistant2"],
            "exp": 1234567890
        }
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize JWT auth provider.

        Args:
            secret_key: Secret key for JWT validation
            algorithm: JWT algorithm (default: HS256)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm

        try:
            import jose.jwt

            self.jwt = jose.jwt
        except ImportError:
            raise ImportError(
                "python-jose is required for JWT auth. "
                "Install with: pip install python-jose[cryptography]"
            )

    def _decode_token(self, auth_token: str) -> dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            # Remove "Bearer " prefix if present
            if auth_token.startswith("Bearer "):
                auth_token = auth_token[7:]

            payload = self.jwt.decode(
                auth_token, self.secret_key, algorithms=[self.algorithm]
            )
            return payload
        except self.jwt.JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise AuthenticationError(f"Invalid authentication token: {e}")
        except Exception as e:
            logger.error(f"Token decoding error: {e}")
            raise AuthenticationError(f"Authentication error: {e}")

    def validate_user(self, user_id: str, auth_token: str) -> bool:
        """Validate JWT token matches user_id"""
        try:
            payload = self._decode_token(auth_token)
            token_user_id = payload.get("user_id") or payload.get("sub")

            if token_user_id != user_id:
                logger.warning(
                    f"User ID mismatch: token={token_user_id}, requested={user_id}"
                )
                return False

            return True
        except AuthenticationError:
            return False

    def validate_assistant_access(
        self, user_id: str, assistant_id: str, auth_token: str
    ) -> bool:
        """Validate user has access to assistant"""
        try:
            payload = self._decode_token(auth_token)

            # First validate user
            if not self.validate_user(user_id, auth_token):
                return False

            # Check assistant permissions
            allowed_assistants = payload.get("assistants", [])

            # If no assistants specified in token, allow all (backward compat)
            if not allowed_assistants:
                return True

            if assistant_id not in allowed_assistants:
                logger.warning(
                    f"User {user_id} not authorized for assistant {assistant_id}"
                )
                return False

            return True
        except AuthenticationError:
            return False

    def validate_session_access(
        self, user_id: str, session_id: str, auth_token: str
    ) -> bool:
        """Validate user has access to session"""
        try:
            # First validate user
            if not self.validate_user(user_id, auth_token):
                return False

            # For sessions, we trust that if user is valid, they own their sessions
            # More complex session validation can be added here if needed
            return True
        except AuthenticationError:
            return False

    def extract_user_id(self, auth_token: str) -> str | None:
        """Extract user_id from JWT"""
        try:
            payload = self._decode_token(auth_token)
            return payload.get("user_id") or payload.get("sub")
        except AuthenticationError:
            return None


class APIKeyAuthProvider(AuthProvider):
    """
    API key-based authentication provider.

    Validates API keys against a database or cache and checks permissions.

    Example:
        auth = APIKeyAuthProvider(
            api_key_validator=lambda key: validate_key_in_database(key)
        )
    """

    def __init__(self, api_key_validator):
        """
        Initialize API key auth provider.

        Args:
            api_key_validator: Callable that takes an API key and returns
                              user info dict or None if invalid
                              Example: {"user_id": "user123", "assistants": [...]}
        """
        self.api_key_validator = api_key_validator

    def _get_user_info(self, auth_token: str) -> dict[str, Any] | None:
        """Get user info from API key"""
        try:
            # Remove "Bearer " or "ApiKey " prefix if present
            if auth_token.startswith(("Bearer ", "ApiKey ")):
                auth_token = auth_token.split(" ", 1)[1]

            user_info = self.api_key_validator(auth_token)
            return user_info
        except Exception as e:
            logger.error(f"API key validation error: {e}")
            return None

    def validate_user(self, user_id: str, auth_token: str) -> bool:
        """Validate API key matches user_id"""
        user_info = self._get_user_info(auth_token)
        if not user_info:
            return False

        return user_info.get("user_id") == user_id

    def validate_assistant_access(
        self, user_id: str, assistant_id: str, auth_token: str
    ) -> bool:
        """Validate user has access to assistant"""
        user_info = self._get_user_info(auth_token)
        if not user_info or user_info.get("user_id") != user_id:
            return False

        allowed_assistants = user_info.get("assistants", [])
        if not allowed_assistants:
            return True  # Allow all if none specified

        return assistant_id in allowed_assistants

    def validate_session_access(
        self, user_id: str, session_id: str, auth_token: str
    ) -> bool:
        """Validate user has access to session"""
        user_info = self._get_user_info(auth_token)
        if not user_info:
            return False

        return user_info.get("user_id") == user_id

    def extract_user_id(self, auth_token: str) -> str | None:
        """Extract user_id from API key"""
        user_info = self._get_user_info(auth_token)
        return user_info.get("user_id") if user_info else None


def create_auth_provider(provider_type: str = "jwt", **kwargs) -> AuthProvider:
    """
    Factory function to create auth providers.

    Args:
        provider_type: Type of auth provider ("jwt", "api_key", "none")
        **kwargs: Provider-specific configuration

    Returns:
        AuthProvider instance

    Example:
        # JWT provider
        auth = create_auth_provider("jwt", secret_key="secret")

        # API key provider
        auth = create_auth_provider(
            "api_key",
            api_key_validator=my_validator
        )

        # Development only - no auth
        auth = create_auth_provider("none")
    """
    providers = {
        "jwt": JWTAuthProvider,
        "api_key": APIKeyAuthProvider,
        "none": NoAuthProvider,
    }

    provider_class = providers.get(provider_type)
    if not provider_class:
        raise ValueError(
            f"Unknown auth provider type: {provider_type}. "
            f"Available: {list(providers.keys())}"
        )

    return provider_class(**kwargs)
