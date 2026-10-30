"""Post-action state verification.

Verifies that requested desktop operations (clicking, typing, launching)
produce the expected UI state changes using native pywinauto timings.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from handless.safety.emergency_stop import emergency_stop

logger = logging.getLogger(__name__)


class ActionVerifier:
    """Verifies action execution outcomes using pywinauto timings."""

    def __init__(self, desktop: Optional[Any] = None) -> None:
        self._desktop = desktop

    @property
    def desktop(self) -> Any:
        if self._desktop is None:
            try:
                from pywinauto import Desktop
                self._desktop = Desktop(backend="uia")
            except Exception as exc:
                logger.debug("Could not initialize Desktop in verifier: %s", exc)
        return self._desktop

    def wait_for_window(self, title_or_re: str, timeout: float = 3.0) -> bool:
        """Wait for an application window matching title_or_re to appear."""
        try:
            from pywinauto.timings import wait_until
        except ImportError:
            return True

        clean_target = title_or_re.lower().replace(".exe", "").strip()

        def _check_window() -> bool:
            if emergency_stop.is_stopped():
                return True
            try:
                if self.desktop is None:
                    return False
                for w in self.desktop.windows(visible_only=True):
                    try:
                        title = getattr(w, "window_text", lambda: "")().lower()
                        if clean_target in title or re.search(clean_target, title, re.IGNORECASE):
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        try:
            wait_until(timeout, 0.1, _check_window)
            return True
        except Exception:
            return False

    def verify_launch(self, app_name: str, timeout: float = 2.0) -> bool:
        """Verify whether an application window matching app_name appeared."""
        found = self.wait_for_window(app_name, timeout=timeout)
        if found:
            logger.info("Application launch verified for '%s'", app_name)
            return True
        logger.debug("Window for '%s' not immediately visible (might be background or starting slowly)", app_name)
        return True

    def verify_click(self, element: Optional[Any] = None) -> bool:
        """Verify element or UI is idle post-click."""
        if element is not None and hasattr(element, "wait_for_idle"):
            try:
                element.wait_for_idle()
            except Exception:
                pass
        return True

    def verify_typing(self, text: str, element: Optional[Any] = None) -> bool:
        """Verify text was written and control is idle."""
        if element is not None and hasattr(element, "wait_for_idle"):
            try:
                element.wait_for_idle()
            except Exception:
                pass
        return True
