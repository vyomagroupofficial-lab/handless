"""Watch Me & Automate - No-Code Desktop Voice Macro Recorder.

Enables users to record sequences of desktop interactions by saying:
  "Handless, watch what I do"
and then saving them with:
  "Call this 'Morning Report Workflow'"
or:
  "Save workflow as <Name>"

Captures mouse clicks, keyboard text entry, keyboard shortcuts, and Handless
action dispatches, packaging them into persistent Workflows that can be executed
autonomously by voice or 1-click.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, List, Optional, Set

import pynput
from pynput import keyboard, mouse
from PySide6.QtCore import QObject, Signal

try:
    import win32gui
    import win32process
except ImportError:
    win32gui = None  # type: ignore
    win32process = None  # type: ignore

from handless.actions.workflows import Workflow, WorkflowManager
from handless.intelligence.models import ActionRequest, ActionType

logger = logging.getLogger(__name__)


def get_active_window_title() -> str:
    """Return the title of the current foreground Windows application."""
    if not win32gui:
        return ""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            return win32gui.GetWindowText(hwnd).strip()
    except Exception:
        pass
    return ""


class MacroRecorder(QObject):
    """Event listener and synthesizer for user desktop action sequences."""

    recording_started = Signal()
    recording_stopped = Signal()
    action_recorded = Signal(object)      # passes ActionRequest
    action_count_changed = Signal(int)   # passes current total actions
    macro_saved = Signal(object)          # passes Workflow

    def __init__(
        self,
        workflow_manager: Optional[WorkflowManager] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.workflow_manager = workflow_manager or WorkflowManager()

        self._is_recording = False
        self._actions: List[ActionRequest] = []
        self._typed_buffer: List[str] = []
        self._current_keys: Set[Any] = set()
        self._lock = threading.Lock()

        self._mouse_listener: Optional[mouse.Listener] = None
        self._keyboard_listener: Optional[keyboard.Listener] = None
        self._last_action_timestamp = 0.0

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def action_count(self) -> int:
        with self._lock:
            return len(self._actions)

    @property
    def actions(self) -> List[ActionRequest]:
        with self._lock:
            return list(self._actions)

    def start_recording(self) -> None:
        """Begin listening and recording mouse clicks, keyboard typing, and shortcuts."""
        with self._lock:
            if self._is_recording:
                return
            self._is_recording = True
            self._actions.clear()
            self._typed_buffer.clear()
            self._current_keys.clear()
            self._last_action_timestamp = time.time()

        try:
            self._mouse_listener = mouse.Listener(
                on_click=self._on_mouse_click,
            )
            self._mouse_listener.daemon = True
            self._mouse_listener.start()

            self._keyboard_listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
            )
            self._keyboard_listener.daemon = True
            self._keyboard_listener.start()
        except Exception as exc:
            logger.error("Failed to start pynput macro listeners: %s", exc)

        self.recording_started.emit()
        self.action_count_changed.emit(0)
        logger.info("MacroRecorder: Started watching desktop actions.")

    def stop_and_save(self, name: str, description: Optional[str] = None) -> Optional[Workflow]:
        """Finalize recording and save the workflow with trigger phrases."""
        if not self._is_recording:
            return None

        self._stop_listeners()
        with self._lock:
            self._flush_typed_buffer_locked()
            recorded_actions = list(self._actions)
            self._is_recording = False

        self.recording_stopped.emit()

        if not recorded_actions:
            logger.warning("MacroRecorder: No actions were recorded to save.")
            return None

        clean_name = name.strip() or f"Workflow {int(time.time())}"
        clean_lower = clean_name.lower()

        # Build natural trigger phrases for voice matching
        triggers = [
            clean_lower,
            f"run {clean_lower}",
            f"execute {clean_lower}",
            f"start {clean_lower}",
            f"do {clean_lower}",
        ]

        desc = description or f"User-recorded macro with {len(recorded_actions)} action steps."
        workflow = Workflow(
            id=f"macro_{uuid.uuid4().hex[:8]}",
            name=clean_name,
            description=desc,
            icon="⚡",
            trigger_phrases=triggers,
            actions=recorded_actions,
            is_builtin=False,
        )

        self.workflow_manager.save(workflow)
        self.macro_saved.emit(workflow)
        logger.info("MacroRecorder: Successfully saved workflow '%s' with %d steps.", clean_name, len(recorded_actions))
        return workflow

    def save_macro(self, name: str = "", description: Optional[str] = None) -> Optional[Workflow]:
        """Convenience alias for stop_and_save."""
        return self.stop_and_save(name=name, description=description)

    def cancel_recording(self) -> None:
        """Discard recorded actions and stop listening."""
        if not self._is_recording:
            return
        self._stop_listeners()
        with self._lock:
            self._actions.clear()
            self._typed_buffer.clear()
            self._current_keys.clear()
            self._is_recording = False

        self.recording_stopped.emit()
        self.action_count_changed.emit(0)
        logger.info("MacroRecorder: Cancelled recording.")

    def discard_recording(self) -> None:
        """Convenience alias for cancel_recording."""
        self.cancel_recording()

    def record_action(self, action: ActionRequest) -> None:
        """Programmatically record an action (e.g. dispatched via voice command)."""
        if not self._is_recording:
            return
        with self._lock:
            self._flush_typed_buffer_locked()
            self._actions.append(action)
            count = len(self._actions)

        self.action_recorded.emit(action)
        self.action_count_changed.emit(count)
        logger.debug("MacroRecorder: Recorded action %s", action.action_type)

    def _stop_listeners(self) -> None:
        if self._mouse_listener:
            try:
                self._mouse_listener.stop()
            except Exception:
                pass
            self._mouse_listener = None

        if self._keyboard_listener:
            try:
                self._keyboard_listener.stop()
            except Exception:
                pass
            self._keyboard_listener = None

    def _flush_typed_buffer_locked(self) -> None:
        """Convert accumulated keystrokes into a single ActionType.TYPE action."""
        if not self._typed_buffer:
            return
        text = "".join(self._typed_buffer)
        self._typed_buffer.clear()
        if text.strip():
            target_app = get_active_window_title()
            action = ActionRequest(
                action_type=ActionType.TYPE,
                text=text,
                target_app=target_app or None,
            )
            self._actions.append(action)
            self.action_recorded.emit(action)
            self.action_count_changed.emit(len(self._actions))

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if not self._is_recording or not pressed:
            return
        # Only record left clicks
        if button != mouse.Button.left:
            return

        window_title = get_active_window_title()
        # Avoid recording clicks on Handless overlay widgets themselves
        if any(h in window_title.lower() for h in ("vyoma handless", "macro overlay", "screen lens")):
            return

        with self._lock:
            self._flush_typed_buffer_locked()
            action = ActionRequest(
                action_type=ActionType.CLICK,
                coordinates=[int(x), int(y)],
                target_app=window_title or None,
            )
            self._actions.append(action)
            count = len(self._actions)

        self.action_recorded.emit(action)
        self.action_count_changed.emit(count)

    def _on_key_press(self, key: Any) -> None:
        if not self._is_recording:
            return
        with self._lock:
            self._current_keys.add(key)
            is_ctrl = any(
                k in (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
                for k in self._current_keys
            )
            is_alt = any(
                k in (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r)
                for k in self._current_keys
            )
            is_win = any(
                k in (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r)
                for k in self._current_keys
            )
            is_shift = any(
                k in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
                for k in self._current_keys
            )

            # Special keys
            if key == keyboard.Key.enter:
                self._flush_typed_buffer_locked()
                action = ActionRequest(action_type=ActionType.KEY_PRESS, key="enter")
                self._actions.append(action)
                self.action_recorded.emit(action)
                self.action_count_changed.emit(len(self._actions))
                return

            if key == keyboard.Key.tab:
                self._flush_typed_buffer_locked()
                action = ActionRequest(action_type=ActionType.KEY_PRESS, key="tab")
                self._actions.append(action)
                self.action_recorded.emit(action)
                self.action_count_changed.emit(len(self._actions))
                return

            # Shortcut combinations (Ctrl+C, Ctrl+V, Ctrl+T, Ctrl+S, Win+Left, etc.)
            if is_ctrl or is_win or is_alt:
                key_name = ""
                if hasattr(key, "char") and key.char:
                    key_name = key.char.lower()
                elif hasattr(key, "name") and key.name:
                    key_name = key.name.lower()

                if key_name and key_name not in ("ctrl", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r", "cmd", "cmd_l", "cmd_r", "shift", "shift_l", "shift_r"):
                    self._flush_typed_buffer_locked()
                    prefix = []
                    if is_win:
                        prefix.append("win")
                    if is_ctrl:
                        prefix.append("ctrl")
                    if is_alt:
                        prefix.append("alt")
                    if is_shift:
                        prefix.append("shift")
                    prefix.append(key_name)
                    shortcut_str = "+".join(prefix)

                    action = ActionRequest(action_type=ActionType.SHORTCUT, keys=shortcut_str)
                    self._actions.append(action)
                    self.action_recorded.emit(action)
                    self.action_count_changed.emit(len(self._actions))
                return

            # Normal printable text character
            if hasattr(key, "char") and key.char:
                self._typed_buffer.append(key.char)
            elif key == keyboard.Key.space:
                self._typed_buffer.append(" ")
            elif key == keyboard.Key.backspace and self._typed_buffer:
                self._typed_buffer.pop()

    def _on_key_release(self, key: Any) -> None:
        with self._lock:
            self._current_keys.discard(key)
