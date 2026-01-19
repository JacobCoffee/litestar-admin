"""Logging abstraction for litestar-admin with optional structlog support.

This module provides a unified logging interface that automatically uses structlog
when available, falling back to Python's standard logging module otherwise.

Example:
    Basic usage::

        from litestar_admin.logging import get_logger

        logger = get_logger("litestar_admin.mymodule")
        logger.info("Hello", user_id=123)

    With configuration::

        from litestar_admin.logging import configure_logging, LoggingConfig

        configure_logging(
            LoggingConfig(
                enable_structlog=True,
                log_level="DEBUG",
                json_logs=False,
            )
        )
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

__all__ = [
    "LoggingConfig",
    "configure_logging",
    "get_logger",
    "has_structlog",
]


def has_structlog() -> bool:
    """Check if structlog is available.

    Returns:
        True if structlog is installed and can be imported.
    """
    try:
        import structlog  # noqa: F401

        return True
    except ImportError:
        return False


@dataclass
class LoggingConfig:
    """Configuration for the logging system.

    Attributes:
        enable_structlog: Whether to use structlog when available.
            If True and structlog is installed, structlog will be used.
            If False, standard logging is always used regardless of availability.
        log_level: The minimum log level to emit (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_logs: Whether to output logs in JSON format (requires structlog).
        add_timestamp: Whether to add timestamps to log entries.
        processors: Custom structlog processors to use. If not provided, defaults are used.
        logger_name: Base logger name for the admin panel.
    """

    enable_structlog: bool = True
    log_level: str = "INFO"
    json_logs: bool = False
    add_timestamp: bool = True
    processors: list[Callable[..., Any]] | None = None
    logger_name: str = "litestar_admin"

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_levels:
            msg = f"log_level must be one of {valid_levels}"
            raise ValueError(msg)
        self.log_level = self.log_level.upper()


class _LoggingState:
    """Internal state container for the logging module."""

    __slots__ = ("config", "structlog_configured")

    def __init__(self) -> None:
        self.config: LoggingConfig | None = None
        self.structlog_configured: bool = False


# Module-level state container
_state = _LoggingState()


def configure_logging(config: LoggingConfig | None = None) -> None:
    """Configure the logging system.

    This function sets up either structlog or standard logging based on
    the configuration and availability of structlog.

    Args:
        config: Logging configuration. If None, uses defaults.

    Example:
        Configure with structlog and JSON output::

            configure_logging(
                LoggingConfig(
                    enable_structlog=True,
                    json_logs=True,
                    log_level="DEBUG",
                )
            )
    """
    _state.config = config or LoggingConfig()

    if _state.config.enable_structlog and has_structlog():
        _configure_structlog(_state.config)
        _state.structlog_configured = True
    else:
        _configure_stdlib(_state.config)
        _state.structlog_configured = False


def _configure_structlog(config: LoggingConfig) -> None:
    """Configure structlog with the given settings.

    Args:
        config: Logging configuration.
    """
    import structlog

    # Build processor chain
    processors: list[Any] = []

    if config.add_timestamp:
        processors.append(structlog.processors.TimeStamper(fmt="iso"))

    processors.extend(
        [
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]
    )

    # Use custom processors if provided
    if config.processors:
        processors = config.processors

    # Add the final renderer
    if config.json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty()))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging for foreign loggers
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, config.log_level),
    )


def _configure_stdlib(config: LoggingConfig) -> None:
    """Configure standard library logging.

    Args:
        config: Logging configuration.
    """
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    if not config.add_timestamp:
        log_format = "%(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        format=log_format,
        stream=sys.stderr,
        level=getattr(logging, config.log_level),
    )


class StructlogAdapter:
    """Adapter that wraps a structlog logger to provide a consistent interface."""

    __slots__ = ("_logger",)

    def __init__(self, logger: Any) -> None:
        """Initialize the adapter with a structlog logger.

        Args:
            logger: The underlying structlog logger.
        """
        self._logger = logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message."""
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception with traceback."""
        self._logger.exception(msg, *args, **kwargs)

    def bind(self, **kwargs: Any) -> StructlogAdapter:
        """Bind context variables to the logger.

        Args:
            **kwargs: Context variables to bind.

        Returns:
            A new adapter with the bound context.
        """
        return StructlogAdapter(self._logger.bind(**kwargs))


class StdlibAdapter:
    """Adapter that wraps a stdlib logger to provide structlog-like interface."""

    __slots__ = ("_context", "_logger")

    def __init__(self, logger: logging.Logger, context: dict[str, Any] | None = None) -> None:
        """Initialize the adapter with a stdlib logger.

        Args:
            logger: The underlying stdlib logger.
            context: Optional context dictionary for bound variables.
        """
        self._logger = logger
        self._context = context or {}

    def _format_msg(self, msg: str, **kwargs: Any) -> str:
        """Format message with context and kwargs."""
        all_context = {**self._context, **kwargs}
        if all_context:
            context_str = " ".join(f"{k}={v!r}" for k, v in all_context.items())
            return f"{msg} [{context_str}]"
        return msg

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a debug message."""
        self._logger.debug(self._format_msg(msg, **kwargs), *args)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an info message."""
        self._logger.info(self._format_msg(msg, **kwargs), *args)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a warning message."""
        self._logger.warning(self._format_msg(msg, **kwargs), *args)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an error message."""
        self._logger.error(self._format_msg(msg, **kwargs), *args)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log a critical message."""
        self._logger.critical(self._format_msg(msg, **kwargs), *args)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log an exception with traceback."""
        self._logger.exception(self._format_msg(msg, **kwargs), *args)

    def bind(self, **kwargs: Any) -> StdlibAdapter:
        """Bind context variables to the logger.

        Args:
            **kwargs: Context variables to bind.

        Returns:
            A new adapter with the bound context.
        """
        new_context = {**self._context, **kwargs}
        return StdlibAdapter(self._logger, new_context)


def get_logger(name: str | None = None) -> StructlogAdapter | StdlibAdapter:
    """Get a logger instance.

    Returns either a structlog or stdlib logger based on configuration.
    The returned logger has a consistent interface regardless of backend.

    Args:
        name: Logger name. If None, uses the base logger name from config.

    Returns:
        A logger adapter that can be used for logging.

    Example:
        Basic usage::

            logger = get_logger("litestar_admin.discovery")
            logger.info("Discovered model", model_name="User")

        With context binding::

            logger = get_logger("mymodule").bind(request_id="abc123")
            logger.info("Processing request")  # includes request_id
    """
    # Use default config if not configured
    if _state.config is None:
        _state.config = LoggingConfig()

    logger_name = name or _state.config.logger_name

    # Check if we should use structlog
    use_structlog = _state.config.enable_structlog and has_structlog()

    if use_structlog:
        import structlog

        # Configure structlog if not already done
        if not _state.structlog_configured:
            _configure_structlog(_state.config)
            _state.structlog_configured = True

        return StructlogAdapter(structlog.get_logger(logger_name))

    # Fall back to stdlib
    return StdlibAdapter(logging.getLogger(logger_name))
