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


def _is_key(k: keyboard.Key | keyboard.KeyCode, target_char: str) -> bool:
    """Robust key matching for Windows pynput supporting char, control codes, and virtual keys."""
    target_lower = target_char.lower()
    target_vk = ord(target_lower.upper())
    # 1. Direct char match & Ctrl-code match (e.g. Ctrl+T is '\x14')
    if hasattr(k, "char") and k.char:
        c = k.char
        if c.lower() == target_lower:
            return True
        if len(c) == 1 and ord(c) == (ord(target_lower) - ord('a') + 1):
            return True
    # 2. Virtual Key code match (e.g. VK_T = 84)
    if hasattr(k, "vk") and k.vk:
        if k.vk == target_vk:
            return True
    return False


class GlobalHotkeyManager:
    """Manages system-wide hotkeys."""

    def __init__(
        self,
        on_ptt_pressed: Optional[Callable[[], None]] = None,
        on_ptt_released: Optional[Callable[[], None]] = None,
        on_toggle_bar: Optional[Callable[[], None]] = None,
        on_toggle_dictation: Optional[Callable[[], None]] = None,
        on_flow_pressed: Optional[Callable[[], None]] = None,
        on_flow_released: Optional[Callable[[], None]] = None,
        on_screen_lens: Optional[Callable[[], None]] = None,
        on_transform_selection: Optional[Callable[[], None]] = None,
        on_undo_dictation: Optional[Callable[[], None]] = None,
    ) -> None:
        self.on_ptt_pressed = on_ptt_pressed
        self.on_ptt_released = on_ptt_released
        self.on_toggle_bar = on_toggle_bar
        self.on_toggle_dictation = on_toggle_dictation
        self.on_flow_pressed = on_flow_pressed
        self.on_flow_released = on_flow_released
        self.on_screen_lens = on_screen_lens
        self.on_transform_selection = on_transform_selection
        self.on_undo_dictation = on_undo_dictation

        self._listener: Optional[keyboard.Listener] = None
        self._current_keys: Set[keyboard.Key | keyboard.KeyCode] = set()
        self._ptt_active = False
        self._flow_active = False
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
            is_win = any(
                k in (getattr(keyboard.Key, "cmd", None), getattr(keyboard.Key, "cmd_l", None), getattr(keyboard.Key, "cmd_r", None))
                for k in self._current_keys if k is not None
            )

            # Check Screen Lens (Win + Shift + Space or Alt + Shift + Space)
            if (is_win or is_alt) and is_shift and key == keyboard.Key.space:
                if self.on_screen_lens:
                    try:
                        self.on_screen_lens()
                    except Exception as exc:
                        logger.error("Error in on_screen_lens callback: %s", exc)
                return

            # Check Double-Escape for emergency stop
            if key == keyboard.Key.esc:
                emergency_stop.handle_escape_key()

            # Check Ctrl+Shift+Q for Emergency Stop
            if is_ctrl and is_shift and _is_key(key, "q"):
                emergency_stop.trigger(reason="Global hotkey Ctrl+Shift+Q")
                return

            # Check Transform Selected Text (Rewrite)
            # Supported combinations: Ctrl+Alt+T, Alt+Shift+T, Ctrl+Alt+R, Ctrl+Shift+T
            is_transform_key = _is_key(key, "t") or _is_key(key, "r")
            if ((is_ctrl and is_alt) or (is_alt and is_shift) or (is_ctrl and is_shift)) and is_transform_key:
                if self._flow_active:
                    self._flow_active = False
                    if self.on_flow_released:
                        try:
                            self.on_flow_released()
                        except Exception:
                            pass
                if self.on_transform_selection:
                    try:
                        self.on_transform_selection()
                    except Exception as exc:
                        logger.error("Error in on_transform_selection callback: %s", exc)
                return

            # Check Ctrl+Alt+Z for Revert / Undo AI Edit
            if is_ctrl and is_alt and _is_key(key, "z"):
                if self.on_undo_dictation:
                    try:
                        self.on_undo_dictation()
                    except Exception as exc:
                        logger.error("Error in on_undo_dictation callback: %s", exc)
                return

            # Check Ctrl+Alt+H for toggling voice bar
            if is_ctrl and is_alt and _is_key(key, "h"):
                if self.on_toggle_bar:
                    self.on_toggle_bar()
                return

            # Check Ctrl+Alt+D for toggling Dictation Mode (OpenWhispr pattern)
            if is_ctrl and is_alt and _is_key(key, "d"):
                if self.on_toggle_dictation:
                    try:
                        self.on_toggle_dictation()
                    except Exception as exc:
                        logger.error("Error in on_toggle_dictation callback: %s", exc)
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

            # Check Wispr Flow Mode (Hold Ctrl+Shift to dictate)
            if is_ctrl and is_shift and not _is_key(key, "q") and not is_transform_key and not self._flow_active:
                self._flow_active = True
                if self.on_flow_pressed:
                    try:
                        self.on_flow_pressed()
                    except Exception as exc:
                        logger.error("Error in on_flow_pressed callback: %s", exc)

    def _handle_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        with self._lock:
            self._current_keys.discard(key)

            # Check if Push-to-Talk released
            is_ctrl = any(
                k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
                for k in self._current_keys
            )
            is_shift = any(
                k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
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

            if self._flow_active and (not is_ctrl or not is_shift):
                self._flow_active = False
                if self.on_flow_released:
                    try:
                        self.on_flow_released()
                    except Exception as exc:
                        logger.error("Error in on_flow_released callback: %s", exc)

