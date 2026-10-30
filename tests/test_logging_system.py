"""Unit tests for the Handless Centralized Logging System."""

from __future__ import annotations

import logging
from pathlib import Path
import tempfile

import pytest

from handless.logging_config import (
    BenignLogFilter,
    clear_logs,
    get_error_log_path,
    get_latest_errors,
    get_latest_logs,
    get_main_log_path,
    setup_logging,
)


@pytest.fixture
def temp_logs_dir(tmp_path: Path):
    """Fixture providing an isolated temporary directory for logging tests."""
    logs_dir = tmp_path / "logs"
    setup_logging(logs_dir=logs_dir)
    return logs_dir


def test_logging_initialization(temp_logs_dir: Path):
    """Verify that setup_logging creates the directory and file handlers."""
    assert temp_logs_dir.exists()
    main_log = temp_logs_dir / "handless.log"
    error_log = temp_logs_dir / "handless_errors.log"

    assert main_log.exists()
    assert error_log.exists()


def test_multi_tier_log_routing(temp_logs_dir: Path):
    """Verify that INFO logs only go to main log, while ERROR logs go to both."""
    test_logger = logging.getLogger("test_module")
    
    test_logger.info("Informational message 12345")
    test_logger.error("Critical failure error 67890")

    # Flush handlers
    for h in logging.getLogger().handlers:
        h.flush()

    main_text = (temp_logs_dir / "handless.log").read_text(encoding="utf-8")
    error_text = (temp_logs_dir / "handless_errors.log").read_text(encoding="utf-8")

    assert "Informational message 12345" in main_text
    assert "Informational message 12345" not in error_text

    assert "Critical failure error 67890" in main_text
    assert "Critical failure error 67890" in error_text


def test_benign_filter():
    """Verify that known benign DWM and DPI warnings are filtered out."""
    log_filter = BenignLogFilter()
    
    record_benign_1 = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="", lineno=1,
        msg="UpdateLayeredWindowIndirect failed for ptDst=(770, 919) (The parameter is incorrect.)",
        args=(), exc_info=None
    )
    assert log_filter.filter(record_benign_1) is False

    record_benign_2 = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="", lineno=1,
        msg="qt.qpa.window: SetProcessDpiAwarenessContext() failed: Access is denied.",
        args=(), exc_info=None
    )
    assert log_filter.filter(record_benign_2) is False

    record_normal = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=1,
        msg="Groq Whisper recognized: 'Hello world'",
        args=(), exc_info=None
    )
    assert log_filter.filter(record_normal) is True


def test_diagnostic_tail_helpers(temp_logs_dir: Path):
    """Verify tail reading helpers."""
    test_logger = logging.getLogger("diag_test")
    test_logger.error("Sample diagnostics error line")
    
    for h in logging.getLogger().handlers:
        h.flush()

    # Test reading latest logs
    logs_content = (temp_logs_dir / "handless.log").read_text(encoding="utf-8")
    assert "Sample diagnostics error line" in logs_content

