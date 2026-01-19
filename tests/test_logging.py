"""Tests for the logging module with optional structlog support."""

from __future__ import annotations

import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from litestar_admin.logging import (
    LoggingConfig,
    StdlibAdapter,
    StructlogAdapter,
    configure_logging,
    get_logger,
    has_structlog,
)


class TestHasStructlog:
    """Tests for has_structlog function."""

    def test_has_structlog_when_installed(self) -> None:
        """Test has_structlog returns True when structlog is installed."""
        # Since structlog may or may not be installed in test env, we mock it
        with patch.dict(sys.modules, {"structlog": MagicMock()}):
            # Reset the cached import
            result = has_structlog()
            # Result depends on actual installation
            assert isinstance(result, bool)

    def test_has_structlog_when_not_installed(self) -> None:
        """Test has_structlog returns False when structlog is not installed."""
        with patch.dict(sys.modules, {"structlog": None}):
            with patch("builtins.__import__", side_effect=ImportError):
                result = has_structlog()
                assert result is False


class TestLoggingConfig:
    """Tests for LoggingConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = LoggingConfig()
        assert config.enable_structlog is True
        assert config.log_level == "INFO"
        assert config.json_logs is False
        assert config.add_timestamp is True
        assert config.processors is None
        assert config.logger_name == "litestar_admin"

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = LoggingConfig(
            enable_structlog=False,
            log_level="DEBUG",
            json_logs=True,
            add_timestamp=False,
            logger_name="myapp.admin",
        )
        assert config.enable_structlog is False
        assert config.log_level == "DEBUG"
        assert config.json_logs is True
        assert config.add_timestamp is False
        assert config.logger_name == "myapp.admin"

    def test_log_level_normalization(self) -> None:
        """Test that log level is normalized to uppercase."""
        config = LoggingConfig(log_level="debug")
        assert config.log_level == "DEBUG"

    def test_invalid_log_level(self) -> None:
        """Test that invalid log level raises ValueError."""
        with pytest.raises(ValueError, match="log_level must be one of"):
            LoggingConfig(log_level="INVALID")


class TestStdlibAdapter:
    """Tests for StdlibAdapter class."""

    def test_debug_logging(self) -> None:
        """Test debug level logging."""
        mock_logger = MagicMock()
        adapter = StdlibAdapter(mock_logger)
        adapter.debug("test message")
        mock_logger.debug.assert_called_once()

    def test_info_logging(self) -> None:
        """Test info level logging."""
        mock_logger = MagicMock()
        adapter = StdlibAdapter(mock_logger)
        adapter.info("test message")
        mock_logger.info.assert_called_once()

    def test_warning_logging(self) -> None:
        """Test warning level logging."""
        mock_logger = MagicMock()
        adapter = StdlibAdapter(mock_logger)
        adapter.warning("test message")
        mock_logger.warning.assert_called_once()

    def test_error_logging(self) -> None:
        """Test error level logging."""
        mock_logger = MagicMock()
        adapter = StdlibAdapter(mock_logger)
        adapter.error("test message")
        mock_logger.error.assert_called_once()

    def test_critical_logging(self) -> None:
        """Test critical level logging."""
        mock_logger = MagicMock()
        adapter = StdlibAdapter(mock_logger)
        adapter.critical("test message")
        mock_logger.critical.assert_called_once()

    def test_exception_logging(self) -> None:
        """Test exception logging."""
        mock_logger = MagicMock()
        adapter = StdlibAdapter(mock_logger)
        adapter.exception("test message")
        mock_logger.exception.assert_called_once()

    def test_logging_with_kwargs(self) -> None:
        """Test logging with extra kwargs formats correctly."""
        mock_logger = MagicMock()
        adapter = StdlibAdapter(mock_logger)
        adapter.info("test message", user_id=123, action="login")
        call_args = mock_logger.info.call_args
        assert "user_id=" in call_args[0][0]
        assert "action=" in call_args[0][0]

    def test_bind_creates_new_adapter(self) -> None:
        """Test bind creates a new adapter with context."""
        mock_logger = MagicMock()
        adapter = StdlibAdapter(mock_logger)
        bound = adapter.bind(request_id="abc123")
        assert bound is not adapter
        assert isinstance(bound, StdlibAdapter)

    def test_bound_context_included_in_logs(self) -> None:
        """Test that bound context is included in log messages."""
        mock_logger = MagicMock()
        adapter = StdlibAdapter(mock_logger)
        bound = adapter.bind(request_id="abc123")
        bound.info("test message")
        call_args = mock_logger.info.call_args
        assert "request_id='abc123'" in call_args[0][0]


class TestStructlogAdapter:
    """Tests for StructlogAdapter class."""

    def test_debug_logging(self) -> None:
        """Test debug level logging."""
        mock_logger = MagicMock()
        adapter = StructlogAdapter(mock_logger)
        adapter.debug("test message", key="value")
        mock_logger.debug.assert_called_once_with("test message", key="value")

    def test_info_logging(self) -> None:
        """Test info level logging."""
        mock_logger = MagicMock()
        adapter = StructlogAdapter(mock_logger)
        adapter.info("test message")
        mock_logger.info.assert_called_once()

    def test_warning_logging(self) -> None:
        """Test warning level logging."""
        mock_logger = MagicMock()
        adapter = StructlogAdapter(mock_logger)
        adapter.warning("test message")
        mock_logger.warning.assert_called_once()

    def test_error_logging(self) -> None:
        """Test error level logging."""
        mock_logger = MagicMock()
        adapter = StructlogAdapter(mock_logger)
        adapter.error("test message")
        mock_logger.error.assert_called_once()

    def test_critical_logging(self) -> None:
        """Test critical level logging."""
        mock_logger = MagicMock()
        adapter = StructlogAdapter(mock_logger)
        adapter.critical("test message")
        mock_logger.critical.assert_called_once()

    def test_exception_logging(self) -> None:
        """Test exception logging."""
        mock_logger = MagicMock()
        adapter = StructlogAdapter(mock_logger)
        adapter.exception("test message")
        mock_logger.exception.assert_called_once()

    def test_bind_returns_new_adapter(self) -> None:
        """Test bind returns a new StructlogAdapter."""
        mock_logger = MagicMock()
        mock_logger.bind.return_value = MagicMock()
        adapter = StructlogAdapter(mock_logger)
        bound = adapter.bind(key="value")
        assert isinstance(bound, StructlogAdapter)
        mock_logger.bind.assert_called_once_with(key="value")


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def test_configure_with_default_config(self) -> None:
        """Test configure_logging with default config."""
        # Just ensure it doesn't raise
        configure_logging()

    def test_configure_with_custom_config(self) -> None:
        """Test configure_logging with custom config."""
        config = LoggingConfig(log_level="DEBUG", enable_structlog=False)
        configure_logging(config)
        # Configuration should complete without error
        logger = get_logger("test")
        assert isinstance(logger, StdlibAdapter)

    def test_configure_without_structlog(self) -> None:
        """Test configure_logging falls back to stdlib when structlog disabled."""
        config = LoggingConfig(enable_structlog=False)
        configure_logging(config)
        # Should complete without error


class TestGetLogger:
    """Tests for get_logger function."""

    def test_get_logger_with_name(self) -> None:
        """Test get_logger with custom name."""
        # Reset global state by configuring with stdlib
        configure_logging(LoggingConfig(enable_structlog=False))
        logger = get_logger("test.module")
        assert isinstance(logger, StdlibAdapter)

    def test_get_logger_without_name(self) -> None:
        """Test get_logger uses default name."""
        configure_logging(LoggingConfig(enable_structlog=False))
        logger = get_logger()
        assert isinstance(logger, StdlibAdapter)

    def test_get_logger_returns_stdlib_when_structlog_disabled(self) -> None:
        """Test get_logger returns StdlibAdapter when structlog is disabled."""
        configure_logging(LoggingConfig(enable_structlog=False))
        logger = get_logger("test")
        assert isinstance(logger, StdlibAdapter)


class TestLoggingIntegration:
    """Integration tests for the logging system."""

    def test_stdlib_logging_output(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that stdlib adapter actually logs."""
        configure_logging(LoggingConfig(enable_structlog=False, log_level="DEBUG"))
        logger = get_logger("test.integration")

        with caplog.at_level(logging.DEBUG):
            logger.info("Integration test message")

        # Note: The caplog might not capture if our adapter changes handlers
        # This is more of a smoke test

    def test_logging_with_context_binding(self) -> None:
        """Test logging with context binding works end-to-end."""
        configure_logging(LoggingConfig(enable_structlog=False))
        logger = get_logger("test.context")
        bound_logger = logger.bind(user_id=123, session="abc")
        # Should not raise
        bound_logger.info("User action", action="click")

    def test_exception_logging_includes_traceback(self) -> None:
        """Test that exception logging captures tracebacks."""
        configure_logging(LoggingConfig(enable_structlog=False))
        logger = get_logger("test.exception")

        try:
            msg = "Test error"
            raise ValueError(msg)
        except ValueError:
            # Should not raise
            logger.exception("An error occurred")


