"""Chromium & Browser Deep Tracking Bridge.

Provides:
1. Auto-Wake Chromium UIA Accessibility:
   Sends the Windows WM_GETOBJECT / AccessibleObjectFromWindow handshake to Chromium
   top-level windows (Chrome_WidgetWin_1) and child renderers (Chrome_RenderWidgetHostHWND).
   This wakes Chromium's dormant accessibility engine, forcing Chrome, Edge, Brave,
   and Electron apps (WhatsApp Desktop, Slack, Discord, VS Code, Spotify) to expose
   every web DOM button, search field, chat item, and link as native UIA nodes.

2. Browser Chrome vs. Page Content Partitioning:
   Automatically partitions elements into "Browser Shell" (tabs, address bar, bookmarks)
   and "Web Content" (DOM inside the web page canvas, e.g. WhatsApp Web chats), tagging
   them with clear visual metadata ([WEB] vs [APP]).
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Standard GUID and constants for oleacc.dll
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", wintypes.BYTE * 8),
    ]

# IID_IAccessible: {618736E0-3C3D-11CF-810C-00AA00389B71}
IID_IAccessible = GUID(
    0x618736E0,
    0x3C3D,
    0x11CF,
    (wintypes.BYTE * 8)(0x81, 0x0C, 0x00, 0xAA, 0x00, 0x38, 0x9B, 0x71),
)

OBJID_CLIENT = 0xFFFFFFFC  # -4
WM_GETOBJECT = 0x003D

# Known Chromium and Electron executable names (case-insensitive)
CHROMIUM_PROCESS_NAMES: Set[str] = {
    "chrome.exe",
    "msedge.exe",
    "brave.exe",
    "vivaldi.exe",
    "opera.exe",
    "slack.exe",
    "discord.exe",
    "whatsapp.exe",
    "code.exe",
    "spotify.exe",
    "notion.exe",
    "teams.exe",
    "telegram.exe",
}

# Known Chromium window class patterns
CHROMIUM_WINDOW_CLASSES: Tuple[str, ...] = (
    "Chrome_WidgetWin_1",
    "Chrome_WidgetWin_0",
    "Chrome_RenderWidgetHostHWND",
    "Intermediate D3D Window",
)


def is_chromium_window(hwnd: int) -> bool:
    """Check if an HWND belongs to a Chromium-based browser or Electron application."""
    if not hwnd or hwnd <= 0:
        return False

    try:
        import win32api
        import win32con
        import win32gui
        import win32process

        # 1. Check window class name
        class_name = win32gui.GetClassName(hwnd)
        for pattern in CHROMIUM_WINDOW_CLASSES:
            if pattern in class_name:
                return True

        # 2. Check process executable name via pywin32
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid:
            try:
                hproc = win32api.OpenProcess(
                    win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                    False,
                    pid,
                )
                if hproc:
                    exe_path = win32process.GetModuleFileNameEx(hproc, 0)
                    win32api.CloseHandle(hproc)
                    exe_name = os.path.basename(exe_path).lower()
                    if exe_name in CHROMIUM_PROCESS_NAMES:
                        return True
            except Exception:
                pass
    except Exception as exc:
        logger.debug("is_chromium_window check failed for hwnd %s: %s", hwnd, exc)

    return False


def get_chromium_render_hwnds(top_hwnd: int) -> List[int]:
    """Find all Chrome_RenderWidgetHostHWND child windows within a top-level window."""
    render_hwnds: List[int] = []
    if not top_hwnd or top_hwnd <= 0:
        return render_hwnds

    try:
        import win32gui

        def _enum_child(hwnd: int, extra: Any) -> bool:
            try:
                cls_name = win32gui.GetClassName(hwnd)
                if "Chrome_RenderWidgetHostHWND" in cls_name:
                    render_hwnds.append(hwnd)
            except Exception:
                pass
            return True

        win32gui.EnumChildWindows(top_hwnd, _enum_child, None)
    except Exception as exc:
        logger.debug("EnumChildWindows error for hwnd %s: %s", top_hwnd, exc)

    return render_hwnds


def wake_chromium_accessibility(hwnd_or_spec: Any) -> bool:
    """Trigger Chromium accessibility engine via Windows WM_GETOBJECT / oleacc handshake.

    Sends AccessibleObjectFromWindow(hwnd, OBJID_CLIENT) to both the top-level window
    and child Chrome_RenderWidgetHostHWND renderers. This prompts Chromium to build
    its internal BrowserAccessibilityManager and publish full DOM trees to UI Automation.
    """
    hwnd = None
    if isinstance(hwnd_or_spec, int):
        hwnd = hwnd_or_spec
    elif hasattr(hwnd_or_spec, "handle"):
        hwnd = getattr(hwnd_or_spec, "handle", None)

    if not hwnd:
        return False

    awakened = False
    try:
        oleacc = ctypes.windll.oleacc
        AccessibleObjectFromWindow = oleacc.AccessibleObjectFromWindow
        AccessibleObjectFromWindow.argtypes = [
            wintypes.HWND,
            wintypes.DWORD,
            ctypes.POINTER(GUID),
            ctypes.POINTER(ctypes.c_void_p),
        ]
        AccessibleObjectFromWindow.restype = ctypes.HRESULT

        targets = [hwnd]
        # Include any child render canvases (Chrome_RenderWidgetHostHWND)
        child_renders = get_chromium_render_hwnds(hwnd)
        targets.extend(child_renders)

        for target_hwnd in targets:
            try:
                ptr = ctypes.c_void_p()
                hr = AccessibleObjectFromWindow(
                    target_hwnd,
                    OBJID_CLIENT,
                    ctypes.byref(IID_IAccessible),
                    ctypes.byref(ptr),
                )
                if hr == 0 and ptr.value:
                    awakened = True
                    # Release COM interface pointer
                    try:
                        ctypes.windll.ole32.CoTaskMemFree(ptr)
                    except Exception:
                        pass
            except Exception as e:
                logger.debug("AccessibleObjectFromWindow failed on HWND %s: %s", target_hwnd, e)

        if awakened:
            logger.info("Successfully awakened Chromium UIA accessibility for HWND %s (targets: %d)", hwnd, len(targets))
    except Exception as exc:
        logger.debug("wake_chromium_accessibility failed: %s", exc)

    return awakened


def partition_browser_elements(
    elements: List[Dict[str, Any]],
    window_title: str = "",
    window_rect: Optional[Dict[str, int]] = None,
) -> List[Dict[str, Any]]:
    """Partition UI elements into Browser Shell vs Inside-Page Web Content.

    Distinguishes native browser chrome controls (Tabs, Omnibox address bar, Bookmarks)
    from inside-page DOM elements (WhatsApp chats, web search fields, article text, submit buttons).

    Enriches each element dictionary with:
    - is_web_content: bool (True for webpage DOM nodes, False for app shell)
    - source_tag: str ("[WEB]" or "[APP]")
    - category: str ("web_dom", "browser_shell", or "native_desktop")
    """
    is_browser = False
    lower_title = (window_title or "").lower()
    if any(k in lower_title for k in ("chrome", "edge", "brave", "opera", "vivaldi", "firefox", "browser", "whatsapp")):
        is_browser = True

    # Approximate dividing boundary between browser shell (tabs + omnibox) and webpage canvas
    # The browser top toolbar is typically the upper ~85-125 pixels of the browser window.
    toolbar_cutoff_y = 120
    if window_rect:
        toolbar_cutoff_y = window_rect.get("top", 0) + 120

    partitioned: List[Dict[str, Any]] = []
    for elem in elements:
        copied = dict(elem)
        name = copied.get("name", "")
        ctype = copied.get("control_type", "")
        rect = copied.get("rect", {})
        top_y = rect.get("top", 0)

        # Check heuristics for Web Content
        is_web = False
        if is_browser:
            # Elements below toolbar cutoff, or elements with web ARIA roles / inside document panes
            is_toolbar_control = any(
                term in name.lower() for term in (
                    "address and search bar",
                    "omnibox",
                    "reload",
                    "back",
                    "forward",
                    "extensions",
                    "tab",
                    "minimize",
                    "maximize",
                    "close",
                    "app menu",
                )
            ) and top_y < toolbar_cutoff_y

            if not is_toolbar_control and top_y >= (toolbar_cutoff_y - 30):
                is_web = True
            elif ctype in ("Hyperlink", "Document", "Heading", "Table", "ListItem") and not is_toolbar_control:
                is_web = True

        copied["is_web_content"] = is_web
        if is_web:
            copied["source_tag"] = "[WEB]"
            copied["category"] = "web_dom"
        elif is_browser:
            copied["source_tag"] = "[SHELL]"
            copied["category"] = "browser_shell"
        else:
            copied["source_tag"] = "[APP]"
            copied["category"] = "native_desktop"

        partitioned.append(copied)

    return partitioned
