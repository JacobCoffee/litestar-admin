"""Audit logging middleware for automatic request tracking.

This module provides middleware for automatically logging admin panel
requests based on configurable rules.

Example:
    Configure middleware with the admin plugin::

        from litestar_admin.audit import AuditMiddleware, InMemoryAuditLogger

        logger = InMemoryAuditLogger()
        app = Litestar(
            plugins=[AdminPlugin(config=AdminConfig(extra={"audit_logger": logger}))],
            middleware=[AuditMiddleware(logger)],
        )
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from litestar.middleware import AbstractMiddleware
from litestar.status_codes import HTTP_200_OK, HTTP_300_MULTIPLE_CHOICES

from litestar_admin.audit.logger import (
    AuditAction,
    AuditEntry,
    AuditLogger,
)

if TYPE_CHECKING:
    from litestar.types import ASGIApp, Message, Receive, Scope, Send

__all__ = [
    "AuditMiddleware",
    "AuditMiddlewareConfig",
]


# HTTP method to action mapping
_METHOD_ACTION_MAP: dict[str, AuditAction] = {
    "POST": AuditAction.CREATE,
    "GET": AuditAction.READ,
    "PUT": AuditAction.UPDATE,
    "PATCH": AuditAction.UPDATE,
    "DELETE": AuditAction.DELETE,
}

# Pattern for extracting model name and record ID from paths
# Matches: /admin/api/models/{model_name}/{record_id}
_MODEL_PATH_PATTERN = re.compile(r"/api/models/([^/]+)(?:/([^/]+))?$")


@dataclass
class AuditMiddlewareConfig:
    """Configuration for the audit middleware.

    Attributes:
        log_reads: Whether to log READ actions (can be noisy).
        log_path_patterns: List of regex patterns for paths to audit.
        exclude_path_patterns: List of regex patterns for paths to exclude.
        log_successful_only: Only log successful responses (2xx status codes).
        include_request_body: Include request body in metadata (use with caution).
        max_body_size: Maximum request body size to include (bytes).

    Example:
        Configure to skip read logging::

            config = AuditMiddlewareConfig(
                log_reads=False,
                log_path_patterns=[r"/admin/api/.*"],
            )
    """

    log_reads: bool = False
    log_path_patterns: list[str] = field(default_factory=lambda: [r"/admin/api/models/.*"])
    exclude_path_patterns: list[str] = field(default_factory=lambda: [r"/admin/api/models/[^/]+/schema$"])
    log_successful_only: bool = True
    include_request_body: bool = False
    max_body_size: int = 10240


class AuditMiddleware(AbstractMiddleware):
    """Litestar middleware for automatic audit logging.

    Automatically logs admin panel requests based on configured rules.
    Extracts model names, record IDs, and actor information from requests.

    Attributes:
        logger: The audit logger to use for storing entries.
        config: Configuration options for the middleware.

    Example:
        Basic usage::

            from litestar_admin.audit import AuditMiddleware, InMemoryAuditLogger

            logger = InMemoryAuditLogger()
            middleware = AuditMiddleware(logger)

        With configuration::

            config = AuditMiddlewareConfig(log_reads=True)
            middleware = AuditMiddleware(logger, config=config)
    """

    scopes: ClassVar[set[str]] = {"http"}

    def __init__(
        self,
        app: ASGIApp,
        logger: AuditLogger,
        config: AuditMiddlewareConfig | None = None,
    ) -> None:
        """Initialize the audit middleware.

        Args:
            app: The ASGI application.
            logger: The audit logger to use for storing entries.
            config: Configuration options. Uses defaults if not provided.
        """
        super().__init__(app)
        self._logger = logger
        self._config = config or AuditMiddlewareConfig()
        self._include_patterns = [re.compile(p) for p in self._config.log_path_patterns]
        self._exclude_patterns = [re.compile(p) for p in self._config.exclude_path_patterns]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process the request and optionally log it.

        Args:
            scope: The ASGI scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "GET")

        # Check if path should be audited
        if not self._should_audit(path, method):
            await self.app(scope, receive, send)
            return

        # Capture response status
        response_status: int | None = None

        async def send_wrapper(message: Message) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 200)
            await send(message)

        # Process the request
        await self.app(scope, receive, send_wrapper)

        # Log if appropriate
        if self._should_log_response(response_status):
            await self._log_request(scope, method, path, response_status)

    def _should_audit(self, path: str, method: str) -> bool:
        """Determine if a request path should be audited.

        Args:
            path: The request path.
            method: The HTTP method.

        Returns:
            True if the request should be audited.
        """
        # Skip reads if configured
        if method == "GET" and not self._config.log_reads:
            return False

        # Check exclusion patterns first
        for pattern in self._exclude_patterns:
            if pattern.search(path):
                return False

        # Check inclusion patterns
        return any(pattern.search(path) for pattern in self._include_patterns)

    def _should_log_response(self, status: int | None) -> bool:
        """Determine if a response should be logged based on status.

        Args:
            status: The HTTP response status code.

        Returns:
            True if the response should be logged.
        """
        if status is None:
            return False

        if self._config.log_successful_only:
            return HTTP_200_OK <= status < HTTP_300_MULTIPLE_CHOICES

        return True

    async def _log_request(
        self,
        scope: Scope,
        method: str,
        path: str,
        status: int | None,
    ) -> None:
        """Create and log an audit entry for a request.

        Args:
            scope: The ASGI scope.
            method: The HTTP method.
            path: The request path.
            status: The response status code.
        """
        # Determine action from method
        action = _METHOD_ACTION_MAP.get(method, AuditAction.READ)

        # Check for bulk operations
        if "bulk" in path.lower():
            if method == "DELETE":
                action = AuditAction.BULK_DELETE
            elif method == "POST":
                action = AuditAction.BULK_ACTION

        # Extract model name and record ID from path
        model_name, record_id = self._extract_model_info(path)

        # Extract actor info from scope
        actor_id, actor_email = self._extract_actor_from_scope(scope)

        # Extract request info
        ip_address, user_agent = self._extract_request_info_from_scope(scope)

        # Build metadata
        metadata: dict[str, Any] = {
            "path": path,
            "method": method,
            "status": status,
        }

        # Add query parameters if present
        query_string = scope.get("query_string", b"")
        if query_string:
            metadata["query_string"] = query_string.decode("utf-8", errors="replace")

        entry = AuditEntry(
            action=action,
            actor_id=actor_id,
            actor_email=actor_email,
            model_name=model_name,
            record_id=record_id,
            metadata=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        await self._logger.log(entry)

    def _extract_model_info(self, path: str) -> tuple[str | None, str | int | None]:
        """Extract model name and record ID from a request path.

        Args:
            path: The request path.

        Returns:
            Tuple of (model_name, record_id). Either may be None.
        """
        match = _MODEL_PATH_PATTERN.search(path)
        if not match:
            return None, None

        model_name = match.group(1)
        record_id: str | int | None = match.group(2)

        # Try to convert record_id to int if it looks numeric
        if record_id is not None:
            with contextlib.suppress(ValueError):
                record_id = int(record_id)

        return model_name, record_id

    def _extract_actor_from_scope(self, scope: Scope) -> tuple[str | int | None, str | None]:
        """Extract actor information from ASGI scope.

        Args:
            scope: The ASGI scope.

        Returns:
            Tuple of (actor_id, actor_email).
        """
        # Check for user in scope state
        state = scope.get("state", {})
        user = state.get("user")

        if user is None:
            # Try scope directly (some frameworks put user here)
            user = scope.get("user")

        if user is None:
            return None, None

        actor_id = getattr(user, "id", None)
        actor_email = getattr(user, "email", None)

        return actor_id, actor_email

    def _extract_request_info_from_scope(self, scope: Scope) -> tuple[str | None, str | None]:
        """Extract request information from ASGI scope.

        Args:
            scope: The ASGI scope.

        Returns:
            Tuple of (ip_address, user_agent).
        """
        # Get IP address from client
        ip_address: str | None = None
        client = scope.get("client")
        if client:
            ip_address = client[0] if isinstance(client, tuple) else None

        # Get headers
        headers = dict(scope.get("headers", []))

        # Check for X-Forwarded-For header
        forwarded_for = headers.get(b"x-forwarded-for")
        if forwarded_for:
            ip_address = forwarded_for.decode("utf-8").split(",")[0].strip()

        # Get user agent
        user_agent: str | None = None
        user_agent_bytes = headers.get(b"user-agent")
        if user_agent_bytes:
            user_agent = user_agent_bytes.decode("utf-8", errors="replace")

        return ip_address, user_agent
