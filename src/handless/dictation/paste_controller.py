"""Clipboard-preserving text inserter with terminal awareness.

Inspired by OpenWhispr: automatically detects terminal windows (issuing Ctrl+Shift+V)
versus standard Windows apps (Ctrl+V), and preserves the user's prior clipboard content
so dictating does not overwrite their copied text.
"""

from __future__ import annotations

import logging
import time
from typing import Optional
import pyautogui
import pyperclip

logger = logging.getLogger(__name__)

TERMINAL_PROCESS_NAMES = {
    "cmd.exe",
    "powershell.exe",
    "pwsh.exe",
    "windowsterminal.exe",
    "wt.exe",
    "alacritty.exe",
    "wezterm-gui.exe",
    "kitty.exe",
    "hyper.exe",
    "conhost.exe",
    "bash.exe",
    "mintty.exe",
}


def is_terminal_window(process_name: Optional[str] = None, class_name: Optional[str] = None) -> bool:
    """Check if the currently active foreground window belongs to a terminal process."""
    if process_name is not None:
        if process_name.lower() in TERMINAL_PROCESS_NAMES:
            return True
        if class_name and ("console" in class_name.lower() or "terminal" in class_name.lower()):
            return True
        return False

    try:
        import win32gui
        import win32process
        import psutil

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return False

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return False

        proc = psutil.Process(pid)
        name = (proc.name() or "").lower()
        if name in TERMINAL_PROCESS_NAMES:
            return True

        # Check window class or title for terminal hints
        cls_name = win32gui.GetClassName(hwnd).lower()
        if "console" in cls_name or "terminal" in cls_name:
            return True

    except Exception as exc:
        logger.debug("Terminal window detection error: %s", exc)

    return False


def get_active_window_title() -> str:
    """Get the window title or process name of the active foreground window."""
    try:
        import win32gui
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            title = win32gui.GetWindowText(hwnd).strip()
            if title:
                return title
    except Exception:
        pass
    try:
        import ctypes
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            title = buff.value.strip()
            if title:
                return title
    except Exception:
        pass
    return "Desktop App"


class PasteController:
    """Manages fast, reliable text insertion into any desktop application."""

    def __init__(self, preserve_clipboard: bool = True) -> None:
        self.preserve_clipboard = preserve_clipboard

    def _read_clipboard(self) -> Optional[str]:
        try:
            return pyperclip.paste()
        except Exception:
            return None

    def _write_clipboard(self, text: str) -> None:
        try:
            pyperclip.copy(text)
        except Exception as exc:
            logger.debug("Could not copy to clipboard: %s", exc)

    def _send_paste_shortcut(self, is_terminal: bool) -> None:
        if is_terminal:
            logger.debug("Terminal detected; pasting via Ctrl+Shift+V")
            pyautogui.hotkey("ctrl", "shift", "v")
        else:
            pyautogui.hotkey("ctrl", "v")

    def insert_text(self, text: str, preserve_clipboard: Optional[bool] = None) -> bool:
        """Insert text at the current cursor position."""
        if not text:
            return True

        preserve = self.preserve_clipboard if preserve_clipboard is None else preserve_clipboard
        old_clipboard: Optional[str] = None
        if preserve:
            old_clipboard = self._read_clipboard()

        try:
            # 1. Place dictated text onto clipboard
            self._write_clipboard(text)

            # 2. Determine appropriate shortcut (Ctrl+Shift+V for terminals, Ctrl+V for GUI)
            is_term = is_terminal_window()
            self._send_paste_shortcut(is_term)

            # 3. Allow target application window message loop to consume clipboard data
            time.sleep(0.04)

            # 4. Restore original clipboard content
            if preserve and old_clipboard is not None:
                self._write_clipboard(old_clipboard)

            return True

        except Exception as exc:
            logger.warning("Clipboard paste failed (%s); falling back to direct keystrokes.", exc)
            try:
                pyautogui.write(text, interval=0.005)
                return True
            except Exception as write_exc:
                logger.error("Keystroke typing fallback failed: %s", write_exc)
                return False

    def paste(self, text: str, preserve_clipboard: Optional[bool] = None) -> bool:
        """Convenience alias for insert_text."""
        return self.insert_text(text, preserve_clipboard=preserve_clipboard)


# Module-level convenience function
_default_controller = PasteController(preserve_clipboard=True)


def paste_text(text: str, preserve_clipboard: bool = True) -> bool:
    """Insert text at active cursor with terminal detection and clipboard preservation."""
    controller = _default_controller if preserve_clipboard else PasteController(preserve_clipboard=False)
    return controller.insert_text(text)
