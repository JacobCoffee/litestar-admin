"""OAuth authentication backend using litestar-oauth.

This module provides OAuth2 authentication integration for litestar-admin,
supporting multiple providers (GitHub, Google, Discord) and generic OAuth2/OIDC.

Example:
    Basic setup with GitHub provider:

    >>> from litestar_admin.contrib.oauth import (
    ...     OAuthAuthBackend,
    ...     OAuthConfig,
    ...     OAuthProviderConfig,
    ...     OAuthProviderType,
    ... )
    >>>
    >>> async def load_user(user_id: str | int) -> AdminUser | None:
    ...     return await user_repository.get(user_id)
    >>>
    >>> async def load_user_by_email(email: str) -> AdminUser | None:
    ...     return await user_repository.get_by_email(email)
    >>>
    >>> async def create_user(user_info: OAuthUserInfo) -> AdminUser:
    ...     return await user_repository.create(
    ...         email=user_info.email,
    ...         name=user_info.name,
    ...     )
    >>>
    >>> config = OAuthConfig(
    ...     providers=[
    ...         OAuthProviderConfig(
    ...             name="github",
    ...             client_id="your-client-id",
    ...             client_secret="your-client-secret",
    ...             provider_type=OAuthProviderType.GITHUB,
    ...         ),
    ...     ],
    ...     redirect_base_url="https://example.com",
    ... )
    >>>
    >>> backend = OAuthAuthBackend(
    ...     config=config,
    ...     user_loader=load_user,
    ...     user_loader_by_email=load_user_by_email,
    ...     user_creator=create_user,
    ... )

Note:
    This module requires the `litestar-oauth` package to be installed.
    Install it with: ``pip install 'litestar-admin[oauth]'``
"""

from __future__ import annotations

from litestar_admin.contrib.oauth.backend import (
    OAuthAuthBackend,
    OAuthTokens,
    OAuthUserInfo,
)
from litestar_admin.contrib.oauth.config import (
    OAuthConfig,
    OAuthProviderConfig,
    OAuthProviderType,
)

__all__ = [
    "OAuthAuthBackend",
    "OAuthConfig",
    "OAuthProviderConfig",
    "OAuthProviderType",
    "OAuthTokens",
    "OAuthUserInfo",
]
