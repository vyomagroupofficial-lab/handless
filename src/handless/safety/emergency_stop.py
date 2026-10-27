"""Emergency stop coordinator for Vyoma Handless.

Provides a thread-safe kill-switch mechanism that immediately halts all
in-flight and queued actions when triggered by the global hotkey,
double-escape tap, or user interface button.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, List

logger = logging.getLogger(__name__)


class EmergencyStop:
    """Thread-safe emergency stop manager."""

    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._callbacks: List[Callable[[], None]] = []
        self._lock = threading.Lock()
        self._last_escape_time: float = 0.0

    def trigger(self, reason: str = "User initiated") -> None:
        """Trigger the emergency stop."""
        self._stop_event.set()
        logger.warning("EMERGENCY STOP TRIGGERED: %s", reason)
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error("Error executing emergency stop callback: %s", exc)

    def reset(self) -> None:
        """Reset the stop state so new actions can be run."""
        self._stop_event.clear()
        logger.info("Emergency stop reset.")

    def is_stopped(self) -> bool:
        """Check if an emergency stop is active."""
        return self._stop_event.is_set()

    def register_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be invoked when emergency stop fires."""
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[], None]) -> None:
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)

    def handle_escape_key(self) -> bool:
        """Check for rapid double-escape tap within 500ms.

        Returns:
            True if emergency stop was triggered by double escape.
        """
        now = time.time()
        if now - self._last_escape_time <= 0.5:
            self.trigger(reason="Double Escape key tap")
            self._last_escape_time = 0.0
            return True
        self._last_escape_time = now
        return False


# Global singleton
emergency_stop = EmergencyStop()
