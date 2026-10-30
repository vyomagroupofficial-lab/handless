"""Window management actions.

Handles focusing, minimizing, maximizing, positioning, centering, popup floating,
splitting, switching, and closing windows or targeted desktop applications.
"""

from __future__ import annotations

import logging
import subprocess
from typing import Any, List, Optional, Tuple
import pyautogui

try:
    import win32gui
    import win32con
    import win32api
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class WindowController:
    """Manages desktop windows, geometry, positioning, and application layouts."""

    def get_work_area(self) -> Tuple[int, int, int, int]:
        """Get the primary monitor work area (left, top, right, bottom), excluding taskbar."""
        if WIN32_AVAILABLE:
            try:
                mon = win32api.MonitorFromPoint((0, 0))
                info = win32api.GetMonitorInfo(mon)
                work = info.get("Work")
                if work and len(work) == 4:
                    return int(work[0]), int(work[1]), int(work[2]), int(work[3])
            except Exception as exc:
                logger.debug("Failed to query monitor work area via win32api: %s", exc)
        return 0, 0, 1920, 1040

    def resolve_window_hwnd(self, target: Optional[str] = None, uia: Optional[Any] = None) -> Optional[int]:
        """Resolve the Windows HWND handle for a target application or the active window."""
        if not WIN32_AVAILABLE:
            return None

        clean_target = target.strip().lower() if target else ""
        is_generic = not clean_target or clean_target in (
            "this", "the", "window", "app", "application", "active", "current", "it", "this window", "this app"
        )

        if not is_generic:
            # 1. Search top-level windows via win32gui
            found_hwnds: List[Tuple[int, str]] = []
            def enum_cb(h, _):
                if win32gui.IsWindow(h) and win32gui.IsWindowVisible(h):
                    t = win32gui.GetWindowText(h)
                    if t and "Vyoma Handless" not in t and "Program Manager" not in t:
                        if clean_target in t.lower():
                            found_hwnds.append((h, t))
            try:
                win32gui.EnumWindows(enum_cb, None)
                if found_hwnds:
                    return found_hwnds[0][0]
            except Exception as exc:
                logger.debug("EnumWindows search failed: %s", exc)

            # 2. Try UIA connect / desktop windows if provided
            if uia:
                try:
                    for w in uia.desktop.windows(visible_only=False):
                        try:
                            txt = w.window_text() or ""
                            if clean_target in txt.lower():
                                handle = getattr(w, "handle", None)
                                if handle:
                                    return int(handle)
                        except Exception:
                            continue
                except Exception:
                    pass

        # Target is generic or not found: resolve currently active / foreground window
        if uia:
            try:
                active_win = uia.get_active_window()
                if active_win:
                    handle = getattr(active_win, "handle", None)
                    if handle:
                        return int(handle)
            except Exception:
                pass

        try:
            fg = win32gui.GetForegroundWindow()
            if fg:
                title = win32gui.GetWindowText(fg)
                if "Vyoma Handless" not in title:
                    return fg
        except Exception:
            pass

        return None

    def close(self, window: Optional[Any] = None) -> bool:
        """Close active or specified window."""
        if window is not None:
            try:
                window.close()
                logger.info("Closed window via UIA handle.")
                return True
            except Exception as exc:
                logger.debug("window.close() failed: %s. Falling back to Alt+F4.", exc)

        # Standard Windows close shortcut
        try:
            pyautogui.hotkey("alt", "f4")
            logger.info("Closed active window via Alt+F4.")
            return True
        except Exception as exc:
            logger.error("Failed to close window: %s", exc)
            return False

    def close_window_or_app(self, target: Optional[str] = None, uia: Optional[Any] = None) -> bool:
        """Close a specific window/application by name, or the active window if no target."""
        if not target or target.lower() in ("this", "active", "current", "window", "app"):
            active_win = uia.get_active_window() if uia else None
            return self.close(active_win)

        clean_target = target.strip()
        logger.info("Attempting to close window/application matching '%s'...", clean_target)

        # 1. Try pywinauto connect to app
        if uia:
            try:
                app = uia.connect_to_app(clean_target, timeout=1.0)
                if app:
                    try:
                        top = app.top_window()
                        top.close()
                        logger.info("Closed top window of '%s' via UIA Application.", clean_target)
                        return True
                    except Exception:
                        pass
            except Exception as exc:
                logger.debug("UIA connect_to_app error: %s", exc)

            # 2. Search visible top-level windows
            try:
                windows = uia.desktop.windows(visible_only=True)
                for w in windows:
                    title = ""
                    try:
                        title = w.window_text()
                    except Exception:
                        continue
                    if clean_target.lower() in title.lower():
                        try:
                            w.close()
                            logger.info("Closed window matching '%s' (title: '%s')", clean_target, title)
                            return True
                        except Exception:
                            try:
                                w.set_focus()
                                pyautogui.hotkey("alt", "f4")
                                return True
                            except Exception:
                                pass
            except Exception as exc:
                logger.debug("Desktop window search error: %s", exc)

        # 3. Graceful taskkill attempt for named process
        try:
            exe_name = clean_target if clean_target.lower().endswith(".exe") else f"{clean_target}.exe"
            res = subprocess.run(["taskkill", "/IM", exe_name], capture_output=True, text=True)
            if res.returncode == 0:
                logger.info("Terminated process '%s' via taskkill.", exe_name)
                return True
        except Exception as exc:
            logger.debug("Taskkill fallback error: %s", exc)

        # 4. Fallback to closing active window
        active_win = uia.get_active_window() if uia else None
        return self.close(active_win)

    def switch_to_app(self, target: Optional[str] = None, uia: Optional[Any] = None) -> bool:
        """Focus a specific application window by name, or Alt+Tab if none given."""
        if not target or target.lower() in ("this", "active", "window"):
            return self.switch_window()

        clean_target = target.strip().lower()
        if uia:
            try:
                windows = uia.desktop.windows(visible_only=True)
                for w in windows:
                    try:
                        title = w.window_text().lower()
                        if clean_target in title:
                            try:
                                if hasattr(w, "is_minimized") and w.is_minimized():
                                    w.restore()
                            except Exception:
                                pass
                            w.set_focus()
                            logger.info("Focused window matching '%s' ('%s')", clean_target, title)
                            return True
                    except Exception:
                        continue
            except Exception as exc:
                logger.debug("Error focusing window '%s': %s", clean_target, exc)

        return False

    def minimize(self, target: Optional[str] = None, uia: Optional[Any] = None) -> bool:
        """Minimize active window or specified window."""
        hwnd = self.resolve_window_hwnd(target, uia) if target else None
        if hwnd and WIN32_AVAILABLE:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                logger.info("Minimized window HWND %d via SW_MINIMIZE", hwnd)
                return True
            except Exception as exc:
                logger.debug("win32gui.ShowWindow SW_MINIMIZE error: %s", exc)

        window = None
        if target and uia:
            try:
                for w in uia.desktop.windows(visible_only=True):
                    if target.lower() in (w.window_text() or "").lower():
                        window = w
                        break
            except Exception:
                pass

        if window is None and uia:
            window = uia.get_active_window()

        if window is not None:
            try:
                window.minimize()
                return True
            except Exception:
                pass

        try:
            pyautogui.hotkey("win", "down")
            return True
        except Exception as exc:
            logger.error("Failed to minimize window: %s", exc)
            return False

    def maximize(self, target: Optional[str] = None, uia: Optional[Any] = None) -> bool:
        """Maximize active window or specified window."""
        hwnd = self.resolve_window_hwnd(target, uia) if target else None
        if hwnd and WIN32_AVAILABLE:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass
                logger.info("Maximized window HWND %d via SW_MAXIMIZE", hwnd)
                return True
            except Exception as exc:
                logger.debug("win32gui.ShowWindow SW_MAXIMIZE error: %s", exc)

        window = None
        if target and uia:
            try:
                for w in uia.desktop.windows(visible_only=True):
                    if target.lower() in (w.window_text() or "").lower():
                        window = w
                        break
            except Exception:
                pass

        if window is None and uia:
            window = uia.get_active_window()

        if window is not None:
            try:
                window.maximize()
                return True
            except Exception:
                pass

        try:
            pyautogui.hotkey("win", "up")
            return True
        except Exception as exc:
            logger.error("Failed to maximize window: %s", exc)
            return False

    def restore(self, target: Optional[str] = None, uia: Optional[Any] = None) -> bool:
        """Restore active or specified window from minimized or maximized state."""
        hwnd = self.resolve_window_hwnd(target, uia)
        if hwnd and WIN32_AVAILABLE:
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                try:
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass
                logger.info("Restored window HWND %d via SW_RESTORE", hwnd)
                return True
            except Exception as exc:
                logger.debug("SW_RESTORE failed for HWND %d: %s", hwnd, exc)

        if uia and target:
            try:
                for w in uia.desktop.windows(visible_only=False):
                    if target.lower() in (w.window_text() or "").lower():
                        w.restore()
                        return True
            except Exception:
                pass

        return False

    def center_window(
        self,
        target: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        uia: Optional[Any] = None,
    ) -> bool:
        """Center the active or specified window on the desktop work area."""
        hwnd = self.resolve_window_hwnd(target, uia)
        if not hwnd or not WIN32_AVAILABLE:
            logger.warning("Could not resolve window HWND to center")
            return False

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

            work_l, work_t, work_r, work_b = self.get_work_area()
            work_w = work_r - work_l
            work_h = work_b - work_t

            w = width
            h = height
            if w is None or h is None:
                try:
                    rect = win32gui.GetWindowRect(hwnd)
                    cur_w = rect[2] - rect[0]
                    cur_h = rect[3] - rect[1]
                    if cur_w >= 300 and cur_h >= 200 and cur_w < work_w and cur_h < work_h:
                        w = w or cur_w
                        h = h or cur_h
                except Exception:
                    pass

            w = w or int(work_w * 0.72)
            h = h or int(work_h * 0.75)

            w = min(w, work_w)
            h = min(h, work_h)

            x = work_l + (work_w - w) // 2
            y = work_t + (work_h - h) // 2

            win32gui.MoveWindow(hwnd, x, y, w, h, True)
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
            logger.info("Centered window HWND %d at (%d, %d, %d, %d)", hwnd, x, y, w, h)
            return True
        except Exception as exc:
            logger.error("Failed to center window: %s", exc)
            return False

    def make_popup_window(
        self,
        target: Optional[str] = None,
        width: int = 780,
        height: int = 520,
        uia: Optional[Any] = None,
    ) -> bool:
        """Resize active or specified window into a compact floating popup window and center it."""
        hwnd = self.resolve_window_hwnd(target, uia)
        if not hwnd or not WIN32_AVAILABLE:
            logger.warning("Could not resolve window HWND for popup mode")
            return False

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            work_l, work_t, work_r, work_b = self.get_work_area()
            work_w = work_r - work_l
            work_h = work_b - work_t

            w = min(width, work_w - 40)
            h = min(height, work_h - 40)
            x = work_l + (work_w - w) // 2
            y = work_t + (work_h - h) // 2

            win32gui.MoveWindow(hwnd, x, y, w, h, True)
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
            logger.info("Created popup window HWND %d size (%d, %d) at (%d, %d)", hwnd, w, h, x, y)
            return True
        except Exception as exc:
            logger.error("Failed to make popup window: %s", exc)
            return False

    def position_window(
        self,
        position: str,
        target: Optional[str] = None,
        uia: Optional[Any] = None,
    ) -> bool:
        """Position active or specified window to a specific screen region or quadrant.

        Supported positions:
        - 'left', 'snap_left': Left half
        - 'right', 'snap_right': Right half
        - 'top', 'top_half': Top half
        - 'bottom', 'bottom_half', 'down': Bottom half
        - 'top_left', 'left_top': Top-left quadrant
        - 'top_right', 'right_top': Top-right quadrant
        - 'bottom_left', 'left_bottom': Bottom-left quadrant
        - 'bottom_right', 'right_bottom': Bottom-right quadrant
        - 'center': Centered on screen
        - 'popup': Compact centered popup
        """
        pos = position.strip().lower().replace("-", "_").replace(" ", "_")
        if pos == "center":
            return self.center_window(target=target, uia=uia)
        if pos in ("popup", "small_popup", "float"):
            return self.make_popup_window(target=target, uia=uia)

        hwnd = self.resolve_window_hwnd(target, uia)
        if not hwnd or not WIN32_AVAILABLE:
            if pos in ("left", "snap_left"):
                pyautogui.hotkey("win", "left")
                return True
            if pos in ("right", "snap_right"):
                pyautogui.hotkey("win", "right")
                return True
            if pos in ("top_left", "left_top"):
                pyautogui.hotkey("win", "left")
                pyautogui.hotkey("win", "up")
                return True
            if pos in ("top_right", "right_top"):
                pyautogui.hotkey("win", "right")
                pyautogui.hotkey("win", "up")
                return True
            if pos in ("bottom_left", "left_bottom"):
                pyautogui.hotkey("win", "left")
                pyautogui.hotkey("win", "down")
                return True
            if pos in ("bottom_right", "right_bottom"):
                pyautogui.hotkey("win", "right")
                pyautogui.hotkey("win", "down")
                return True
            return False

        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            work_l, work_t, work_r, work_b = self.get_work_area()
            work_w = work_r - work_l
            work_h = work_b - work_t

            half_w = work_w // 2
            half_h = work_h // 2
            rem_w = work_w - half_w
            rem_h = work_h - half_h

            if pos in ("left", "snap_left"):
                x, y, w, h = work_l, work_t, half_w, work_h
            elif pos in ("right", "snap_right"):
                x, y, w, h = work_l + half_w, work_t, rem_w, work_h
            elif pos in ("top", "top_half"):
                x, y, w, h = work_l, work_t, work_w, half_h
            elif pos in ("bottom", "bottom_half", "down"):
                x, y, w, h = work_l, work_t + half_h, work_w, rem_h
            elif pos in ("top_left", "left_top"):
                x, y, w, h = work_l, work_t, half_w, half_h
            elif pos in ("top_right", "right_top"):
                x, y, w, h = work_l + half_w, work_t, rem_w, half_h
            elif pos in ("bottom_left", "left_bottom"):
                x, y, w, h = work_l, work_t + half_h, half_w, rem_h
            elif pos in ("bottom_right", "right_bottom"):
                x, y, w, h = work_l + half_w, work_t + half_h, rem_w, rem_h
            else:
                logger.warning("Unrecognized window position '%s'", pos)
                return False

            win32gui.MoveWindow(hwnd, x, y, w, h, True)
            try:
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
            logger.info("Positioned window HWND %d to '%s' (%d, %d, %d, %d)", hwnd, pos, x, y, w, h)
            return True
        except Exception as exc:
            logger.error("Failed to position window to '%s': %s", pos, exc)
            return False

    def layout_two_apps(
        self,
        app1: str,
        app2: str,
        layout: str = "side_by_side",
        uia: Optional[Any] = None,
    ) -> bool:
        """Position two applications relative to each other (e.g. side-by-side or stacked).

        Layout types:
        - 'side_by_side' / 'left_right': app1 on left half, app2 on right half
        - 'right_left': app1 on right half, app2 on left half
        - 'top_bottom' / 'stacked': app1 on top half, app2 on bottom half
        - 'bottom_top': app1 on bottom half, app2 on top half
        - 'left_quadrants': app1 on top-left, app2 on bottom-left
        - 'right_quadrants': app1 on top-right, app2 on bottom-right
        """
        clean_layout = layout.strip().lower().replace("-", "_")

        pos_map = {
            "side_by_side": ("left", "right"),
            "left_right": ("left", "right"),
            "right_left": ("right", "left"),
            "top_bottom": ("top", "bottom"),
            "stacked": ("top", "bottom"),
            "bottom_top": ("bottom", "top"),
            "left_quadrants": ("top_left", "bottom_left"),
            "right_quadrants": ("top_right", "bottom_right"),
        }
        p1, p2 = pos_map.get(clean_layout, ("left", "right"))

        res1 = self.position_window(p1, target=app1, uia=uia)
        res2 = self.position_window(p2, target=app2, uia=uia)
        logger.info(
            "Coordinated two-app layout '%s' for '%s' (%s) and '%s' (%s) -> %s, %s",
            clean_layout, app1, p1, app2, p2, res1, res2,
        )
        return res1 or res2

    def switch_window(self) -> bool:
        """Switch to previous/next application window."""
        try:
            pyautogui.hotkey("alt", "tab")
            return True
        except Exception as exc:
            logger.error("Failed to switch window: %s", exc)
            return False
