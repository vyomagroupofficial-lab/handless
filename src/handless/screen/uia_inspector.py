"""Windows UI Automation (UIA) Inspector using pywinauto.

Interrogates active Windows desktop applications, enumerating interactive controls
(buttons, text fields, tabs, menus) via native Microsoft UI Automation COM interfaces.
"""

from __future__ import annotations

import contextlib
import io
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import pywinauto
from pywinauto import Application, Desktop

from .chromium_bridge import (
    is_chromium_window,
    partition_browser_elements,
    wake_chromium_accessibility,
)
from .element_matcher import find_best_element_match

logger = logging.getLogger(__name__)

# Map common conversational control types to pywinauto / UIA control_type names
CONTROL_TYPE_MAP: Dict[str, str] = {
    "button": "Button",
    "edit": "Edit",
    "textbox": "Edit",
    "menu": "MenuItem",
    "menuitem": "MenuItem",
    "tab": "TabItem",
    "tabitem": "TabItem",
    "combo": "ComboBox",
    "combobox": "ComboBox",
    "dropdown": "ComboBox",
    "list": "List",
    "listitem": "ListItem",
    "tree": "TreeItem",
    "treeitem": "TreeItem",
    "checkbox": "CheckBox",
    "radio": "RadioButton",
    "radiobutton": "RadioButton",
    "hyperlink": "Hyperlink",
    "link": "Hyperlink",
    "text": "Text",
    "window": "Window",
    "pane": "Pane",
}


