"""Global hotkey listener using pynput.

Listens for push-to-talk key combinations and the emergency stop hotkey
globally across all Windows applications.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional, Set

from pynput import keyboard

from .emergency_stop import emergency_stop

logger = logging.getLogger(__name__)


class GlobalHotkeyManager:
    """Manages system-wide hotkeys."""

    def __init__(
        self,
        on_ptt_pressed: Optional[Callable[[], None]] = None,
        on_ptt_released: Optional[Callable[[], None]] = None,
        on_toggle_bar: Optional[Callable[[], None]] = None,
    ) -> None:
        self.on_ptt_pressed = on_ptt_pressed
        self.on_ptt_released = on_ptt_released
        self.on_toggle_bar = on_toggle_bar

        self._listener: Optional[keyboard.Listener] = None
        self._current_keys: Set[keyboard.Key | keyboard.KeyCode] = set()
        self._ptt_active = False
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start global keyboard hook in background."""
        if self._listener is not None:
            return

        self._listener = keyboard.Listener(
            on_press=self._handle_press,
            on_release=self._handle_release,
        )
        self._listener.daemon = True
        self._listener.start()
        logger.info("Global hotkey listener started.")

    def stop(self) -> None:
        """Stop global keyboard hook."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            logger.info("Global hotkey listener stopped.")

    def _handle_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        with self._lock:
            self._current_keys.add(key)
            is_ctrl = any(
                k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
                for k in self._current_keys
            )
            is_shift = any(
                k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
                for k in self._current_keys
            )
            is_alt = any(
                k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r)
                for k in self._current_keys
            )

            # Check Double-Escape for emergency stop
            if key == keyboard.Key.esc:
                emergency_stop.handle_escape_key()

            # Check Ctrl+Shift+Q for Emergency Stop
            is_q = False
            if hasattr(key, "char") and key.char and key.char.lower() == "q":
                is_q = True

            if is_ctrl and is_shift and is_q:
                emergency_stop.trigger(reason="Global hotkey Ctrl+Shift+Q")
                return

            # Check Ctrl+Alt+H for toggling voice bar
            is_h = False
            if hasattr(key, "char") and key.char and key.char.lower() == "h":
                is_h = True
            if is_ctrl and is_alt and is_h:
                if self.on_toggle_bar:
                    self.on_toggle_bar()
                return

            # Check Push-to-Talk (Ctrl+Space)
            is_space = key == keyboard.Key.space
            if is_ctrl and is_space and not self._ptt_active:
                self._ptt_active = True
                if self.on_ptt_pressed:
                    try:
                        self.on_ptt_pressed()
                    except Exception as exc:
                        logger.error("Error in on_ptt_pressed callback: %s", exc)

    def _handle_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        with self._lock:
            self._current_keys.discard(key)

            # Check if Push-to-Talk released
            is_ctrl = any(
                k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
                for k in self._current_keys
            )
            is_space = keyboard.Key.space in self._current_keys

            if self._ptt_active and (not is_ctrl or not is_space):
                self._ptt_active = False
                if self.on_ptt_released:
                    try:
                        self.on_ptt_released()
                    except Exception as exc:
                        logger.error("Error in on_ptt_released callback: %s", exc)
