"""Password hashing utilities for admin authentication.

This module provides secure password hashing using Argon2 (preferred) with
automatic fallback to bcrypt if Argon2 is not available.

Example:
    Hash and verify passwords::

        from litestar_admin.auth.password import hash_password, verify_password

        # Hash a password
        hashed = hash_password("my_secure_password")

        # Verify a password
        if verify_password("my_secure_password", hashed):
            print("Password is correct!")

        # Check if rehashing is needed (e.g., after algorithm upgrade)
        if needs_rehash(hashed):
            new_hash = hash_password("my_secure_password")
"""

from __future__ import annotations

import logging
from typing import Protocol

__all__ = [
    "PasswordHasher",
    "hash_password",
    "needs_rehash",
    "verify_password",
]

logger = logging.getLogger(__name__)


class PasswordHasherProtocol(Protocol):
    """Protocol for password hashing implementations."""

    def hash(self, password: str) -> str:
        """Hash a password.

        Args:
            password: The plain text password to hash.

        Returns:
            The hashed password string.
        """
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: The plain text password to verify.
            password_hash: The hash to verify against.

        Returns:
            True if the password matches, False otherwise.
        """
        ...

    def needs_rehash(self, password_hash: str) -> bool:
        """Check if a password hash needs to be rehashed.

        Args:
            password_hash: The hash to check.

        Returns:
            True if the hash should be regenerated, False otherwise.
        """
        ...


class PasswordHasher:
    """Password hasher using Argon2 with bcrypt fallback.

    This class provides a unified interface for password hashing using the
    passlib library. It prefers Argon2 (the winner of the Password Hashing
    Competition) but falls back to bcrypt if Argon2 is not available.

    The hasher automatically handles:
    - Secure hashing with appropriate work factors
    - Hash verification
    - Hash migration (detecting when passwords need rehashing)

    Attributes:
        _context: The passlib CryptContext instance.
        _available: Whether passlib is available.

    Example:
        Using the hasher directly::

            hasher = PasswordHasher()
            hashed = hasher.hash("password123")
            assert hasher.verify("password123", hashed)
    """

    _context: object | None = None
    _available: bool = False
    _initialized: bool = False

    def __init__(self) -> None:
        """Initialize the password hasher.

        Attempts to configure passlib with Argon2, falling back to bcrypt
        if Argon2 is not available, and finally to a deprecation-warned
        SHA-256 if neither is available.
        """
        if PasswordHasher._initialized:
            return

        PasswordHasher._initialized = True

        try:
            from passlib.context import CryptContext

            # Try Argon2 first (preferred)
            try:
                PasswordHasher._context = CryptContext(
                    schemes=["argon2", "bcrypt"],
                    default="argon2",
                    argon2__rounds=4,  # Time cost
                    argon2__memory_cost=65536,  # 64MB memory
                    argon2__parallelism=2,  # Parallelism factor
                    bcrypt__rounds=12,  # Fallback bcrypt rounds
                    deprecated=["bcrypt"],  # Mark bcrypt as deprecated for rehashing
                )
                PasswordHasher._available = True
                logger.debug("Password hasher initialized with Argon2")
            except ValueError:
                # Argon2 not available, try bcrypt only
                try:
                    PasswordHasher._context = CryptContext(
                        schemes=["bcrypt"],
                        default="bcrypt",
                        bcrypt__rounds=12,
                    )
                    PasswordHasher._available = True
                    logger.debug("Password hasher initialized with bcrypt (Argon2 not available)")
                except ValueError:
                    logger.warning(
                        "Neither Argon2 nor bcrypt available. "
                        "Install 'passlib[argon2]' for secure password hashing."
                    )
                    PasswordHasher._available = False
        except ImportError:
            logger.warning("passlib not installed. Install 'litestar-admin[auth]' for password hashing support.")
            PasswordHasher._available = False

    def hash(self, password: str) -> str:
        """Hash a password using the configured algorithm.

        Args:
            password: The plain text password to hash.

        Returns:
            The hashed password string.

        Raises:
            RuntimeError: If no password hashing backend is available.

        Example:
            >>> hasher = PasswordHasher()
            >>> hashed = hasher.hash("secure_password")
            >>> hashed.startswith("$argon2")  # If Argon2 is available
            True
        """
        if not PasswordHasher._available or PasswordHasher._context is None:
            msg = (
                "No password hashing backend available. "
                "Install 'litestar-admin[auth]' or 'passlib[argon2]'."
            )
            raise RuntimeError(msg)
        return PasswordHasher._context.hash(password)  # type: ignore[union-attr]

    def verify(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: The plain text password to verify.
            password_hash: The hash to verify against.

        Returns:
            True if the password matches the hash, False otherwise.

        Raises:
            RuntimeError: If no password hashing backend is available.

        Example:
            >>> hasher = PasswordHasher()
            >>> hashed = hasher.hash("my_password")
            >>> hasher.verify("my_password", hashed)
            True
            >>> hasher.verify("wrong_password", hashed)
            False
        """
        if not PasswordHasher._available or PasswordHasher._context is None:
            msg = (
                "No password hashing backend available. "
                "Install 'litestar-admin[auth]' or 'passlib[argon2]'."
            )
            raise RuntimeError(msg)
        return PasswordHasher._context.verify(password, password_hash)  # type: ignore[union-attr]

    def needs_rehash(self, password_hash: str) -> bool:
        """Check if a password hash needs to be rehashed.

        This is useful for migrating passwords when:
        - The hashing algorithm has been upgraded (e.g., bcrypt to Argon2)
        - The work factor parameters have been increased
        - The hash format is deprecated

        Args:
            password_hash: The hash to check.

        Returns:
            True if the hash should be regenerated, False otherwise.

        Raises:
            RuntimeError: If no password hashing backend is available.

        Example:
            >>> hasher = PasswordHasher()
            >>> old_bcrypt_hash = "$2b$..."  # Old bcrypt hash
            >>> if hasher.needs_rehash(old_bcrypt_hash):
            ...     # Verify and rehash on next login
            ...     pass
        """
        if not PasswordHasher._available or PasswordHasher._context is None:
            msg = (
                "No password hashing backend available. "
                "Install 'litestar-admin[auth]' or 'passlib[argon2]'."
            )
            raise RuntimeError(msg)
        return PasswordHasher._context.needs_update(password_hash)  # type: ignore[union-attr]

    @classmethod
    def is_available(cls) -> bool:
        """Check if password hashing is available.

        Returns:
            True if a password hashing backend is configured.
        """
        if not cls._initialized:
            cls()  # Initialize on first check
        return cls._available


