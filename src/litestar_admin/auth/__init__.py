"""Authentication backends, models, and protocols.

This module provides authentication infrastructure for the admin panel including:
- AdminUser model with secure password hashing
- Password hashing utilities (Argon2/bcrypt)
- Password reset functionality with token management
- Authentication protocols for custom implementations
- JWT authentication backend
"""

from __future__ import annotations

from litestar_admin.auth.jwt import JWTAuthBackend, JWTConfig
from litestar_admin.auth.models import AdminUser, AdminUserBase
from litestar_admin.auth.password import (
    PasswordHasher,
    hash_password,
    needs_rehash,
    verify_password,
)
from litestar_admin.auth.password_reset import (
    PasswordResetService,
    PasswordResetToken,
)
from litestar_admin.auth.protocols import AdminUserProtocol, AuthBackend

__all__ = [
    # Models
    "AdminUser",
    "AdminUserBase",
    # Protocols
    "AdminUserProtocol",
    "AuthBackend",
    # JWT
    "JWTAuthBackend",
    "JWTConfig",
    # Password utilities
    "PasswordHasher",
    "hash_password",
    "needs_rehash",
    "verify_password",
    # Password reset
    "PasswordResetService",
    "PasswordResetToken",
]
