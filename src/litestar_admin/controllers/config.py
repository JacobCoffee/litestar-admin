"""ConfigController for exposing admin configuration to frontend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from litestar import Controller, get
from litestar.status_codes import HTTP_200_OK

from litestar_admin.config import AdminConfig  # noqa: TC001

__all__ = [
    "ConfigController",
    "ConfigResponse",
    "DevCredential",
]


@dataclass
class DevCredential:
    """Development credential for quick login.

    Attributes:
        email: The user's email address.
        password: The user's password.
        role: The user's role name.
    """

    email: str
    password: str
    role: str


@dataclass
class ConfigResponse:
    """Response containing admin panel configuration.

    Only non-sensitive configuration is exposed.

    Attributes:
        title: The admin panel title.
        debug: Whether debug mode is enabled.
        theme: The current theme (dark/light).
        dev_credentials: Development credentials (only when debug=True).
    """

    title: str
    debug: bool
    theme: str
    dev_credentials: list[DevCredential] = field(default_factory=list)


class ConfigController(Controller):
    """Controller for admin panel configuration.

    Provides a public endpoint to retrieve non-sensitive admin configuration,
    including debug mode status and development credentials when enabled.

    Example:
        Access at GET /admin/api/config to retrieve:
        - Admin panel title
        - Debug mode status
        - Theme setting
        - Dev credentials (only in debug mode)
    """

    path = "/api/config"
    tags: ClassVar[list[str]] = ["Configuration"]

    @get(
        "/",
        status_code=HTTP_200_OK,
        summary="Get admin configuration",
        description="Return public admin configuration including debug mode status.",
    )
    async def get_config(
        self,
        admin_config: AdminConfig,
    ) -> ConfigResponse:
        """Get the admin panel configuration.

        Returns non-sensitive configuration values. When debug mode is enabled,
        also includes development credentials for quick login.

        Args:
            admin_config: The admin configuration.

        Returns:
            ConfigResponse containing public configuration values.
        """
        dev_credentials: list[DevCredential] = []

        # Only expose dev credentials when debug mode is enabled
        if admin_config.debug:
            # Standard dev credentials for quick login (intentionally simple for dev mode)
            dev_credentials = [
                DevCredential(email="admin@example.com", password="admin", role="admin"),  # noqa: S106
                DevCredential(email="editor@example.com", password="editor", role="editor"),  # noqa: S106
                DevCredential(email="viewer@example.com", password="viewer", role="viewer"),  # noqa: S106
            ]

        return ConfigResponse(
            title=admin_config.title,
            debug=admin_config.debug,
            theme=admin_config.theme,
            dev_credentials=dev_credentials,
        )
