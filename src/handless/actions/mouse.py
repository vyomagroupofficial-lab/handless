"""Mouse input action executor.

Simulates mouse clicks, double-clicks, right-clicks, and scrolling using either
pywinauto element handles (preferred for accessibility resilience) or pyautogui
screen coordinates as visual fallback.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Tuple
import pyautogui

logger = logging.getLogger(__name__)

# Use our own dedicated EmergencyStop instead of PyAutoGUI corner-crash
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class MouseController:
    """Dispatches mouse interactions."""

    def click(self, element: Optional[Any] = None, coordinates: Optional[Tuple[int, int]] = None) -> bool:
        """Perform a left click on an element or coordinate."""
        if element is not None:
            try:
                element.click_input()
                logger.info("Clicked UIA element: %s", getattr(element, "window_text", lambda: "Unknown")())
                return True
            except Exception as exc:
                logger.debug("element.click_input() failed, trying coordinates: %s", exc)
                try:
                    rect = element.rectangle()
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2
                    pyautogui.click(cx, cy)
                    return True
                except Exception as ex2:
                    logger.error("Failed to click element: %s", ex2)

        if coordinates is not None:
            try:
                x, y = coordinates
                pyautogui.click(x, y)
                logger.info("Clicked screen coordinates: (%d, %d)", x, y)
                return True
            except Exception as exc:
                logger.error("Failed to click coordinates: %s", exc)

        return False

    def double_click(self, element: Optional[Any] = None, coordinates: Optional[Tuple[int, int]] = None) -> bool:
        """Perform a double-click."""
        if element is not None:
            try:
                element.double_click_input()
                return True
            except Exception:
                try:
                    rect = element.rectangle()
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2
                    pyautogui.doubleClick(cx, cy)
                    return True
                except Exception as exc:
                    logger.error("Failed to double-click element: %s", exc)

        if coordinates is not None:
            x, y = coordinates
            pyautogui.doubleClick(x, y)
            return True

        return False

    def right_click(self, element: Optional[Any] = None, coordinates: Optional[Tuple[int, int]] = None) -> bool:
        """Perform a right-click (context menu)."""
        if element is not None:
            try:
                element.right_click_input()
                return True
            except Exception:
                try:
                    rect = element.rectangle()
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2
                    pyautogui.rightClick(cx, cy)
                    return True
                except Exception as exc:
                    logger.error("Failed to right-click element: %s", exc)

        if coordinates is not None:
            x, y = coordinates
            pyautogui.rightClick(x, y)
            return True

        return False

    def scroll(self, direction: str = "down", amount: int = 3) -> bool:
        """Scroll mouse wheel up or down at current position or over active screen."""
        try:
            cx, cy = pyautogui.position()
            # If cursor is resting in the top-left corner, reposition to center
            if cx < 30 and cy < 30:
                sw, sh = pyautogui.size()
                pyautogui.moveTo(sw // 2, sh // 2)

            clicks = amount * 120
            if direction.lower() in ("down", "bottom"):
                clicks = -clicks
            pyautogui.scroll(clicks)
            logger.info("Scrolled %s by %d units", direction, amount)
            return True
        except Exception as exc:
            logger.error("Failed to scroll: %s", exc)
            return False