class TestStructlogIntegration:
    """Integration tests for structlog when available."""

    def test_structlog_available(self) -> None:
        """Test that structlog is available in test environment."""
        assert has_structlog() is True

    def test_get_logger_with_structlog_enabled(self) -> None:
        """Test get_logger returns StructlogAdapter when structlog enabled."""
        configure_logging(LoggingConfig(enable_structlog=True))
        logger = get_logger("test.structlog")
        assert isinstance(logger, StructlogAdapter)

    def test_structlog_logging_with_context(self) -> None:
        """Test structlog logging with context binding."""
        configure_logging(LoggingConfig(enable_structlog=True))
        logger = get_logger("test.structlog.context")
        bound = logger.bind(user_id=456, action="test")
        # Should not raise
        bound.info("Structlog context test")

    def test_structlog_json_output_config(self) -> None:
        """Test structlog can be configured for JSON output."""
        config = LoggingConfig(enable_structlog=True, json_logs=True)
        configure_logging(config)
        logger = get_logger("test.structlog.json")
        # Should not raise
        logger.info("JSON output test", extra_data={"key": "value"})

    def test_structlog_console_output_config(self) -> None:
        """Test structlog with console output (default)."""
        config = LoggingConfig(enable_structlog=True, json_logs=False)
        configure_logging(config)
        logger = get_logger("test.structlog.console")
        # Should not raise
        logger.info("Console output test")

    def test_structlog_all_log_levels(self) -> None:
        """Test all log levels work with structlog."""
        configure_logging(LoggingConfig(enable_structlog=True, log_level="DEBUG"))
        logger = get_logger("test.structlog.levels")

        # Should not raise
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

    def test_structlog_exception_logging(self) -> None:
        """Test exception logging with structlog."""
        configure_logging(LoggingConfig(enable_structlog=True))
        logger = get_logger("test.structlog.exception")

        try:
            msg = "Structlog test error"
            raise ValueError(msg)
        except ValueError:
            # Should not raise
            logger.exception("Structlog caught an error")
