"""Authentication backends and protocols."""

from __future__ import annotations

from litestar_admin.auth.jwt import JWTAuthBackend, JWTConfig
from litestar_admin.auth.protocols import AdminUser, AuthBackend

__all__ = [
    "AdminUser",
    "AuthBackend",
    "JWTAuthBackend",
    "JWTConfig",
]
