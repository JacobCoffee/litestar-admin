"""Password reset functionality for admin users.

This module provides secure password reset token generation, validation, and a hook
system for sending reset emails. It uses HMAC-based tokens with configurable expiry.

Example:
    Basic usage with the password reset service::

        from litestar_admin.auth.password_reset import PasswordResetService

        # Create service with default in-memory token storage
        service = PasswordResetService(
            secret_key="your-secret-key",
            token_expiry=3600,  # 1 hour
        )

        # Generate a reset token
        token = await service.generate_token("user@example.com")

        # Validate the token
        email = await service.validate_token(token)
        if email:
            print(f"Valid token for {email}")

    Using a custom email sender::

        async def send_reset_email(email: str, token: str, reset_url: str) -> bool:
            # Send email using your preferred service
            await email_service.send(
                to=email,
                subject="Password Reset",
                body=f"Click here to reset: {reset_url}?token={token}",
            )
            return True

        service = PasswordResetService(
            secret_key="your-secret-key",
            email_sender=send_reset_email,
        )
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

__all__ = [
    "EmailSenderProtocol",
    "PasswordResetService",
    "PasswordResetToken",
    "TokenStorageProtocol",
]

logger = logging.getLogger(__name__)


class EmailSenderProtocol(Protocol):
    """Protocol for email sending implementations.

    Implementations should handle the actual delivery of password reset emails.
    The default implementation is a no-op that logs a warning.
    """

    async def __call__(self, email: str, token: str, reset_url: str) -> bool:
        """Send a password reset email.

        Args:
            email: The recipient's email address.
            token: The password reset token.
            reset_url: The base URL for the password reset page.

        Returns:
            True if the email was sent successfully, False otherwise.
        """
        ...


class TokenStorageProtocol(Protocol):
    """Protocol for token storage implementations.

    Implementations should handle storing and retrieving password reset tokens.
    """

    async def store(self, token: str, email: str, expires_at: float) -> None:
        """Store a password reset token.

        Args:
            token: The token to store.
            email: The email associated with the token.
            expires_at: Unix timestamp when the token expires.
        """
        ...

    async def get(self, token: str) -> tuple[str, float] | None:
        """Retrieve a token's associated email and expiry.

        Args:
            token: The token to look up.

        Returns:
            Tuple of (email, expires_at) or None if not found.
        """
        ...

    async def delete(self, token: str) -> None:
        """Delete a token (after use or expiry).

        Args:
            token: The token to delete.
        """
        ...

    async def delete_for_email(self, email: str) -> None:
        """Delete all tokens for an email (when new token is generated).

        Args:
            email: The email to delete tokens for.
        """
        ...


@dataclass
class PasswordResetToken:
    """Represents a password reset token with metadata.

    Attributes:
        token: The actual token string.
        email: The email address the token was generated for.
        created_at: Unix timestamp when the token was created.
        expires_at: Unix timestamp when the token expires.
    """

    token: str
    email: str
    created_at: float
    expires_at: float

    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return time.time() > self.expires_at


class InMemoryTokenStorage:
    """In-memory implementation of token storage for development/testing.

    Not recommended for production use as tokens will be lost on restart
    and won't work across multiple instances.
    """

    __slots__ = ("_email_to_tokens", "_tokens")

    def __init__(self) -> None:
        """Initialize the in-memory storage."""
        self._tokens: dict[str, tuple[str, float]] = {}
        self._email_to_tokens: dict[str, set[str]] = {}

    async def store(self, token: str, email: str, expires_at: float) -> None:
        """Store a token in memory."""
        self._tokens[token] = (email, expires_at)
        if email not in self._email_to_tokens:
            self._email_to_tokens[email] = set()
        self._email_to_tokens[email].add(token)

    async def get(self, token: str) -> tuple[str, float] | None:
        """Get a token's data from memory."""
        return self._tokens.get(token)

    async def delete(self, token: str) -> None:
        """Delete a token from memory."""
        if token in self._tokens:
            email, _ = self._tokens[token]
            del self._tokens[token]
            if email in self._email_to_tokens:
                self._email_to_tokens[email].discard(token)

    async def delete_for_email(self, email: str) -> None:
        """Delete all tokens for an email."""
        if email in self._email_to_tokens:
            for token in list(self._email_to_tokens[email]):
                if token in self._tokens:
                    del self._tokens[token]
            del self._email_to_tokens[email]


