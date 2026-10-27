"""Central Action Dispatcher.

Coordinates action execution, element locating, vision fallbacks, safety gates,
and emergency stop checks across all subsystems.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, List, Optional

from handless.intelligence.models import ActionRequest, ActionType, WindowActionType
from handless.safety.emergency_stop import emergency_stop
from handless.screen.uia_inspector import UIAInspector
from handless.screen.vision_analyzer import ScreenVisionAnalyzer

from .keyboard import KeyboardController
from .launcher import ApplicationLauncher
from .mouse import MouseController
from .verifier import ActionVerifier
from .window import WindowController

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """Executes high-level ActionRequests safely."""

    def __init__(
        self,
        uia_inspector: Optional[UIAInspector] = None,
        vision_analyzer: Optional[ScreenVisionAnalyzer] = None,
        mouse: Optional[MouseController] = None,
        keyboard: Optional[KeyboardController] = None,
        window: Optional[WindowController] = None,
        launcher: Optional[ApplicationLauncher] = None,
        verifier: Optional[ActionVerifier] = None,
        enable_vision_fallback: bool = True,
    ) -> None:
        self.uia = uia_inspector or UIAInspector()
        self.vision = vision_analyzer or ScreenVisionAnalyzer()
        self.mouse = mouse or MouseController()
        self.keyboard = keyboard or KeyboardController()
        self.window = window or WindowController()
        self.launcher = launcher or ApplicationLauncher()
        self.verifier = verifier or ActionVerifier()
        self.enable_vision_fallback = enable_vision_fallback

    def execute_plan(
        self,
        actions: List[ActionRequest],
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Execute a sequence of actions with emergency stop checks between steps."""
        if not actions:
            return True

        for idx, act in enumerate(actions):
            # Check emergency stop before every action
            if emergency_stop.is_stopped():
                logger.warning("Action execution interrupted by EMERGENCY STOP.")
                if status_callback:
                    status_callback("⛔ Emergency Stop")
                return False

            if status_callback:
                status_callback(self._describe_action(act))

            success = self.execute_action(act)
            if not success:
                logger.warning("Action step %d (%s) failed.", idx, act.action_type)
                if status_callback:
                    status_callback(f"Failed: {self._describe_action(act)}")
                return False

            # Brief pause between chained actions for UI stabilization
            time.sleep(0.1)

        if status_callback:
            status_callback("Done ✓")
        return True

    def execute_action(self, action: ActionRequest) -> bool:
        """Execute an individual ActionRequest."""
        if emergency_stop.is_stopped():
            return False

        t = action.action_type

        # 1. Launch App
        if t == ActionType.LAUNCH_APP:
            if not action.target:
                return False
            success = self.launcher.launch(action.target)
            self.verifier.verify_launch(action.target)
            return success

        # 2. Mouse Clicks
        if t in (ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.RIGHT_CLICK):
            element = None
            coords = action.coordinates

            if action.target and not coords:
                # First try UIA element search
                element = self.uia.find_element(action.target, target_type=action.target_type)

                # Fallback to Vision if UIA found nothing
                if not element and self.enable_vision_fallback:
                    logger.info("UIA did not find '%s'. Trying visual analysis...", action.target)
                    coords = self.vision.locate_element_coordinates(action.target)

            if t == ActionType.CLICK:
                return self.mouse.click(element=element, coordinates=coords)
            elif t == ActionType.DOUBLE_CLICK:
                return self.mouse.double_click(element=element, coordinates=coords)
            elif t == ActionType.RIGHT_CLICK:
                return self.mouse.right_click(element=element, coordinates=coords)

        # 3. Typing
        if t == ActionType.TYPE:
            element = None
            if action.target:
                element = self.uia.find_element(action.target, target_type="edit")
            return self.keyboard.type_text(action.text or "", element=element)

        # 4. Key Press
        if t == ActionType.KEY_PRESS:
            return self.keyboard.press_key(action.keys or "enter")

        # 5. Shortcuts
        if t == ActionType.SHORTCUT:
            return self.keyboard.execute_shortcut(action.keys or "")

        # 6. Scrolling
        if t == ActionType.SCROLL:
            direction = action.scroll_direction or "down"
            return self.mouse.scroll(direction=direction, amount=action.scroll_amount)

        # 7. Window Management
        if t == ActionType.WINDOW_ACTION:
            w_act = action.window_action
            target_win = None
            if action.target:
                target_win = self.uia.get_active_window()

            if w_act == WindowActionType.CLOSE:
                return self.window.close(target_win)
            elif w_act == WindowActionType.MINIMIZE:
                return self.window.minimize(target_win)
            elif w_act == WindowActionType.MAXIMIZE:
                return self.window.maximize(target_win)
            elif w_act == WindowActionType.SWITCH:
                return self.window.switch_window()

        # 8. Wait
        if t == ActionType.WAIT:
            time.sleep(0.5)
            return True

        if t == ActionType.NONE:
            return True

        return False

    def _describe_action(self, action: ActionRequest) -> str:
        t = action.action_type
        if t == ActionType.LAUNCH_APP:
            return f"Opening {action.target or 'application'}..."
        if t == ActionType.CLICK:
            return f"Clicking {action.target or 'element'}..."
        if t == ActionType.DOUBLE_CLICK:
            return f"Double-clicking {action.target or 'element'}..."
        if t == ActionType.RIGHT_CLICK:
            return f"Right-clicking {action.target or 'element'}..."
        if t == ActionType.TYPE:
            preview = (action.text[:18] + "...") if action.text and len(action.text) > 18 else (action.text or "")
            return f"Typing '{preview}'..."
        if t == ActionType.SHORTCUT:
            return f"Hotkey {action.keys}..."
        if t == ActionType.WINDOW_ACTION:
            return f"Window {action.window_action or 'action'}..."
        if t == ActionType.SCROLL:
            return f"Scrolling {action.scroll_direction or 'down'}..."
        return "Executing action..."
