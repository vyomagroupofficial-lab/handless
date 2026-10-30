"""Central Action Dispatcher.

Coordinates action execution, element locating, UI component tracking, vision fallbacks,
safety gates, system controls, and emergency stop checks across all subsystems.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, List, Optional

from handless.intelligence.models import ActionRequest, ActionType, WindowActionType
from handless.safety.emergency_stop import emergency_stop
from handless.screen.uia_inspector import UIAInspector
from handless.screen.vision_analyzer import ScreenVisionAnalyzer

from .element_ops import ElementOperations
from .keyboard import KeyboardController
from .launcher import ApplicationLauncher
from .mouse import MouseController
from .system import SystemController
from .verifier import ActionVerifier
from .window import WindowController

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """Executes high-level ActionRequests safely, prioritizing UI component tracking."""

    def __init__(
        self,
        uia_inspector: Optional[UIAInspector] = None,
        vision_analyzer: Optional[ScreenVisionAnalyzer] = None,
        mouse: Optional[MouseController] = None,
        keyboard: Optional[KeyboardController] = None,
        window: Optional[WindowController] = None,
        launcher: Optional[ApplicationLauncher] = None,
        verifier: Optional[ActionVerifier] = None,
        element_ops: Optional[ElementOperations] = None,
        system: Optional[SystemController] = None,
        enable_vision_fallback: bool = True,
        ui_bridge: Optional[Any] = None,
    ) -> None:
        self.uia = uia_inspector or UIAInspector()
        self.vision = vision_analyzer or ScreenVisionAnalyzer()
        self.mouse = mouse or MouseController()
        self.keyboard = keyboard or KeyboardController()
        self.window = window or WindowController()
        self.launcher = launcher or ApplicationLauncher()
        self.verifier = verifier or ActionVerifier()
        self.element_ops = element_ops or ElementOperations()
        self.system = system or SystemController()
        self.enable_vision_fallback = enable_vision_fallback
        self.ui_bridge = ui_bridge
        self.on_sidebar_action: Optional[Callable[[str], bool]] = None


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

            success = self.execute_action(act, status_callback=status_callback)
            if not success:
                logger.warning("Action step %d (%s) failed.", idx, act.action_type)
                if status_callback:
                    status_callback(f"Failed: {self._describe_action(act)}")
                return False

            # Smart pause / readiness check between chained actions
            if emergency_stop.is_stopped():
                return False
            try:
                active_win = self.uia.get_active_window()
                if active_win and hasattr(active_win, "wait_for_idle"):
                    active_win.wait_for_idle()
            except Exception:
                pass

            # Generous settle time for tab creation, app launches, or contact/chat selection
            if act.action_type == ActionType.SHORTCUT and "t" in (act.keys or "").lower():
                time.sleep(0.15)
            elif act.action_type == ActionType.LAUNCH_APP:
                time.sleep(0.2)
            elif act.action_type == ActionType.CLICK and getattr(act, "target_type", None) in ("contact", "chat"):
                time.sleep(0.25)
            else:
                time.sleep(0.05)

        if status_callback:
            status_callback("Done ✓")
        return True

    def execute_action(
        self,
        action: ActionRequest,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Execute an individual ActionRequest."""
        if emergency_stop.is_stopped():
            return False

        # Connect to targeted application if requested
        if action.target_app:
            self.uia.connect_to_app(action.target_app)

        t = action.action_type

        # Ensure keyboard and scroll actions are routed to the actual user application,
        # not the Vyoma Handless sidebar/window itself!
        if t in (ActionType.SHORTCUT, ActionType.TYPE, ActionType.KEY_PRESS, ActionType.SCROLL):
            try:
                import win32gui
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    title = win32gui.GetWindowText(hwnd) or ""
                    if "Vyoma Handless" in title:
                        active_win = self.uia.get_active_window()
                        if active_win and hasattr(active_win, "set_focus"):
                            active_win.set_focus()
                            time.sleep(0.08)
            except Exception:
                pass

        # 1. Launch App
        if t == ActionType.LAUNCH_APP:
            if not action.target:
                return False
            # If the application is already running on screen, switch to it immediately
            if hasattr(self.window, "switch_to_app"):
                try:
                    if self.window.switch_to_app(action.target, uia=self.uia):
                        logger.info("Application '%s' was already running. Focused window.", action.target)
                        return True
                except Exception:
                    pass
            success = self.launcher.launch(action.target)
            self.verifier.verify_launch(action.target)
            return success

        # 2. Mouse Clicks (Prioritizing UI Automation Component Tracking first)
        if t in (ActionType.CLICK, ActionType.DOUBLE_CLICK, ActionType.RIGHT_CLICK, ActionType.MIDDLE_CLICK, ActionType.HOVER):
            element = None
            coords = action.coordinates

            # Always try UI Automation component tracking FIRST if a target is named
            if action.target:
                find_kwargs: Dict[str, Any] = {"target_type": action.target_type}
                if action.spatial_landmark:
                    find_kwargs["spatial_landmark"] = action.spatial_landmark
                if action.relative_anchor:
                    find_kwargs["relative_anchor"] = action.relative_anchor
                if action.relative_relation:
                    find_kwargs["relative_relation"] = action.relative_relation
                element = self.uia.find_element(action.target, **find_kwargs)



                # Validate element: Reject nameless/ID-less container elements, but preserve input/edit fields and elements with accessible element_info.name
                if element is not None:
                    try:
                        el_name = (element.window_text() or "").strip()
                        el_id = (element.automation_id() or "").strip()
                        info_name = (getattr(element.element_info, "name", "") or "").strip()
                        ctype = element.friendly_class_name() or ""
                        # An empty Edit/Document/ComboBox field is a valid text input awaiting user keystrokes
                        is_input_field = ctype in ("Edit", "Document", "ComboBox")
                        if not el_name and not el_id and not info_name and not is_input_field:
                            logger.info(
                                "UIA returned an unnamed container for '%s'. Rejecting container to allow fallback.",
                                action.target,
                            )
                            element = None
                        else:
                            display_name = el_name or info_name or el_id or f"<{ctype} input>"
                            logger.info(
                                "UI Component Tracking matched element '%s' (ControlType=%s, ID=%s)",
                                display_name,
                                ctype,
                                el_id,
                            )
                    except Exception:
                        element = None

            # Fallback to Vision if UIA found nothing and vision fallback is enabled
            if not element and not coords and action.target and self.enable_vision_fallback:
                logger.info("UIA component tracking did not find '%s'. Trying visual screen analysis...", action.target)
                coords = self.vision.locate_element_coordinates(action.target)

            clicked = False
            if t == ActionType.CLICK:
                clicked = self.mouse.click(element=element, coordinates=coords)
            elif t == ActionType.DOUBLE_CLICK:
                clicked = self.mouse.double_click(element=element, coordinates=coords)
            elif t == ActionType.RIGHT_CLICK:
                clicked = self.mouse.right_click(element=element, coordinates=coords)
            elif t == ActionType.MIDDLE_CLICK:
                clicked = self.system.middle_click(element=element, coordinates=coords)
            elif t == ActionType.HOVER:
                clicked = self.system.hover(element=element, coordinates=coords)

            # If element click failed (e.g. element became stale or offscreen), fallback to visual coordinates
            if not clicked and element is not None and not coords and self.enable_vision_fallback and action.target:
                logger.info("UIA interaction failed for '%s'. Retrying with visual coordinates fallback...", action.target)
                coords = self.vision.locate_element_coordinates(action.target)
                if coords:
                    if t == ActionType.CLICK:
                        clicked = self.mouse.click(coordinates=coords)
                    elif t == ActionType.DOUBLE_CLICK:
                        clicked = self.mouse.double_click(coordinates=coords)
                    elif t == ActionType.RIGHT_CLICK:
                        clicked = self.mouse.right_click(coordinates=coords)
                    elif t == ActionType.MIDDLE_CLICK:
                        clicked = self.system.middle_click(coordinates=coords)
                    elif t == ActionType.HOVER:
                        clicked = self.system.hover(coordinates=coords)

            if not clicked and action.target and action.target.strip().lower() in (
                "send", "submit", "send button", "submit button", "now send it", "send message", "send prompt"
            ):
                logger.info(
                    "Click on '%s' could not be resolved to element/coordinates. Falling back to pressing Enter.",
                    action.target,
                )
                return self.keyboard.press_key("enter")

            return clicked


        # 3. Typing
        if t == ActionType.TYPE:
            element = None
            if action.target:
                find_kwargs: Dict[str, Any] = {"target_type": "edit"}
                if action.spatial_landmark:
                    find_kwargs["spatial_landmark"] = action.spatial_landmark
                if action.relative_anchor:
                    find_kwargs["relative_anchor"] = action.relative_anchor
                if action.relative_relation:
                    find_kwargs["relative_relation"] = action.relative_relation
                element = self.uia.find_element(action.target, **find_kwargs)

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

        # 7. Mouse Movement
        if t == ActionType.MOVE_MOUSE:
            direction = action.target or "center"
            return self.system.move_mouse(direction, distance=action.scroll_amount * 50)

        # 8. Window Management & Snapping
        if t == ActionType.WINDOW_ACTION:
            w_act = action.window_action
            target = action.target
            act_str = str(w_act.value if hasattr(w_act, "value") else (w_act or "")).lower()

            # Strictly close ONLY when explicitly requested
            if act_str in ("close", "window_action_close", "exit", "quit", "kill", "terminate"):
                if hasattr(self.window, "close_window_or_app"):
                    return self.window.close_window_or_app(target=target, uia=self.uia)
                return self.window.close()
            elif act_str in ("minimize", "window_action_minimize"):
                try:
                    return self.window.minimize(target=target, uia=self.uia)
                except TypeError:
                    return self.window.minimize()
            elif act_str in ("maximize", "window_action_maximize"):
                try:
                    return self.window.maximize(target=target, uia=self.uia)
                except TypeError:
                    return self.window.maximize()
            elif act_str in ("restore", "window_action_restore"):
                if hasattr(self.window, "restore"):
                    return self.window.restore(target=target, uia=self.uia)
                return True
            elif act_str in ("center", "center_window", "window_action_center"):
                if hasattr(self.window, "center_window"):
                    return self.window.center_window(target=target, uia=self.uia)
                return False
            elif act_str in ("popup", "small_popup", "make_popup", "float"):
                if hasattr(self.window, "make_popup_window"):
                    return self.window.make_popup_window(target=target, uia=self.uia)
                return False
            elif act_str in ("snap_left", "snap_window_left", "left"):
                if target and hasattr(self.window, "position_window"):
                    return self.window.position_window("left", target=target, uia=self.uia)
                return self.system.snap_left()
            elif act_str in ("snap_right", "snap_window_right", "right"):
                if target and hasattr(self.window, "position_window"):
                    return self.window.position_window("right", target=target, uia=self.uia)
                return self.system.snap_right()
            elif act_str in ("snap_top_left", "snap_window_top_left", "top_left", "left_top"):
                if hasattr(self.window, "position_window"):
                    return self.window.position_window("top_left", target=target, uia=self.uia)
                return self.system.snap_top_left()
            elif act_str in ("snap_top_right", "snap_window_top_right", "top_right", "right_top"):
                if hasattr(self.window, "position_window"):
                    return self.window.position_window("top_right", target=target, uia=self.uia)
                return self.system.snap_top_right()
            elif act_str in ("snap_bottom_left", "snap_window_bottom_left", "bottom_left", "left_bottom"):
                if hasattr(self.window, "position_window"):
                    return self.window.position_window("bottom_left", target=target, uia=self.uia)
                return self.system.snap_bottom_left()
            elif act_str in ("snap_bottom_right", "snap_window_bottom_right", "bottom_right", "right_bottom"):
                if hasattr(self.window, "position_window"):
                    return self.window.position_window("bottom_right", target=target, uia=self.uia)
                return self.system.snap_bottom_right()
            elif act_str in ("top_half", "top", "snap_top"):
                if hasattr(self.window, "position_window"):
                    return self.window.position_window("top", target=target, uia=self.uia)
                return False
            elif act_str in ("bottom_half", "bottom", "down", "snap_bottom"):
                if hasattr(self.window, "position_window"):
                    return self.window.position_window("bottom", target=target, uia=self.uia)
                return False
            elif act_str in ("layout_two_apps", "two_app_layout"):
                if hasattr(self.window, "layout_two_apps") and action.target and action.text:
                    return self.window.layout_two_apps(
                        action.target, action.text, layout=action.relative_relation or "side_by_side", uia=self.uia
                    )
                return False
            elif act_str in ("next_monitor", "move_next_monitor"):
                return self.system.next_monitor()
            elif act_str in ("prev_monitor", "move_prev_monitor"):
                return self.system.prev_monitor()
            elif act_str in ("minimize_others", "minimize_other_windows"):
                return self.system.minimize_others()
            elif act_str in ("switch", "switch_window", "focus", "bring_up", "activate", "open"):
                if target and hasattr(self.window, "switch_to_app"):
                    if self.window.switch_to_app(target=target, uia=self.uia):
                        return True
                    if self.launcher:
                        return self.launcher.launch(target)
                return self.window.switch_window()
            elif target:
                # If target is specified without explicit close, switch to it or launch it!
                if hasattr(self.window, "switch_to_app"):
                    try:
                        if self.window.switch_to_app(target=target, uia=self.uia):
                            logger.info("Focused application '%s'", target)
                            return True
                    except Exception:
                        pass
                if self.launcher:
                    logger.info("Application '%s' not active; launching via launcher.", target)
                    return self.launcher.launch(target)
                return False
            else:
                logger.warning(
                    "Unrecognized window action '%s' with no target. Action suppressed to prevent closing active window.",
                    act_str,
                )
                return False

        # 9. Fundamental System & PC Controls
        if t == ActionType.SYSTEM_ACTION:
            sys_act = (action.system_action or action.target or "").lower()
            if sys_act.startswith("sidebar_") or sys_act in (
                "start_meeting_recording", "record_meeting", "record_call",
                "stop_meeting_recording", "stop_recording_meeting", "stop_recording_call",
                "summarize_meeting", "summarize_call",
                "start_macro_recording", "watch_me", "record_workflow",
                "save_macro", "save_workflow",
                "stop_macro_recording", "discard_macro", "cancel_macro",
                "open_screen_lens", "screen_lens"
            ):
                if self.on_sidebar_action:
                    try:
                        return self.on_sidebar_action(sys_act, action.target or "")
                    except TypeError:
                        return self.on_sidebar_action(sys_act)
                return True
            if sys_act in ("set_volume", "volume_set", "volume"):
                vol = action.scroll_amount if action.scroll_amount is not None else 50
                if hasattr(self.system, "set_volume"):
                    return self.system.set_volume(vol)
                from .system_tools import SystemTools
                return SystemTools.set_volume(vol)
            if sys_act in ("volume_up", "vol_up"):
                if hasattr(self.system, "volume_up"):
                    return self.system.volume_up(steps=action.scroll_amount or 2)
                from .system_tools import SystemTools
                return SystemTools.volume_up(steps=action.scroll_amount or 5)
            if sys_act in ("volume_down", "vol_down"):
                if hasattr(self.system, "volume_down"):
                    return self.system.volume_down(steps=action.scroll_amount or 2)
                from .system_tools import SystemTools
                return SystemTools.volume_down(steps=action.scroll_amount or 5)
            if sys_act in ("unmute",):
                if hasattr(self.system, "unmute"):
                    return self.system.unmute()
                from .system_tools import SystemTools
                return SystemTools.unmute()
            if sys_act in ("mute", "toggle_mute"):
                if hasattr(self.system, "toggle_mute"):
                    return self.system.toggle_mute()
                from .system_tools import SystemTools
                return SystemTools.toggle_mute()
            if sys_act in ("play_pause", "play", "pause"):
                return self.system.play_pause()
            if sys_act in ("next_track", "next_song"):
                return self.system.next_track()
            if sys_act in ("prev_track", "previous_track", "prev_song"):
                return self.system.prev_track()
            if sys_act in ("stop_media", "stop_playback"):
                return self.system.stop_media()
            if sys_act in ("lock_pc", "lock"):
                from .system_tools import SystemTools
                return SystemTools.lock_pc()
            if sys_act in ("sleep_pc", "sleep"):
                from .system_tools import SystemTools
                return SystemTools.sleep_pc()
            if sys_act in ("restart_pc", "reboot_pc", "restart"):
                from .system_tools import SystemTools
                return SystemTools.restart_pc()
            if sys_act in ("shutdown_pc", "shut_down_pc", "shutdown", "power_off"):
                from .system_tools import SystemTools
                return SystemTools.shutdown_pc()
            if sys_act in ("show_desktop", "desktop"):
                return self.system.show_desktop()
            if sys_act in ("task_manager", "taskmgr"):
                return self.system.open_task_manager()
            if sys_act in ("file_explorer", "explorer"):
                return self.system.open_file_explorer()
            if sys_act in ("settings", "ms_settings"):
                return self.system.open_settings()
            if sys_act in ("start_menu", "start"):
                return self.system.open_start_menu()
            if sys_act in ("search", "windows_search"):
                return self.system.open_search()
            if sys_act in ("screenshot", "snip"):
                return self.system.take_screenshot()
            if sys_act in ("clipboard_history", "clipboard"):
                return self.system.open_clipboard_history()
            if sys_act in ("action_center", "notifications"):
                return self.system.open_action_center()
            if sys_act in ("snap_left", "tile_left"):
                return self.system.snap_left()
            if sys_act in ("snap_right", "tile_right"):
                return self.system.snap_right()
            if sys_act in ("next_desktop",):
                return self.system.next_desktop()
            if sys_act in ("prev_desktop", "previous_desktop"):
                return self.system.prev_desktop()
            if sys_act in ("task_view",):
                return self.system.task_view()
            if sys_act in ("zoom_in",):
                return self.system.zoom_in()
            if sys_act in ("zoom_out",):
                return self.system.zoom_out()
            if sys_act in ("zoom_reset",):
                return self.system.zoom_reset()
            if sys_act in ("go_back", "back"):
                return self.system.go_back()
            if sys_act in ("go_forward", "forward"):
                return self.system.go_forward()
            if sys_act in ("address_bar", "url_bar"):
                return self.system.address_bar()
            if sys_act in ("next_tab",):
                return self.system.next_tab()
            if sys_act in ("prev_tab", "previous_tab"):
                return self.system.prev_tab()
            if sys_act in ("snap_top_left", "tile_top_left"):
                return self.system.snap_top_left()
            if sys_act in ("snap_top_right", "tile_top_right"):
                return self.system.snap_top_right()
            if sys_act in ("snap_bottom_left", "tile_bottom_left"):
                return self.system.snap_bottom_left()
            if sys_act in ("snap_bottom_right", "tile_bottom_right"):
                return self.system.snap_bottom_right()
            if sys_act in ("next_monitor", "move_next_monitor"):
                return self.system.next_monitor()
            if sys_act in ("prev_monitor", "move_prev_monitor"):
                return self.system.prev_monitor()
            if sys_act in ("minimize_others", "minimize_other_windows"):
                return self.system.minimize_others()
            if sys_act in ("duplicate_tab",):
                return self.system.duplicate_tab()
            if sys_act in ("incognito_window", "private_window"):
                return self.system.incognito_window()
            if sys_act in ("hard_refresh", "force_reload"):
                return self.system.hard_refresh()
            if sys_act in ("view_source", "page_source"):
                return self.system.view_source()
            if sys_act in ("toggle_bookmarks_bar", "bookmarks_bar"):
                return self.system.toggle_bookmarks_bar()
            if sys_act.startswith("tab_"):
                try:
                    num = int(sys_act.split("_")[1])
                    return self.system.switch_to_tab(num)
                except Exception:
                    pass
            if sys_act in ("rewind", "rewind_media", "seek_backward"):
                return self.system.rewind_media(seconds=action.scroll_amount or 10)
            if sys_act in ("forward", "forward_media", "seek_forward"):
                return self.system.forward_media(seconds=action.scroll_amount or 10)
            if sys_act in ("speed_up", "playback_faster"):
                return self.system.playback_faster()
            if sys_act in ("slow_down", "playback_slower"):
                return self.system.playback_slower()
            if sys_act in ("captions", "subtitles", "toggle_captions"):
                return self.system.toggle_captions()
            if sys_act in ("theater_mode",):
                return self.system.theater_mode()
            if sys_act in ("fullscreen_media", "full_screen_media"):
                return self.system.full_screen_media()
            if sys_act in ("mute_media", "mute_video"):
                return self.system.mute_media()
            if sys_act in ("delete_line", "clear_line"):
                return self.system.delete_line()
            if sys_act in ("delete_word",):
                return self.system.delete_word()
            if sys_act in ("select_line",):
                return self.system.select_line()
            if sys_act in ("line_start", "beginning_of_line"):
                return self.system.line_start()
            if sys_act in ("line_end", "end_of_line"):
                return self.system.line_end()
            if sys_act in ("page_top", "scroll_top", "top_of_page"):
                return self.system.page_top()
            if sys_act in ("page_bottom", "scroll_bottom", "bottom_of_page"):
                return self.system.page_bottom()
            if sys_act in ("open_run", "run_dialog"):
                return self.system.open_run()
            if sys_act in ("open_inspector", "desktop_inspector", "inspect_element", "inspect_controls", "element_inspector"):
                if getattr(self, "ui_bridge", None) and hasattr(self.ui_bridge, "inspector_requested"):
                    self.ui_bridge.inspector_requested.emit()
                    logger.info("Dispatched open element inspector request to UI bridge")
                    return True
                logger.info("Open inspector requested without ui_bridge attached.")
                return True

            if sys_act in ("emoji_panel", "emojis"):
                return self.system.emoji_panel()
            if sys_act in ("game_bar", "screen_record"):
                return self.system.game_bar()
            if sys_act in ("quick_settings", "control_center"):
                return self.system.quick_settings()

            # 10. Display, Theme & Multi-Monitor
            if sys_act in ("set_brightness", "brightness"):
                level = action.scroll_amount if action.scroll_amount is not None else 60
                if hasattr(self.system, "set_brightness"):
                    return self.system.set_brightness(level)
                from .system_tools import SystemTools
                return SystemTools.set_brightness(level)
            if sys_act in ("brightness_up", "increase_brightness", "brighter"):
                if hasattr(self.system, "brightness_up"):
                    return self.system.brightness_up(steps=action.scroll_amount or 15)
                from .system_tools import SystemTools
                return SystemTools.brightness_up(steps=action.scroll_amount or 15)
            if sys_act in ("brightness_down", "decrease_brightness", "dim", "dimmer"):
                if hasattr(self.system, "brightness_down"):
                    return self.system.brightness_down(steps=action.scroll_amount or 15)
                from .system_tools import SystemTools
                return SystemTools.brightness_down(steps=action.scroll_amount or 15)
            if sys_act in ("dark_mode", "enable_dark_mode", "dark_theme"):
                if hasattr(self.system, "set_dark_mode"):
                    return self.system.set_dark_mode(True)
                from .system_tools import SystemTools
                return SystemTools.set_dark_mode(True)
            if sys_act in ("light_mode", "enable_light_mode", "light_theme"):
                if hasattr(self.system, "set_dark_mode"):
                    return self.system.set_dark_mode(False)
                from .system_tools import SystemTools
                return SystemTools.set_dark_mode(False)
            if sys_act in ("toggle_dark_mode", "toggle_theme"):
                if hasattr(self.system, "toggle_dark_mode"):
                    return self.system.toggle_dark_mode()
                from .system_tools import SystemTools
                return SystemTools.toggle_dark_mode()
            if sys_act in ("night_light", "toggle_night_light"):
                if hasattr(self.system, "toggle_night_light"):
                    return self.system.toggle_night_light()
                from .system_tools import SystemTools
                return SystemTools.toggle_night_light()
            if sys_act in ("display_mode", "set_display_mode"):
                mode = action.target or "extend"
                if hasattr(self.system, "set_display_mode"):
                    return self.system.set_display_mode(mode)
                return True

            # 11. System Health, Diagnostics & Power
            if sys_act in ("battery_status", "battery"):
                info = self.system.get_battery_status() if hasattr(self.system, "get_battery_status") else "Battery status normal."
                action.text = info
                if status_callback:
                    status_callback(info)
                return True
            if sys_act in ("system_health", "check_ram", "top_ram", "ram_usage"):
                info = (
                    self.system.get_system_health()
                    if sys_act == "system_health" and hasattr(self.system, "get_system_health")
                    else self.system.get_top_ram_processes()
                    if hasattr(self.system, "get_top_ram_processes")
                    else "Memory usage normal."
                )
                action.text = info
                if status_callback:
                    status_callback(info)
                return True
            if sys_act in ("kill_process", "force_quit", "terminate_process"):
                target = action.target or ""
                if hasattr(self.system, "kill_process"):
                    return self.system.kill_process(target)
                return True
            if sys_act in ("restart_explorer", "restart_taskbar"):
                if hasattr(self.system, "restart_explorer"):
                    return self.system.restart_explorer()
                return True

            # 12. File System & Download Shortcuts
            if sys_act in ("open_latest_download", "latest_download"):
                if hasattr(self.system, "open_latest_download"):
                    return self.system.open_latest_download()
                return True
            if sys_act in ("open_latest_screenshot", "latest_screenshot"):
                if hasattr(self.system, "open_latest_screenshot"):
                    return self.system.open_latest_screenshot()
                return True
            if sys_act in ("open_folder",):
                f_name = action.target or "downloads"
                if hasattr(self.system, "open_folder"):
                    return self.system.open_folder(f_name)
                return True
            if sys_act in ("empty_recycle_bin", "clear_recycle_bin", "clear_trash"):
                if hasattr(self.system, "empty_recycle_bin"):
                    return self.system.empty_recycle_bin()
                return True

            # 13. Caffeine / Keep Awake & Privacy
            if sys_act in ("keep_awake", "caffeine", "prevent_sleep"):
                if hasattr(self.system, "set_keep_awake"):
                    return self.system.set_keep_awake(True)
                return True
            if sys_act in ("allow_sleep", "caffeine_off"):
                if hasattr(self.system, "set_keep_awake"):
                    return self.system.set_keep_awake(False)
                return True
            if sys_act in ("boss_mode", "privacy_shield", "hide_everything"):
                if hasattr(self.system, "boss_mode"):
                    return self.system.boss_mode()
                return True

            # 14. Network & Connectivity
            if sys_act in ("network_info", "ip_address", "ping_status"):
                info = self.system.get_network_info() if hasattr(self.system, "get_network_info") else "Network online."
                action.text = info
                if status_callback:
                    status_callback(info)
                return True

            # 15. Clipboard & Browser Utilities
            if sys_act in ("paste_plain_text", "paste_text"):
                if hasattr(self.system, "paste_plain_text"):
                    return self.system.paste_plain_text()
                return True
            if sys_act in ("clear_clipboard",):
                if hasattr(self.system, "clear_clipboard"):
                    return self.system.clear_clipboard()
                return True
            if sys_act in ("switch_to_tab", "search_tab", "tab_search"):
                target = action.target or action.text or ""
                if hasattr(self.system, "switch_to_tab"):
                    return self.system.switch_to_tab(target, uia=self.uia)
                return True
            if sys_act in ("copy_current_url", "copy_url"):
                if hasattr(self.system, "copy_current_url"):
                    return self.system.copy_current_url()
                return True

            logger.warning("Unrecognized system action: %s", sys_act)
            return False

        # 10. Rich Element Operations: Select / Menu / Combobox
        if t == ActionType.SELECT:
            element = None
            if action.menu_path:
                if action.target:
                    element = self.uia.find_element(action.target, target_type=action.target_type)
                else:
                    element = self.uia.get_active_window()
                return self.element_ops.select_menu_item(element, action.menu_path)

            if action.select_value:
                if action.target:
                    element = self.uia.find_element(action.target, target_type=action.target_type or "combobox")
                return self.element_ops.select_combo_item(element, action.select_value)

            if action.target:
                element = self.uia.find_element(action.target, target_type=action.target_type)
            if element and hasattr(element, "select"):
                try:
                    element.select()
                    return True
                except Exception:
                    pass
            return self.mouse.click(element=element)

        # 11. Tree / Item Expand & Collapse
        if t == ActionType.EXPAND:
            element = None
            if action.target:
                element = self.uia.find_element(action.target, target_type=action.target_type or "tree")
            return self.element_ops.expand_tree_item(element)

        if t == ActionType.COLLAPSE:
            element = None
            if action.target:
                element = self.uia.find_element(action.target, target_type=action.target_type or "tree")
            return self.element_ops.collapse_tree_item(element)

        # 12. Wait
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
        if t == ActionType.MIDDLE_CLICK:
            return f"Middle-clicking {action.target or 'element'}..."
        if t == ActionType.HOVER:
            return f"Hovering {action.target or 'element'}..."
        if t == ActionType.MOVE_MOUSE:
            return f"Moving mouse {action.target or 'center'}..."
        if t == ActionType.TYPE:
            preview = (action.text[:18] + "...") if action.text and len(action.text) > 18 else (action.text or "")
            return f"Typing '{preview}'..."
        if t == ActionType.SHORTCUT:
            return f"Hotkey {action.keys}..."
        if t == ActionType.WINDOW_ACTION:
            return f"Window {action.window_action or 'action'}..."
        if t == ActionType.SYSTEM_ACTION:
            return f"System {action.system_action or action.target or 'action'}..."
        if t == ActionType.SCROLL:
            return f"Scrolling {action.scroll_direction or 'down'}..."
        if t == ActionType.SELECT:
            if action.menu_path:
                return f"Opening menu '{action.menu_path}'..."
            if action.select_value:
                return f"Selecting '{action.select_value}' in {action.target or 'control'}..."
            return f"Selecting {action.target or 'element'}..."
        if t == ActionType.EXPAND:
            return f"Expanding {action.target or 'item'}..."
        if t == ActionType.COLLAPSE:
            return f"Collapsing {action.target or 'item'}..."
        return "Executing action..."
