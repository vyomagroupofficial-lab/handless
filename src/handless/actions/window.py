"""Window management actions.

Handles focusing, minimizing, maximizing, switching, and closing windows.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
import pyautogui

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class WindowController:
    """Manages desktop windows."""

    def close(self, window: Optional[Any] = None) -> bool:
        """Close active or specified window."""
        if window is not None:
            try:
                window.close()
                logger.info("Closed window via UIA handle.")
                return True
            except Exception as exc:
                logger.debug("window.close() failed: %s. Falling back to Alt+F4.", exc)

        # Standard Windows close shortcut
        try:
            pyautogui.hotkey("alt", "f4")
            logger.info("Closed active window via Alt+F4.")
            return True
        except Exception as exc:
            logger.error("Failed to close window: %s", exc)
            return False

    def minimize(self, window: Optional[Any] = None) -> bool:
        """Minimize window."""
        if window is not None:
            try:
                window.minimize()
                return True
            except Exception:
                pass

        try:
            pyautogui.hotkey("win", "down")
            return True
        except Exception as exc:
            logger.error("Failed to minimize window: %s", exc)
            return False

    def maximize(self, window: Optional[Any] = None) -> bool:
        """Maximize window."""
        if window is not None:
            try:
                window.maximize()
                return True
            except Exception:
                pass

        try:
            pyautogui.hotkey("win", "up")
            return True
        except Exception as exc:
            logger.error("Failed to maximize window: %s", exc)
            return False

    def switch_window(self) -> bool:
        """Switch to previous/next application window."""
        try:
            pyautogui.hotkey("alt", "tab")
            return True
        except Exception as exc:
            logger.error("Failed to switch window: %s", exc)
            return False