# Module-level singleton instance
_hasher: PasswordHasher | None = None


def _get_hasher() -> PasswordHasher:
    """Get or create the singleton hasher instance."""
    global _hasher  # noqa: PLW0603
    if _hasher is None:
        _hasher = PasswordHasher()
    return _hasher


def hash_password(password: str) -> str:
    """Hash a password using Argon2 (or bcrypt fallback).

    This is a convenience function that uses the module-level password hasher.

    Args:
        password: The plain text password to hash.

    Returns:
        The hashed password string.

    Raises:
        RuntimeError: If no password hashing backend is available.

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> hashed.startswith("$argon2")
        True
    """
    return _get_hasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash.

    This is a convenience function that uses the module-level password hasher.

    Args:
        password: The plain text password to verify.
        password_hash: The hash to verify against.

    Returns:
        True if the password matches the hash, False otherwise.

    Raises:
        RuntimeError: If no password hashing backend is available.

    Example:
        >>> hashed = hash_password("my_password")
        >>> verify_password("my_password", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    return _get_hasher().verify(password, password_hash)


def needs_rehash(password_hash: str) -> bool:
    """Check if a password hash needs to be rehashed.

    This is a convenience function that uses the module-level password hasher.
    Use this to detect when passwords should be re-hashed during login,
    such as when migrating from bcrypt to Argon2 or increasing work factors.

    Args:
        password_hash: The hash to check.

    Returns:
        True if the hash should be regenerated, False otherwise.

    Raises:
        RuntimeError: If no password hashing backend is available.

    Example:
        >>> hashed = hash_password("password")
        >>> needs_rehash(hashed)
        False
    """
    return _get_hasher().needs_rehash(password_hash)
