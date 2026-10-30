"""Centralized Logging System for Vyoma Handless.

Provides:
1. Multi-tier logging with automatic log file rotation:
   - logs/handless.log: Complete activity log with timestamps, threads, and modules.
   - logs/handless_errors.log: Dedicated error log capturing WARNING, ERROR, and CRITICAL events.
2. Clean, structured console output with benign noise filtering.
3. Global unhandled exception interception for both main and background worker threads.
4. PySide6 Qt message handler integration to capture Qt warnings/errors into the log file.
5. Diagnostic utilities for inspecting, viewing, and opening logs from UI or chat.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import threading
import warnings
from typing import Optional


# Default project logs directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"

MAIN_LOG_FILE = LOGS_DIR / "handless.log"
ERROR_LOG_FILE = LOGS_DIR / "handless_errors.log"

# Filter known benign Windows / COM / DPI warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto.*")
warnings.filterwarnings("ignore", message=".*Revert to STA COM threading mode.*")


class BenignLogFilter(logging.Filter):
    """Filter out known benign OS or library warnings that clutter console/logs."""

    BENIGN_SUBSTRINGS = (
        "SetProcessDpiAwarenessContext() failed",
        "UpdateLayeredWindowIndirect failed",
        "Revert to STA COM threading mode",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        for benign in self.BENIGN_SUBSTRINGS:
            if benign in msg:
                return False
        return True


def setup_logging(
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    logs_dir: Optional[Path] = None,
) -> Path:
    """Initialize the complete multi-tier Handless logging subsystem.
    
    Returns the resolved logs directory path.
    """
    target_dir = logs_dir or LOGS_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    main_log_path = target_dir / "handless.log"
    error_log_path = target_dir / "handless_errors.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear existing handlers to prevent duplicate lines
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # 1. Console Handler (Clean, high-level summary)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(BenignLogFilter())
    root_logger.addHandler(console_handler)

    # 2. Main Rotating File Handler (10MB per file, up to 5 backups)
    try:
        main_file_handler = RotatingFileHandler(
            filename=str(main_log_path),
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        main_file_handler.setLevel(file_level)
        file_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s:%(lineno)d: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        main_file_handler.setFormatter(file_formatter)
        root_logger.addHandler(main_file_handler)
    except Exception as exc:
        print(f"Failed to initialize main log file handler: {exc}", file=sys.stderr)

    # 3. Dedicated Error Rotating File Handler (5MB, warnings & errors only)
    try:
        error_file_handler = RotatingFileHandler(
            filename=str(error_log_path),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        error_file_handler.setLevel(logging.WARNING)
        error_formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(threadName)s] %(name)s:%(lineno)d: %(message)s\nContext: %(pathname)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        error_file_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_file_handler)
    except Exception as exc:
        print(f"Failed to initialize error log file handler: {exc}", file=sys.stderr)

    # 4. Install Global Exception Hooks
    _install_exception_hooks()

    # 5. Install Qt Message Handler if PySide6 is loaded
    _install_qt_message_handler()

    root_logger.info("Logging initialized. Main log: %s | Error log: %s", main_log_path, error_log_path)
    return target_dir


def _install_exception_hooks() -> None:
    """Intercept unhandled exceptions on main thread and background threads."""
    logger = logging.getLogger("handless.crash")

    def handle_sys_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.critical(
            "Unhandled Main Thread Exception: %s: %s",
            exc_type.__name__,
            exc_value,
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = handle_sys_exception

    def handle_thread_exception(args: threading.ExceptHookArgs):
        if issubclass(args.exc_type, SystemExit):
            return
        logger.critical(
            "Unhandled Background Thread Exception in [%s]: %s: %s",
            getattr(args.thread, "name", "unknown_thread"),
            args.exc_type.__name__,
            args.exc_value,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = handle_thread_exception


def _install_qt_message_handler() -> None:
    """Capture Qt internal messages and route them through python logging."""
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler

        qt_logger = logging.getLogger("handless.qt")

        def qt_message_router(mode: QtMsgType, context, message: str) -> None:
            # Filter known benign Windows platform / DWM messages
            if any(b in message for b in (
                "UpdateLayeredWindowIndirect failed",
                "SetProcessDpiAwarenessContext",
                "DPI_AWARENESS_CONTEXT",
            )):
                return

            if "Cannot set parent, new parent is in a different thread" in message:
                qt_logger.warning("Qt Thread Boundary Warning: %s", message)
                return

            if mode == QtMsgType.QtDebugMsg:
                qt_logger.debug(message)
            elif mode == QtMsgType.QtInfoMsg:
                qt_logger.info(message)
            elif mode == QtMsgType.QtWarningMsg:
                qt_logger.warning(message)
            elif mode == QtMsgType.QtCriticalMsg:
                qt_logger.error(message)
            elif mode == QtMsgType.QtFatalMsg:
                qt_logger.critical("FATAL: %s", message)

        qInstallMessageHandler(qt_message_router)
    except Exception:
        # PySide6 might not be available in headless test environments
        pass


# ---------------------------------------------------------------------------
# Diagnostic Utilities
# ---------------------------------------------------------------------------

def get_log_dir() -> Path:
    """Return the active logs directory."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR


def get_main_log_path() -> Path:
    return MAIN_LOG_FILE


def get_error_log_path() -> Path:
    return ERROR_LOG_FILE


def get_latest_logs(max_lines: int = 100) -> str:
    """Read the tail of the main log file."""
    if not MAIN_LOG_FILE.exists():
        return "No log file found."
    try:
        with open(MAIN_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-max_lines:])
    except Exception as exc:
        return f"Failed to read logs: {exc}"


def get_latest_errors(max_lines: int = 50) -> str:
    """Read the tail of the error log file."""
    if not ERROR_LOG_FILE.exists():
        return "No errors recorded."
    try:
        with open(ERROR_LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            if not lines:
                return "No errors recorded. System healthy ✓"
            return "".join(lines[-max_lines:])
    except Exception as exc:
        return f"Failed to read error logs: {exc}"


def open_logs_directory() -> bool:
    """Open the logs folder in Windows File Explorer."""
    import subprocess
    target = get_log_dir()
    try:
        os.startfile(str(target))
        return True
    except Exception:
        try:
            subprocess.Popen(["explorer.exe", str(target)])
            return True
        except Exception:
            return False


def clear_logs() -> bool:
    """Clear active log files."""
    try:
        if MAIN_LOG_FILE.exists():
            MAIN_LOG_FILE.write_text("", encoding="utf-8")
        if ERROR_LOG_FILE.exists():
            ERROR_LOG_FILE.write_text("", encoding="utf-8")
        return True
    except Exception:
        return False

