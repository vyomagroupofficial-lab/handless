"""Windows UI Automation (UIA) Inspector using pywinauto.

Interrogates active Windows desktop applications, enumerating interactive controls
(buttons, text fields, tabs, menus) via native Microsoft UI Automation COM interfaces.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

import pywinauto
from pywinauto import Desktop

from .element_matcher import find_best_element_match

logger = logging.getLogger(__name__)


class UIAInspector:
    """Queries Windows desktop applications using UI Automation backend."""

    def __init__(self) -> None:
        self.desktop = Desktop(backend="uia")

    def get_active_window(self) -> Optional[Any]:
        """Retrieve the currently focused/active desktop top-level window."""
        try:
            # Connect to active foreground window
            win = self.desktop.window(active_only=True)
            if win.exists(timeout=0.5):
                return win
        except Exception as exc:
            logger.debug("Could not get active window directly: %s", exc)

        # Fallback to top window on desktop
        try:
            windows = self.desktop.windows(visible_only=True)
            for w in windows:
                try:
                    if w.is_active():
                        return w
                except Exception:
                    continue
        except Exception as exc:
            logger.error("Failed to list desktop windows: %s", exc)

        return None

    def find_element(
        self,
        target_name: str,
        target_type: Optional[str] = None,
        search_entire_desktop: bool = False,
    ) -> Optional[Any]:
        """Find an interactive control matching target_name.

        First searches inside the currently active foreground window.
        If not found and search_entire_desktop=True, searches all visible windows.
        """
        active_win = self.get_active_window()
        if active_win:
            try:
                candidates = active_win.descendants()
                match = find_best_element_match(target_name, candidates, target_type=target_type)
                if match:
                    _, elem = match
                    return elem
            except Exception as exc:
                logger.debug("Error searching descendants of active window: %s", exc)

        if search_entire_desktop:
            try:
                all_candidates = self.desktop.descendants()
                match = find_best_element_match(target_name, all_candidates, target_type=target_type)
                if match:
                    _, elem = match
                    return elem
            except Exception as exc:
                logger.error("Error searching all desktop descendants: %s", exc)

        return None

    def get_visible_elements_summary(self, max_elements: int = 30) -> List[str]:
        """Return a compact human-readable summary of visible controls in active window."""
        active_win = self.get_active_window()
        if not active_win:
            return []

        summary = []
        try:
            descendants = active_win.descendants()
            for d in descendants:
                if len(summary) >= max_elements:
                    break
                try:
                    text = d.window_text().strip()
                    ctype = d.friendly_class_name()
                    if text and d.is_visible() and ctype in ("Button", "Edit", "MenuItem", "TabItem", "Hyperlink"):
                        summary.append(f"[{ctype}] {text}")
                except Exception:
                    continue
        except Exception:
            pass

        return summary