class UIAInspector:
    """Queries Windows desktop applications using UI Automation backend."""

    def __init__(self) -> None:
        self.desktop = Desktop(backend="uia")

    def connect_to_app(self, name_or_pid: str | int, timeout: float = 2.0) -> Optional[Any]:
        """Connect to an already running application by process ID, title regex, or path.

        Uses pywinauto.Application(backend="uia").connect(...) for targeted process
        connection, which isolates searches to that application's window tree.
        """
        try:
            app = Application(backend="uia")
            if isinstance(name_or_pid, int):
                app.connect(process=name_or_pid, timeout=timeout)
                logger.info("Connected to app with PID %d", name_or_pid)
                return app

            clean_name = str(name_or_pid).strip()
            # If specified as full path or ends with .exe, try path first
            if clean_name.lower().endswith(".exe") or "\\" in clean_name or "/" in clean_name:
                try:
                    app.connect(path=clean_name, timeout=timeout)
                    logger.info("Connected to app with path '%s'", clean_name)
                    return app
                except Exception:
                    pass

            # Try case-insensitive title regex
            title_pat = f"(?i).*{re.escape(clean_name)}.*"
            app.connect(title_re=title_pat, timeout=timeout)
            logger.info("Connected to app matching title '%s'", clean_name)
            return app
        except Exception as exc:
            logger.debug("Could not connect to app '%s': %s", name_or_pid, exc)
            return None

    def get_active_window(self) -> Optional[Any]:
        """Retrieve the currently focused/active desktop top-level window, ignoring internal VoiceBar."""
        try:
            win = self.desktop.window(active_only=True)
            if win.exists(timeout=0.3):
                title = (win.window_text() or "").strip()
                if "Vyoma Handless" not in title:
                    return win
        except Exception as exc:
            logger.debug("Could not get active window directly: %s", exc)

        # Fallback to win32 foreground window HWND
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                title = win32gui.GetWindowText(hwnd) or ""
                if "Vyoma Handless" not in title and win32gui.IsWindowVisible(hwnd):
                    spec = self.desktop.window(handle=hwnd)
                    if spec.exists(timeout=0.2):
                        return spec
        except Exception as exc:
            logger.debug("HWND-based foreground lookup error: %s", exc)

        # Fallback to top visible non-Handless window on desktop
        try:
            windows = self.desktop.windows(visible_only=True)
            for w in windows:
                try:
                    title = w.window_text() or ""
                    if "Vyoma Handless" in title:
                        continue
                    if w.is_active():
                        return w
                except Exception:
                    continue

            # If none active (e.g. desktop background), return the first substantial visible window
            for w in windows:
                try:
                    title = w.window_text() or ""
                    if not title or "Vyoma Handless" in title or "Program Manager" in title:
                        continue
                    return w
                except Exception:
                    continue
        except Exception as exc:
            logger.error("Failed to list desktop windows: %s", exc)

        return None

    def find_element_targeted(
        self,
        target_name: str,
        target_type: Optional[str] = None,
        auto_id: Optional[str] = None,
        window_spec: Optional[Any] = None,
        timeout: float = 0.3,
    ) -> Optional[Any]:
        """Directly search for an element using WindowSpecification.child_window().

        This avoids walking the entire descendants tree when title, control_type,
        or automation_id can locate the element directly.
        """
        try:
            win = window_spec or self.desktop.window(active_only=True)
            if not hasattr(win, "child_window"):
                return None

            criteria: Dict[str, Any] = {}
            if target_name:
                criteria["title_re"] = f"(?i).*{re.escape(target_name.strip())}.*"
            if target_type:
                mapped_type = CONTROL_TYPE_MAP.get(target_type.strip().lower(), target_type)
                criteria["control_type"] = mapped_type
            if auto_id:
                criteria["auto_id"] = auto_id

            if not criteria:
                return None

            spec = win.child_window(**criteria)
            if spec.exists(timeout=timeout):
                elem = spec.wrapper_object()
                # Guard: If user is looking for a button, contact, or clickable item without explicitly requesting an edit field,
                # do NOT return an Edit field whose typed text happens to match (e.g. search box containing contact name)
                c_type = (elem.friendly_class_name() or "").lower()
                clean_target = re.sub(r"^(?:the|a|an)\s+", "", target_name.strip().lower())
                is_edit_requested = target_type and target_type.lower() in ("edit", "input", "textbox", "searchbox")
                is_query_for_edit = clean_target in ("search", "search box", "search bar", "find", "input", "edit", "address bar", "url", "type a message")
                if c_type in ("edit", "textbox") and not is_edit_requested and not is_query_for_edit:
                    logger.debug("Skipping targeted Edit control for non-edit target '%s'", target_name)
                    return None

                logger.debug("Targeted search found element '%s' via child_window", target_name)
                return elem
        except Exception as exc:
            logger.debug("Targeted child_window lookup failed for '%s': %s", target_name, exc)

        return None

    def find_element(
        self,
        target_name: str,
        target_type: Optional[str] = None,
        search_entire_desktop: bool = False,
        spatial_landmark: Optional[str] = None,
        relative_anchor: Optional[str] = None,
        relative_relation: Optional[str] = None,
    ) -> Optional[Any]:
        """Find an interactive control matching target_name.

        Supports:
        - Fast targeted child_window() search
        - Fuzzy matching over active window descendants
        - Spatial landmark zone matching (top_right, bottom_left, etc.)
        - Relative proximity to anchor elements (near, next to, below, above)
        """
        active_win = self.get_active_window()
        parent_rect = None
        if active_win:
            try:
                parent_rect = active_win.rectangle()
            except Exception:
                pass

        # 1. Fast targeted search in active window (only if no spatial constraints)
        if active_win and not spatial_landmark and not relative_anchor:
            targeted = self.find_element_targeted(target_name, target_type=target_type, window_spec=active_win)
            if targeted:
                return targeted

        # 2. Fuzzy descendant search in active window with spatial landmark & anchor support
        if active_win:
            try:
                candidates = active_win.descendants()
                match = find_best_element_match(
                    target_name,
                    candidates,
                    target_type=target_type,
                    spatial_landmark=spatial_landmark,
                    relative_anchor=relative_anchor,
                    relative_relation=relative_relation,
                    parent_rect=parent_rect,
                )
                if match:
                    _, elem = match
                    return elem
            except Exception as exc:
                logger.debug("Error searching descendants of active window: %s", exc)

        # 3. Fallback to searching entire desktop if requested
        if search_entire_desktop:
            # First try targeted desktop lookup
            try:
                if not spatial_landmark and not relative_anchor:
                    targeted_dt = self.find_element_targeted(target_name, target_type=target_type, window_spec=self.desktop)
                    if targeted_dt:
                        return targeted_dt
            except Exception:
                pass

            try:
                all_candidates = self.desktop.descendants()
                match = find_best_element_match(
                    target_name,
                    all_candidates,
                    target_type=target_type,
                    spatial_landmark=spatial_landmark,
                    relative_anchor=relative_anchor,
                    relative_relation=relative_relation,
                    parent_rect=parent_rect,
                )
                if match:
                    _, elem = match
                    return elem
            except Exception as exc:
                logger.error("Error searching all desktop descendants: %s", exc)

        return None


    def dump_control_tree(self, depth: int = 3, max_lines: int = 150) -> str:
        """Capture the control hierarchy of the active window as a structured string.

        Useful for developer diagnostics (`handless diag`) and vision LLM context prompts.
        Truncates output to max_lines to prevent memory exhaustion on complex trees.
        """
        active_win = self.get_active_window()
        if not active_win:
            return "No active window detected."

        output_str = ""
        # 1. If active_win has print_control_identifiers (WindowSpecification)
        if hasattr(active_win, "print_control_identifiers"):
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    active_win.print_control_identifiers(depth=depth)
                output_str = buf.getvalue()
            except Exception as exc:
                logger.debug("active_win.print_control_identifiers failed: %s", exc)

        # 2. If wrapper handle is available, wrap in WindowSpecification
        if not output_str and hasattr(active_win, "handle"):
            try:
                spec = self.desktop.window(handle=active_win.handle)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    spec.print_control_identifiers(depth=depth)
                output_str = buf.getvalue()
            except Exception as exc:
                logger.debug("Handle-based print_control_identifiers failed: %s", exc)

        # 3. Fallback: manual descendant walk
        if not output_str:
            lines = []
            try:
                win_text = getattr(active_win, "window_text", lambda: "")() or "Window"
                lines.append(f"Root: [{getattr(active_win, 'friendly_class_name', lambda: 'Window')()}] \"{win_text}\"")
                descendants = active_win.descendants()
                for d in descendants[:max_lines]:
                    try:
                        text = d.window_text().strip()
                        ctype = d.friendly_class_name()
                        auto_id = getattr(d, "automation_id", lambda: "")()
                        lines.append(f"  [{ctype}] \"{text}\" (id: {auto_id})")
                    except Exception:
                        continue
                output_str = "\n".join(lines)
            except Exception as exc:
                output_str = f"Error walking control tree: {exc}"

        # Truncate lines if necessary
        all_lines = output_str.strip().splitlines()
        if len(all_lines) > max_lines:
            truncated = all_lines[:max_lines]
            truncated.append(f"... (truncated {len(all_lines) - max_lines} additional elements)")
            output_str = "\n".join(truncated)

        return output_str

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

    def inspect_window_elements(self, window_spec: Optional[Any] = None) -> List[Dict[str, Any]]:
        """Deeply inspect and return structured metadata for all controls in target window.

        Automatically triggers Chromium accessibility engine if target is a browser
        or Electron app, and partitions elements into Browser Shell vs Web DOM ([WEB]).
        """
        if isinstance(window_spec, int):
            win = self.desktop.window(handle=window_spec)
        else:
            win = window_spec or self.get_active_window()

        if not win:
            return []

        # 1. Auto-Wake Chromium UIA Accessibility if browser or Electron app
        win_title = ""
        win_rect = None
        try:
            win_title = (win.window_text() or "").strip()
            win_rect_obj = win.rectangle()
            win_rect = {
                "left": win_rect_obj.left,
                "top": win_rect_obj.top,
                "width": win_rect_obj.width(),
                "height": win_rect_obj.height(),
            }
        except Exception:
            pass

        handle = getattr(win, "handle", None)
        if handle:
            wake_chromium_accessibility(handle)

        results: List[Dict[str, Any]] = []
        try:
            descendants = win.descendants()
            for d in descendants:
                try:
                    name = (d.window_text() or "").strip()
                    if not name:
                        name = (getattr(d.element_info, "name", "") or "").strip()
                    auto_id = getattr(d, "automation_id", lambda: "")() or ""
                    ctype = d.friendly_class_name() or "Control"
                    visible = d.is_visible()
                    enabled = d.is_enabled()
                    rect = d.rectangle()
                    r_dict = {
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom,
                        "width": rect.width(),
                        "height": rect.height(),
                    }
                    results.append({
                        "name": name,
                        "auto_id": auto_id,
                        "control_type": ctype,
                        "is_visible": visible,
                        "is_enabled": enabled,
                        "rect": r_dict,
                        "handle": getattr(d, "handle", None),
                        "wrapper": d,
                    })
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("inspect_window_elements error: %s", exc)

        # 2. Partition browser shell from inside-page web content ([WEB] vs [APP])
        return partition_browser_elements(results, window_title=win_title, window_rect=win_rect)

    def get_element_children(self, wrapper: Any) -> List[Dict[str, Any]]:
        """Return direct children of a specific control wrapper for lazy tree walking."""
        if not wrapper or not hasattr(wrapper, "children"):
            return []

        children_list: List[Dict[str, Any]] = []
        try:
            children = wrapper.children()
            for c in children:
                try:
                    name = (c.window_text() or "").strip()
                    if not name:
                        name = (getattr(c.element_info, "name", "") or "").strip()
                    auto_id = getattr(c, "automation_id", lambda: "")() or ""
                    ctype = c.friendly_class_name() or "Control"
                    visible = c.is_visible()
                    enabled = c.is_enabled()
                    rect = c.rectangle()
                    r_dict = {
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom,
                        "width": rect.width(),
                        "height": rect.height(),
                    }
                    children_list.append({
                        "name": name,
                        "auto_id": auto_id,
                        "control_type": ctype,
                        "is_visible": visible,
                        "is_enabled": enabled,
                        "rect": r_dict,
                        "handle": getattr(c, "handle", None),
                        "wrapper": c,
                    })
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("get_element_children error: %s", exc)

        return children_list

    def inspect_element_at_point(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """Inspect and return metadata for the exact UI element at screen coordinate (x, y)."""
        try:
            elem = self.desktop.from_point(x, y)
            if elem:
                rect = elem.rectangle()
                txt = (elem.window_text() or "").strip()
                if not txt:
                    txt = (getattr(elem.element_info, "name", "") or "").strip()
                return {
                    "name": txt,
                    "auto_id": getattr(elem, "automation_id", lambda: "")() or "",
                    "control_type": elem.friendly_class_name() or "Control",
                    "is_visible": elem.is_visible(),
                    "is_enabled": elem.is_enabled(),
                    "rect": {
                        "left": rect.left,
                        "top": rect.top,
                        "right": rect.right,
                        "bottom": rect.bottom,
                        "width": rect.width(),
                        "height": rect.height(),
                    },
                    "handle": getattr(elem, "handle", None),
                    "wrapper": elem,
                }
        except Exception as exc:
            logger.debug("inspect_element_at_point failed for (%d, %d): %s", x, y, exc)
        return None

    def get_top_level_windows(self) -> List[Dict[str, Any]]:
        """List open top-level application windows for targeting in Element Inspector."""
        windows_list: List[Dict[str, Any]] = []
        try:
            windows = self.desktop.windows(visible_only=True)
            for w in windows:
                try:
                    title = (w.window_text() or "").strip()
                    if not title or "Vyoma Handless" in title or "Program Manager" in title:
                        continue
                    handle = getattr(w, "handle", None)
                    pid = getattr(w, "process_id", lambda: None)()
                    windows_list.append({
                        "title": title,
                        "handle": handle,
                        "pid": pid,
                        "wrapper": w,
                    })
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("Failed to list top-level windows: %s", exc)
        return windows_list

