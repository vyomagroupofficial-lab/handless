"""Keyboard action executor for typing and shortcuts.

Simulates keystrokes, clipboard-based reliable text insertion, and multi-key combinations.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional
import pyautogui
import pyperclip

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class KeyboardController:
    """Dispatches typing and keyboard shortcuts."""

    def type_text(self, text: str, element: Optional[Any] = None) -> bool:
        """Type text into an element or the currently focused application."""
        if not text:
            return True

        if element is not None:
            try:
                element.set_focus()
                element.type_keys(text, with_spaces=True, pause=0.01)
                logger.info("Typed text into element via pywinauto: %s", text)
                return True
            except Exception as exc:
                logger.debug("element.type_keys failed, falling back to clipboard: %s", exc)

        # Fallback to clipboard paste for reliable unicode typing without layout issues
        try:
            from ..dictation.paste_controller import paste_text
            success = paste_text(text, preserve_clipboard=True)
            if success:
                logger.info("Typed text via clipboard paste: %s", text)
                return True
        except Exception as exc:
            logger.debug("paste_text helper error: %s. Using basic clipboard fallback.", exc)

        try:
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            logger.info("Typed text via basic clipboard paste: %s", text)
            return True
        except Exception:
            try:
                pyautogui.write(text, interval=0.01)
                return True
            except Exception as exc:
                logger.error("Failed to type text: %s", exc)
                return False

    def press_key(self, key_name: str) -> bool:
        """Press a single key (e.g. 'enter', 'space', 'tab', 'esc')."""
        try:
            clean_key = key_name.strip().lower()
            if clean_key == "escape":
                clean_key = "esc"
            pyautogui.press(clean_key)
            logger.info("Pressed key: %s", clean_key)
            return True
        except Exception as exc:
            logger.error("Failed to press key %s: %s", key_name, exc)
            return False

    def execute_shortcut(self, shortcut: str) -> bool:
        """Execute a hotkey combination (e.g. 'ctrl+c', 'alt+tab', 'ctrl+shift+esc')."""
        try:
            keys: List[str] = [k.strip().lower() for k in shortcut.split("+")]
            pyautogui.hotkey(*keys)
            logger.info("Executed shortcut: %s", shortcut)
            return True
        except Exception as exc:
            logger.error("Failed to execute shortcut %s: %s", shortcut, exc)
            return False
