"""Tests for logging configuration."""

import logging
from pathlib import Path

from linkedin_scraper import logging_config


class TestSetupLogging:
    """Tests for setup_logging behavior."""

    def test_setup_logging_creates_file_handler(self, tmp_path: Path, monkeypatch) -> None:
        """Verify file handler is created when enabled."""
        monkeypatch.setattr(logging_config, "_initialized", False)

        logging_config.setup_logging(log_dir=tmp_path, log_to_file=True)

        handlers = logging.getLogger().handlers
        assert any(isinstance(handler, logging.FileHandler) for handler in handlers)
        assert any(path.suffix == ".log" for path in tmp_path.iterdir())

    def test_setup_logging_skips_file_handler_when_disabled(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Verify no file handler is added when disabled."""
        monkeypatch.setattr(logging_config, "_initialized", False)

        logging_config.setup_logging(log_dir=tmp_path, log_to_file=False)

        handlers = logging.getLogger().handlers
        assert not any(isinstance(handler, logging.FileHandler) for handler in handlers)
        assert not any(path.suffix == ".log" for path in tmp_path.iterdir())

    def test_setup_logging_returns_when_initialized(self, monkeypatch) -> None:
        """Verify repeated calls are ignored after initialization."""
        root_logger = logging.getLogger()
        sentinel = logging.NullHandler()
        root_logger.handlers = [sentinel]

        monkeypatch.setattr(logging_config, "_initialized", True)
        logging_config.setup_logging()

        assert root_logger.handlers == [sentinel]