async def _default_email_sender(email: str, token: str, reset_url: str) -> bool:
    """Default email sender that logs a warning and returns False.

    This is a placeholder that should be replaced with a real email sender
    in production.

    Args:
        email: The recipient's email address.
        token: The password reset token.
        reset_url: The base URL for the password reset page.

    Returns:
        Always returns False (email not sent).
    """
    logger.warning(
        "Password reset email not sent - no email sender configured. "
        "Email: %s, Reset URL: %s?token=%s",
        email,
        reset_url,
        token,
    )
    return False


@dataclass
class PasswordResetService:
    """Service for managing password reset tokens.

    Handles token generation, validation, and optionally email sending.
    Uses HMAC-SHA256 for secure token generation with a random component.

    Attributes:
        secret_key: Secret key used for token signing.
        token_expiry: Token expiry time in seconds (default 3600 = 1 hour).
        reset_url: Base URL for the password reset page.
        email_sender: Async callable for sending reset emails.
        token_storage: Storage backend for tokens.

    Example:
        >>> service = PasswordResetService(
        ...     secret_key="your-secret-key",
        ...     reset_url="/admin/reset-password",
        ... )
        >>> token = await service.generate_token("user@example.com")
        >>> email = await service.validate_token(token)
    """

    secret_key: str
    token_expiry: int = 3600
    reset_url: str = "/admin/reset-password"
    email_sender: Callable[[str, str, str], Awaitable[bool]] = field(
        default_factory=lambda: _default_email_sender
    )
    token_storage: TokenStorageProtocol = field(default_factory=InMemoryTokenStorage)

    def __post_init__(self) -> None:
        """Validate configuration."""
        if not self.secret_key:
            msg = "secret_key is required for password reset service"
            raise ValueError(msg)

        min_token_expiry = 60
        if self.token_expiry < min_token_expiry:
            msg = f"token_expiry must be at least {min_token_expiry} seconds"
            raise ValueError(msg)

    def _generate_token_string(self, email: str, timestamp: float) -> str:
        """Generate a secure token string.

        Combines a random component with HMAC signature for security.

        Args:
            email: The email to generate the token for.
            timestamp: The creation timestamp.

        Returns:
            A secure token string.
        """
        # Generate random bytes for uniqueness
        random_bytes = secrets.token_bytes(32)

        # Create message to sign
        message = f"{email}:{timestamp}:{random_bytes.hex()}"

        # Generate HMAC signature
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Combine random component and signature
        return f"{random_bytes.hex()}.{signature}"

    async def generate_token(
        self,
        email: str,
        *,
        send_email: bool = True,
    ) -> PasswordResetToken:
        """Generate a password reset token for an email address.

        Creates a new token, invalidates any existing tokens for the email,
        stores the new token, and optionally sends a reset email.

        Args:
            email: The email address to generate a token for.
            send_email: Whether to send a reset email (default True).

        Returns:
            The generated PasswordResetToken.
        """
        # Normalize email
        email = email.lower().strip()

        # Invalidate existing tokens for this email
        await self.token_storage.delete_for_email(email)

        # Generate token
        created_at = time.time()
        expires_at = created_at + self.token_expiry
        token_str = self._generate_token_string(email, created_at)

        # Store token
        await self.token_storage.store(token_str, email, expires_at)

        # Create token object
        token = PasswordResetToken(
            token=token_str,
            email=email,
            created_at=created_at,
            expires_at=expires_at,
        )

        # Send email if configured
        if send_email:
            try:
                await self.email_sender(email, token_str, self.reset_url)
            except Exception:
                logger.exception("Failed to send password reset email to %s", email)

        return token

    async def validate_token(self, token: str) -> str | None:
        """Validate a password reset token.

        Checks if the token exists and has not expired.

        Args:
            token: The token to validate.

        Returns:
            The email associated with the token if valid, None otherwise.
        """
        result = await self.token_storage.get(token)
        if result is None:
            return None

        email, expires_at = result

        # Check expiry
        if time.time() > expires_at:
            # Clean up expired token
            await self.token_storage.delete(token)
            return None

        return email

    async def consume_token(self, token: str) -> str | None:
        """Validate and consume a password reset token.

        Same as validate_token but also deletes the token after validation,
        ensuring it can only be used once.

        Args:
            token: The token to consume.

        Returns:
            The email associated with the token if valid, None otherwise.
        """
        email = await self.validate_token(token)
        if email:
            await self.token_storage.delete(token)
        return email

    async def invalidate_tokens_for_email(self, email: str) -> None:
        """Invalidate all password reset tokens for an email address.

        Useful when a user successfully logs in or changes their password
        through other means.

        Args:
            email: The email to invalidate tokens for.
        """
        await self.token_storage.delete_for_email(email.lower().strip())
