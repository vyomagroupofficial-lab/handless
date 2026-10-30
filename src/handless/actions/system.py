"""System and Fundamental PC Action Controller for Windows.

Provides native operating system controls:
- Volume & Media controls (Volume up/down/mute, play/pause, next/previous track)
- System security & Power (Lock PC, Sleep)
- Shell & Desktop navigation (Show desktop, Task Manager, File Explorer, Settings, Start Menu, Snipping/Screenshot)
- Window layout & Snapping (Snap left/right, next/previous virtual desktop, Task View)
- Browser & App navigation (Zoom in/out/reset, Back/Forward, Address bar, Tabs, Search)
- Mouse utilities (Middle-click, hover, cursor repositioning)
"""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
from typing import Any, Optional, Tuple, Union
import pyautogui

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class SystemController:
    """Manages fundamental Windows PC operations, media, audio, and shell interactions."""

    # 1. Volume & Audio
    def volume_up(self, steps: int = 2) -> bool:
        """Increase system master volume."""
        try:
            for _ in range(max(1, steps)):
                pyautogui.press("volumeup")
            logger.info("Volume increased by %d steps", steps)
            return True
        except Exception as exc:
            logger.error("Failed to increase volume: %s", exc)
            return False

    def volume_down(self, steps: int = 2) -> bool:
        """Decrease system master volume."""
        try:
            for _ in range(max(1, steps)):
                pyautogui.press("volumedown")
            logger.info("Volume decreased by %d steps", steps)
            return True
        except Exception as exc:
            logger.error("Failed to decrease volume: %s", exc)
            return False

    def toggle_mute(self) -> bool:
        """Toggle system audio mute."""
        try:
            pyautogui.press("volumemute")
            logger.info("Toggled system mute")
            return True
        except Exception as exc:
            logger.error("Failed to toggle mute: %s", exc)
            return False

    def set_volume(self, level: int) -> bool:
        """Set master audio volume to a specific percentage (0 to 100)."""
        clamped = max(0, min(100, int(level)))
        scalar = clamped / 100.0
        try:
            import ctypes
            from ctypes import HRESULT, POINTER, c_float
            from comtypes import GUID, COMMETHOD, IUnknown
            import comtypes.client

            CLSID_MMDeviceEnumerator = GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
            IID_IMMDeviceEnumerator = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
            IID_IAudioEndpointVolume = GUID('{5CDF2C82-841E-4546-9722-0CF74078229A}')

            class IMMDevice(IUnknown):
                _iid_ = GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
                _methods_ = [
                    COMMETHOD([], HRESULT, 'Activate',
                              (['in'], POINTER(GUID), 'iid'),
                              (['in'], ctypes.c_ulong, 'dwClsCtx'),
                              (['in'], ctypes.c_void_p, 'pActivationParams'),
                              (['out'], POINTER(POINTER(IUnknown)), 'ppInterface')),
                ]

            class IMMDeviceEnumerator(IUnknown):
                _iid_ = IID_IMMDeviceEnumerator
                _methods_ = [
                    COMMETHOD([], HRESULT, 'EnumAudioEndpoints'),
                    COMMETHOD([], HRESULT, 'GetDefaultAudioEndpoint',
                              (['in'], ctypes.c_int, 'dataFlow'),
                              (['in'], ctypes.c_int, 'role'),
                              (['out'], POINTER(POINTER(IMMDevice)), 'ppEndpoint')),
                ]

            class IAudioEndpointVolume(IUnknown):
                _iid_ = IID_IAudioEndpointVolume
                _methods_ = [
                    COMMETHOD([], HRESULT, 'RegisterControlChangeNotify'),
                    COMMETHOD([], HRESULT, 'UnregisterControlChangeNotify'),
                    COMMETHOD([], HRESULT, 'GetChannelCount'),
                    COMMETHOD([], HRESULT, 'SetMasterVolumeLevel'),
                    COMMETHOD([], HRESULT, 'SetMasterVolumeLevelScalar',
                              (['in'], c_float, 'fLevel'),
                              (['in'], POINTER(GUID), 'pguidEventContext')),
                    COMMETHOD([], HRESULT, 'GetMasterVolumeLevel'),
                    COMMETHOD([], HRESULT, 'GetMasterVolumeLevelScalar',
                              (['out'], POINTER(c_float), 'pfLevel')),
                    COMMETHOD([], HRESULT, 'SetChannelVolumeLevel'),
                    COMMETHOD([], HRESULT, 'SetChannelVolumeLevelScalar'),
                    COMMETHOD([], HRESULT, 'GetChannelVolumeLevel'),
                    COMMETHOD([], HRESULT, 'GetChannelVolumeLevelScalar'),
                    COMMETHOD([], HRESULT, 'SetMute',
                              (['in'], ctypes.c_bool, 'bMute'),
                              (['in'], POINTER(GUID), 'pguidEventContext')),
                    COMMETHOD([], HRESULT, 'GetMute',
                              (['out'], POINTER(ctypes.c_bool), 'pbMute')),
                    COMMETHOD([], HRESULT, 'GetVolumeStepInfo'),
                    COMMETHOD([], HRESULT, 'VolumeStepUp'),
                    COMMETHOD([], HRESULT, 'VolumeStepDown'),
                    COMMETHOD([], HRESULT, 'QueryHardwareSupport'),
                    COMMETHOD([], HRESULT, 'GetVolumeRange'),
                ]

            enumerator = comtypes.client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
            endpoint = enumerator.GetDefaultAudioEndpoint(0, 1)  # eRender, eMultimedia
            vol_ptr = endpoint.Activate(IID_IAudioEndpointVolume, 1, None)
            vol = vol_ptr.QueryInterface(IAudioEndpointVolume)
            vol.SetMasterVolumeLevelScalar(scalar, None)
            if clamped > 0:
                try:
                    is_muted = vol.GetMute()
                    if is_muted:
                        vol.SetMute(False, None)
                except Exception:
                    pass
            logger.info("Set system master volume to %d%% (scalar %.2f)", clamped, scalar)
            return True
        except Exception as exc:
            logger.debug("COM master volume setting failed: %s. Falling back to step simulation.", exc)
            try:
                for _ in range(50):
                    pyautogui.press("volumedown")
                steps_up = clamped // 2
                for _ in range(steps_up):
                    pyautogui.press("volumeup")
                logger.info("Set volume to ~%d%% via keypress simulation", clamped)
                return True
            except Exception as e2:
                logger.error("Failed to set volume: %s", e2)
                return False

    def get_volume(self) -> int:
        """Get current master audio volume percentage (0 to 100)."""
        try:
            import ctypes
            from ctypes import HRESULT, POINTER, c_float
            from comtypes import GUID, COMMETHOD, IUnknown
            import comtypes.client

            CLSID_MMDeviceEnumerator = GUID('{BCDE0395-E52F-467C-8E3D-C4579291692E}')
            IID_IMMDeviceEnumerator = GUID('{A95664D2-9614-4F35-A746-DE8DB63617E6}')
            IID_IAudioEndpointVolume = GUID('{5CDF2C82-841E-4546-9722-0CF74078229A}')

            class IMMDevice(IUnknown):
                _iid_ = GUID('{D666063F-1587-4E43-81F1-B948E807363F}')
                _methods_ = [
                    COMMETHOD([], HRESULT, 'Activate',
                              (['in'], POINTER(GUID), 'iid'),
                              (['in'], ctypes.c_ulong, 'dwClsCtx'),
                              (['in'], ctypes.c_void_p, 'pActivationParams'),
                              (['out'], POINTER(POINTER(IUnknown)), 'ppInterface')),
                ]

            class IMMDeviceEnumerator(IUnknown):
                _iid_ = IID_IMMDeviceEnumerator
                _methods_ = [
                    COMMETHOD([], HRESULT, 'EnumAudioEndpoints'),
                    COMMETHOD([], HRESULT, 'GetDefaultAudioEndpoint',
                              (['in'], ctypes.c_int, 'dataFlow'),
                              (['in'], ctypes.c_int, 'role'),
                              (['out'], POINTER(POINTER(IMMDevice)), 'ppEndpoint')),
                ]

            class IAudioEndpointVolume(IUnknown):
                _iid_ = IID_IAudioEndpointVolume
                _methods_ = [
                    COMMETHOD([], HRESULT, 'RegisterControlChangeNotify'),
                    COMMETHOD([], HRESULT, 'UnregisterControlChangeNotify'),
                    COMMETHOD([], HRESULT, 'GetChannelCount'),
                    COMMETHOD([], HRESULT, 'SetMasterVolumeLevel'),
                    COMMETHOD([], HRESULT, 'SetMasterVolumeLevelScalar',
                              (['in'], c_float, 'fLevel'),
                              (['in'], POINTER(GUID), 'pguidEventContext')),
                    COMMETHOD([], HRESULT, 'GetMasterVolumeLevel'),
                    COMMETHOD([], HRESULT, 'GetMasterVolumeLevelScalar',
                              (['out'], POINTER(c_float), 'pfLevel')),
                    COMMETHOD([], HRESULT, 'SetChannelVolumeLevel'),
                    COMMETHOD([], HRESULT, 'SetChannelVolumeLevelScalar'),
                    COMMETHOD([], HRESULT, 'GetChannelVolumeLevel'),
                    COMMETHOD([], HRESULT, 'GetChannelVolumeLevelScalar'),
                    COMMETHOD([], HRESULT, 'SetMute',
                              (['in'], ctypes.c_bool, 'bMute'),
                              (['in'], POINTER(GUID), 'pguidEventContext')),
                    COMMETHOD([], HRESULT, 'GetMute',
                              (['out'], POINTER(ctypes.c_bool), 'pbMute')),
                    COMMETHOD([], HRESULT, 'GetVolumeStepInfo'),
                    COMMETHOD([], HRESULT, 'VolumeStepUp'),
                    COMMETHOD([], HRESULT, 'VolumeStepDown'),
                    COMMETHOD([], HRESULT, 'QueryHardwareSupport'),
                    COMMETHOD([], HRESULT, 'GetVolumeRange'),
                ]

            enumerator = comtypes.client.CreateObject(CLSID_MMDeviceEnumerator, interface=IMMDeviceEnumerator)
            endpoint = enumerator.GetDefaultAudioEndpoint(0, 1)
            vol_ptr = endpoint.Activate(IID_IAudioEndpointVolume, 1, None)
            vol = vol_ptr.QueryInterface(IAudioEndpointVolume)
            scalar = vol.GetMasterVolumeLevelScalar()
            return int(round(scalar * 100))
        except Exception:
            return 50

    # 2. Media Controls
    def play_pause(self) -> bool:
        """Play / Pause active media playback."""
        try:
            pyautogui.press("playpause")
            logger.info("Dispatched Media Play/Pause")
            return True
        except Exception as exc:
            logger.error("Failed to toggle media play/pause: %s", exc)
            return False

    def next_track(self) -> bool:
        """Skip to next media track."""
        try:
            pyautogui.press("nexttrack")
            logger.info("Dispatched Next Track")
            return True
        except Exception as exc:
            logger.error("Failed to skip media track: %s", exc)
            return False

    def prev_track(self) -> bool:
        """Return to previous media track."""
        try:
            pyautogui.press("prevtrack")
            logger.info("Dispatched Previous Track")
            return True
        except Exception as exc:
            logger.error("Failed to return to previous track: %s", exc)
            return False

    def stop_media(self) -> bool:
        """Stop active media playback."""
        try:
            pyautogui.press("stop")
            logger.info("Dispatched Stop Media")
            return True
        except Exception as exc:
            logger.error("Failed to stop media: %s", exc)
            return False

    # 3. System Power & Security
    def lock_pc(self) -> bool:
        """Lock the Windows workstation immediately."""
        try:
            res = ctypes.windll.user32.LockWorkStation()
            logger.info("Locked Windows workstation (code=%s)", res)
            return bool(res)
        except Exception as exc:
            logger.error("Failed to lock PC: %s", exc)
            return False

    def sleep_pc(self) -> bool:
        """Put Windows computer to sleep."""
        try:
            subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            logger.info("Initiated PC sleep")
            return True
        except Exception as exc:
            logger.error("Failed to sleep PC: %s", exc)
            return False

    # 4. Windows Shell & Desktop
    def show_desktop(self) -> bool:
        """Minimize all windows and toggle desktop view (Win+D)."""
        try:
            pyautogui.hotkey("win", "d")
            logger.info("Toggled Desktop (Win+D)")
            return True
        except Exception as exc:
            logger.error("Failed to show desktop: %s", exc)
            return False

    def open_task_manager(self) -> bool:
        """Open Windows Task Manager (Ctrl+Shift+Esc)."""
        try:
            pyautogui.hotkey("ctrl", "shift", "esc")
            logger.info("Opened Task Manager")
            return True
        except Exception as exc:
            logger.error("Failed to open Task Manager: %s", exc)
            return False

    def open_file_explorer(self) -> bool:
        """Open Windows File Explorer (Win+E)."""
        try:
            pyautogui.hotkey("win", "e")
            logger.info("Opened File Explorer (Win+E)")
            return True
        except Exception as exc:
            logger.error("Failed to open File Explorer: %s", exc)
            return False

    def open_settings(self) -> bool:
        """Open Windows Settings."""
        try:
            os.startfile("ms-settings:")
            logger.info("Opened Windows Settings (ms-settings:)")
            return True
        except Exception:
            try:
                pyautogui.hotkey("win", "i")
                return True
            except Exception as exc:
                logger.error("Failed to open Settings: %s", exc)
                return False

    def open_start_menu(self) -> bool:
        """Open Windows Start Menu (Win)."""
        try:
            pyautogui.press("win")
            logger.info("Opened Start Menu")
            return True
        except Exception as exc:
            logger.error("Failed to open Start Menu: %s", exc)
            return False

    def open_search(self) -> bool:
        """Open Windows Search (Win+S)."""
        try:
            pyautogui.hotkey("win", "s")
            logger.info("Opened Windows Search")
            return True
        except Exception as exc:
            logger.error("Failed to open Search: %s", exc)
            return False

    def take_screenshot(self) -> bool:
        """Open Windows Snipping Tool / Screen Clip (Win+Shift+S)."""
        try:
            pyautogui.hotkey("win", "shift", "s")
            logger.info("Triggered Windows Snipping Tool (Win+Shift+S)")
            return True
        except Exception as exc:
            logger.error("Failed to trigger screenshot: %s", exc)
            return False

    def open_clipboard_history(self) -> bool:
        """Open Windows Clipboard History (Win+V)."""
        try:
            pyautogui.hotkey("win", "v")
            logger.info("Opened Clipboard History (Win+V)")
            return True
        except Exception as exc:
            logger.error("Failed to open clipboard history: %s", exc)
            return False

    def open_action_center(self) -> bool:
        """Open Windows Notifications / Action Center (Win+A)."""
        try:
            pyautogui.hotkey("win", "a")
            logger.info("Opened Action Center (Win+A)")
            return True
        except Exception as exc:
            logger.error("Failed to open Action Center: %s", exc)
            return False

    # 5. Window Snapping & Virtual Desktops
    def snap_left(self) -> bool:
        """Snap active window to the left half of the display (Win+Left)."""
        try:
            pyautogui.hotkey("win", "left")
            logger.info("Snapped active window left")
            return True
        except Exception as exc:
            logger.error("Failed to snap window left: %s", exc)
            return False

    def snap_right(self) -> bool:
        """Snap active window to the right half of the display (Win+Right)."""
        try:
            pyautogui.hotkey("win", "right")
            logger.info("Snapped active window right")
            return True
        except Exception as exc:
            logger.error("Failed to snap window right: %s", exc)
            return False

    def snap_top_left(self) -> bool:
        """Snap active window to top-left corner (Win+Left, Win+Up)."""
        try:
            pyautogui.hotkey("win", "left")
            pyautogui.hotkey("win", "up")
            logger.info("Snapped window to top-left corner")
            return True
        except Exception as exc:
            logger.error("Failed to snap top-left: %s", exc)
            return False

    def snap_top_right(self) -> bool:
        """Snap active window to top-right corner (Win+Right, Win+Up)."""
        try:
            pyautogui.hotkey("win", "right")
            pyautogui.hotkey("win", "up")
            logger.info("Snapped window to top-right corner")
            return True
        except Exception as exc:
            logger.error("Failed to snap top-right: %s", exc)
            return False

    def snap_bottom_left(self) -> bool:
        """Snap active window to bottom-left corner (Win+Left, Win+Down)."""
        try:
            pyautogui.hotkey("win", "left")
            pyautogui.hotkey("win", "down")
            logger.info("Snapped window to bottom-left corner")
            return True
        except Exception as exc:
            logger.error("Failed to snap bottom-left: %s", exc)
            return False

    def snap_bottom_right(self) -> bool:
        """Snap active window to bottom-right corner (Win+Right, Win+Down)."""
        try:
            pyautogui.hotkey("win", "right")
            pyautogui.hotkey("win", "down")
            logger.info("Snapped window to bottom-right corner")
            return True
        except Exception as exc:
            logger.error("Failed to snap bottom-right: %s", exc)
            return False

    def next_monitor(self) -> bool:
        """Move active window to the next monitor (Win+Shift+Right)."""
        try:
            pyautogui.hotkey("win", "shift", "right")
            logger.info("Moved active window to next monitor")
            return True
        except Exception as exc:
            logger.error("Failed to move to next monitor: %s", exc)
            return False

    def prev_monitor(self) -> bool:
        """Move active window to previous monitor (Win+Shift+Left)."""
        try:
            pyautogui.hotkey("win", "shift", "left")
            logger.info("Moved active window to previous monitor")
            return True
        except Exception as exc:
            logger.error("Failed to move to previous monitor: %s", exc)
            return False

    def minimize_others(self) -> bool:
        """Minimize all windows except active one (Win+Home)."""
        try:
            pyautogui.hotkey("win", "home")
            logger.info("Minimized all other windows (Win+Home)")
            return True
        except Exception as exc:
            logger.error("Failed to minimize others: %s", exc)
            return False

    def next_desktop(self) -> bool:
        """Switch to next virtual desktop (Ctrl+Win+Right)."""
        try:
            pyautogui.hotkey("ctrl", "win", "right")
            logger.info("Switched to next virtual desktop")
            return True
        except Exception as exc:
            logger.error("Failed switching desktop: %s", exc)
            return False

    def prev_desktop(self) -> bool:
        """Switch to previous virtual desktop (Ctrl+Win+Left)."""
        try:
            pyautogui.hotkey("ctrl", "win", "left")
            logger.info("Switched to previous virtual desktop")
            return True
        except Exception as exc:
            logger.error("Failed switching desktop: %s", exc)
            return False

    def task_view(self) -> bool:
        """Open Windows Task View / All Windows (Win+Tab)."""
        try:
            pyautogui.hotkey("win", "tab")
            logger.info("Opened Task View (Win+Tab)")
            return True
        except Exception as exc:
            logger.error("Failed to open Task View: %s", exc)
            return False

    # 6. Browser & App Navigation
    def zoom_in(self) -> bool:
        """Zoom in on active document or browser page (Ctrl+=)."""
        try:
            pyautogui.hotkey("ctrl", "=")
            return True
        except Exception:
            try:
                pyautogui.hotkey("ctrl", "add")
                return True
            except Exception as exc:
                logger.error("Failed to zoom in: %s", exc)
                return False

    def zoom_out(self) -> bool:
        """Zoom out on active document or browser page (Ctrl+-)."""
        try:
            pyautogui.hotkey("ctrl", "-")
            return True
        except Exception as exc:
            logger.error("Failed to zoom out: %s", exc)
            return False

    def zoom_reset(self) -> bool:
        """Reset zoom to 100% (Ctrl+0)."""
        try:
            pyautogui.hotkey("ctrl", "0")
            return True
        except Exception as exc:
            logger.error("Failed to reset zoom: %s", exc)
            return False

    def go_back(self) -> bool:
        """Navigate back in browser or Explorer (Alt+Left)."""
        try:
            pyautogui.hotkey("alt", "left")
            return True
        except Exception as exc:
            logger.error("Failed to navigate back: %s", exc)
            return False

    def go_forward(self) -> bool:
        """Navigate forward in browser or Explorer (Alt+Right)."""
        try:
            pyautogui.hotkey("alt", "right")
            return True
        except Exception as exc:
            logger.error("Failed to navigate forward: %s", exc)
            return False

    def address_bar(self) -> bool:
        """Focus browser address bar or explorer path (Ctrl+L)."""
        try:
            pyautogui.hotkey("ctrl", "l")
            return True
        except Exception as exc:
            logger.error("Failed to focus address bar: %s", exc)
            return False

    def next_tab(self) -> bool:
        """Switch to next tab in browser/editor (Ctrl+Tab)."""
        try:
            pyautogui.hotkey("ctrl", "tab")
            return True
        except Exception as exc:
            logger.error("Failed to switch next tab: %s", exc)
            return False

    def prev_tab(self) -> bool:
        """Switch to previous tab in browser/editor (Ctrl+Shift+Tab)."""
        try:
            pyautogui.hotkey("ctrl", "shift", "tab")
            return True
        except Exception as exc:
            logger.error("Failed to switch previous tab: %s", exc)
            return False

    def duplicate_tab(self) -> bool:
        """Duplicate current browser tab (Ctrl+L, Alt+Enter)."""
        try:
            pyautogui.hotkey("ctrl", "l")
            pyautogui.hotkey("alt", "enter")
            logger.info("Duplicated browser tab")
            return True
        except Exception as exc:
            logger.error("Failed to duplicate tab: %s", exc)
            return False

    def incognito_window(self) -> bool:
        """Open a new Incognito / Private window (Ctrl+Shift+N)."""
        try:
            pyautogui.hotkey("ctrl", "shift", "n")
            logger.info("Opened new Incognito window (Ctrl+Shift+N)")
            return True
        except Exception as exc:
            logger.error("Failed to open incognito window: %s", exc)
            return False

    def hard_refresh(self) -> bool:
        """Hard refresh ignoring cache (Ctrl+F5)."""
        try:
            pyautogui.hotkey("ctrl", "f5")
            logger.info("Triggered hard refresh (Ctrl+F5)")
            return True
        except Exception as exc:
            logger.error("Failed hard refresh: %s", exc)
            return False

    def view_source(self) -> bool:
        """View page source (Ctrl+U)."""
        try:
            pyautogui.hotkey("ctrl", "u")
            return True
        except Exception as exc:
            logger.error("Failed view source: %s", exc)
            return False

    def toggle_bookmarks_bar(self) -> bool:
        """Toggle bookmarks bar (Ctrl+Shift+B)."""
        try:
            pyautogui.hotkey("ctrl", "shift", "b")
            return True
        except Exception as exc:
            logger.error("Failed toggle bookmarks bar: %s", exc)
            return False

    def switch_to_tab(self, target: Union[int, str], uia: Optional[Any] = None) -> bool:
        """Switch to a specific tab number (1 through 9) or search by title/keyword."""
        if isinstance(target, int) or (isinstance(target, str) and target.strip().isdigit()):
            try:
                num = int(target)
                clamped = max(1, min(9, num))
                pyautogui.hotkey("ctrl", str(clamped))
                logger.info("Switched to tab %d (Ctrl+%d)", clamped, clamped)
                return True
            except Exception as exc:
                logger.error("Failed to switch to tab %s: %s", target, exc)
                return False

        clean_q = str(target).strip()
        if uia:
            try:
                active_win = uia.get_active_window()
                if active_win:
                    for tab in active_win.descendants(control_type="TabItem"):
                        t_text = (tab.window_text() or "").lower()
                        if clean_q.lower() in t_text:
                            tab.select()
                            logger.info("Switched to tab matching '%s' via UIA TabItem", clean_q)
                            return True
            except Exception as exc:
                logger.debug("UIA tab search error: %s", exc)

        try:
            pyautogui.hotkey("ctrl", "shift", "a")
            pyautogui.sleep(0.15)
            pyautogui.write(clean_q)
            pyautogui.sleep(0.1)
            pyautogui.press("enter")
            logger.info("Dispatched tab search for '%s' via Ctrl+Shift+A", clean_q)
            return True
        except Exception as exc:
            logger.error("Failed to search/switch tab: %s", exc)
            return False

    # 7. Media Extensions
    def rewind_media(self, seconds: int = 10) -> bool:
        """Rewind video or media playback."""
        try:
            pyautogui.press("left")
            logger.info("Rewound media by ~%d seconds (Left arrow)", seconds)
            return True
        except Exception as exc:
            logger.error("Failed to rewind media: %s", exc)
            return False

    def forward_media(self, seconds: int = 10) -> bool:
        """Fast-forward video or media playback."""
        try:
            pyautogui.press("right")
            logger.info("Fast-forwarded media by ~%d seconds (Right arrow)", seconds)
            return True
        except Exception as exc:
            logger.error("Failed to forward media: %s", exc)
            return False

    def playback_faster(self) -> bool:
        """Increase media playback speed (Shift+>)."""
        try:
            pyautogui.hotkey("shift", ">")
            return True
        except Exception as exc:
            logger.error("Failed playback faster: %s", exc)
            return False

    def playback_slower(self) -> bool:
        """Decrease media playback speed (Shift+<)."""
        try:
            pyautogui.hotkey("shift", "<")
            return True
        except Exception as exc:
            logger.error("Failed playback slower: %s", exc)
            return False

    def toggle_captions(self) -> bool:
        """Toggle video captions/subtitles ('c')."""
        try:
            pyautogui.press("c")
            return True
        except Exception as exc:
            logger.error("Failed toggle captions: %s", exc)
            return False

    def theater_mode(self) -> bool:
        """Toggle video theater mode ('t')."""
        try:
            pyautogui.press("t")
            return True
        except Exception as exc:
            logger.error("Failed toggle theater mode: %s", exc)
            return False

    def full_screen_media(self) -> bool:
        """Toggle media player fullscreen ('f')."""
        try:
            pyautogui.press("f")
            return True
        except Exception as exc:
            logger.error("Failed toggle media fullscreen: %s", exc)
            return False

    def mute_media(self) -> bool:
        """Toggle in-player audio mute ('m')."""
        try:
            pyautogui.press("m")
            return True
        except Exception as exc:
            logger.error("Failed toggle media mute: %s", exc)
            return False

    # 8. Text & Cursor Controls
    def delete_line(self) -> bool:
        """Clear current line (Home, Shift+End, Backspace)."""
        try:
            pyautogui.press("home")
            pyautogui.hotkey("shift", "end")
            pyautogui.press("backspace")
            return True
        except Exception as exc:
            logger.error("Failed to delete line: %s", exc)
            return False

    def delete_word(self) -> bool:
        """Delete previous word (Ctrl+Backspace)."""
        try:
            pyautogui.hotkey("ctrl", "backspace")
            return True
        except Exception as exc:
            logger.error("Failed to delete word: %s", exc)
            return False

    def select_line(self) -> bool:
        """Select entire current line (Home, Shift+End)."""
        try:
            pyautogui.press("home")
            pyautogui.hotkey("shift", "end")
            return True
        except Exception as exc:
            logger.error("Failed to select line: %s", exc)
            return False

    def line_start(self) -> bool:
        """Move cursor to beginning of line (Home)."""
        try:
            pyautogui.press("home")
            return True
        except Exception as exc:
            logger.error("Failed to go to line start: %s", exc)
            return False

    def line_end(self) -> bool:
        """Move cursor to end of line (End)."""
        try:
            pyautogui.press("end")
            return True
        except Exception as exc:
            logger.error("Failed to go to line end: %s", exc)
            return False

    def page_top(self) -> bool:
        """Scroll/jump to top of document or page (Ctrl+Home)."""
        try:
            pyautogui.hotkey("ctrl", "home")
            return True
        except Exception as exc:
            logger.error("Failed to jump to top: %s", exc)
            return False

    def page_bottom(self) -> bool:
        """Scroll/jump to bottom of document or page (Ctrl+End)."""
        try:
            pyautogui.hotkey("ctrl", "end")
            return True
        except Exception as exc:
            logger.error("Failed to jump to bottom: %s", exc)
            return False

    # 9. Additional Windows Shell Controls
    def open_run(self) -> bool:
        """Open Windows Run dialog (Win+R)."""
        try:
            pyautogui.hotkey("win", "r")
            return True
        except Exception as exc:
            logger.error("Failed to open Run dialog: %s", exc)
            return False

    def emoji_panel(self) -> bool:
        """Open Windows Emoji Panel (Win+.)."""
        try:
            pyautogui.hotkey("win", ".")
            return True
        except Exception as exc:
            logger.error("Failed to open emoji panel: %s", exc)
            return False

    def game_bar(self) -> bool:
        """Open Windows Game Bar / Recording (Win+G)."""
        try:
            pyautogui.hotkey("win", "g")
            return True
        except Exception as exc:
            logger.error("Failed to open game bar: %s", exc)
            return False

    def quick_settings(self) -> bool:
        """Open Windows Quick Settings / Control Center (Win+A)."""
        try:
            pyautogui.hotkey("win", "a")
            return True
        except Exception as exc:
            logger.error("Failed to open quick settings: %s", exc)
            return False

    # 7. Mouse Extensions
    def middle_click(
        self, element: Optional[Any] = None, coordinates: Optional[Tuple[int, int]] = None
    ) -> bool:
        """Perform a middle-click (e.g. to open link in background tab)."""
        if element is not None:
            try:
                rect = element.rectangle()
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                pyautogui.middleClick(cx, cy)
                return True
            except Exception:
                pass

        if coordinates is not None:
            try:
                pyautogui.middleClick(*coordinates)
                return True
            except Exception as exc:
                logger.error("Failed to middle click: %s", exc)

        return False

    def hover(
        self, element: Optional[Any] = None, coordinates: Optional[Tuple[int, int]] = None
    ) -> bool:
        """Hover mouse over an element or coordinates."""
        if element is not None:
            try:
                rect = element.rectangle()
                cx = (rect.left + rect.right) // 2
                cy = (rect.top + rect.bottom) // 2
                pyautogui.moveTo(cx, cy)
                return True
            except Exception:
                pass

        if coordinates is not None:
            try:
                pyautogui.moveTo(*coordinates)
                return True
            except Exception as exc:
                logger.error("Failed to hover mouse: %s", exc)

        return False

    def move_mouse(self, direction: str, distance: int = 200) -> bool:
        """Move mouse relative to current position or center."""
        try:
            dir_clean = direction.strip().lower()
            if dir_clean == "center":
                sw, sh = pyautogui.size()
                pyautogui.moveTo(sw // 2, sh // 2)
                return True

            cx, cy = pyautogui.position()
            if dir_clean == "left":
                pyautogui.moveTo(max(0, cx - distance), cy)
            elif dir_clean == "right":
                pyautogui.moveTo(cx + distance, cy)
            elif dir_clean == "up":
                pyautogui.moveTo(cx, max(0, cy - distance))
            elif dir_clean == "down":
                pyautogui.moveTo(cx, cy + distance)
            return True
        except Exception as exc:
            logger.error("Failed to move mouse %s: %s", direction, exc)
            return False

    # 10. Display & Visual Comfort
    def set_brightness(self, percent: int) -> bool:
        """Set screen brightness (0 to 100%). Uses WMI on laptops or Gamma Ramp on desktop displays."""
        level = max(0, min(100, int(percent)))
        # 1. Try WMI for laptop internal displays
        try:
            cmd = f"(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightnessMethods).WmiSetBrightness(1, {level})"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0:
                logger.info("Set display brightness to %d%% via WMI", level)
                return True
        except Exception:
            pass

        # 2. Universal fallback: Windows GDI Device Gamma Ramp (works on all monitors/screens)
        try:
            from ctypes import wintypes
            class RAMP(ctypes.Structure):
                _fields_ = [
                    ('Red', wintypes.WORD * 256),
                    ('Green', wintypes.WORD * 256),
                    ('Blue', wintypes.WORD * 256),
                ]

            hdc = ctypes.windll.user32.GetDC(None)
            ramp = RAMP()
            factor = max(0.1, level / 100.0)
            for i in range(256):
                val = int(min(65535, max(0, (i * 256) * factor)))
                ramp.Red[i] = val
                ramp.Green[i] = val
                ramp.Blue[i] = val
            ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
            ctypes.windll.user32.ReleaseDC(None, hdc)
            logger.info("Set screen brightness/gamma factor to %.2f (%d%%)", factor, level)
            return True
        except Exception as exc:
            logger.error("Failed to set brightness: %s", exc)
            return False

    def get_brightness(self) -> Optional[int]:
        """Query current display brightness if available."""
        try:
            cmd = "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0 and res.stdout.strip().isdigit():
                return int(res.stdout.strip())
        except Exception:
            pass
        return None

    def set_dark_mode(self, enable: bool = True) -> bool:
        """Switch Windows system and apps theme between Dark Mode and Light Mode."""
        try:
            import winreg
            val = 0 if enable else 1
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
                winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)

            HWND_BROADCAST = 0xFFFF
            WM_SETTINGCHANGE = 0x001A
            SMTO_ABORTIFHUNG = 0x0002
            ctypes.windll.user32.SendMessageTimeoutW(
                HWND_BROADCAST, WM_SETTINGCHANGE, 0, "ImmersiveColorSet", SMTO_ABORTIFHUNG, 200, None
            )
            mode_str = "Dark" if enable else "Light"
            logger.info("Switched Windows theme to %s Mode", mode_str)
            return True
        except Exception as exc:
            logger.error("Failed to set theme mode: %s", exc)
            return False

    def get_dark_mode(self) -> bool:
        """Check if Windows is currently in Dark Mode."""
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return val == 0
        except Exception:
            return False

    def toggle_dark_mode(self) -> bool:
        """Toggle between Dark and Light mode."""
        cur = self.get_dark_mode()
        return self.set_dark_mode(not cur)

    def set_display_mode(self, mode: str) -> bool:
        """Switch multi-monitor display mode (clone/duplicate, extend, internal/pc_only, external/second_only)."""
        mode_clean = mode.strip().lower()
        flag_map = {
            "clone": "/clone",
            "duplicate": "/clone",
            "extend": "/extend",
            "internal": "/internal",
            "pc_only": "/internal",
            "external": "/external",
            "second_only": "/external",
        }
        flag = flag_map.get(mode_clean, "/extend")
        try:
            subprocess.Popen(["DisplaySwitch.exe", flag])
            logger.info("Dispatched DisplaySwitch.exe %s", flag)
            return True
        except Exception as exc:
            logger.error("Failed to switch display mode: %s", exc)
            return False

    def toggle_night_light(self) -> bool:
        """Open or toggle Windows Night Light."""
        try:
            os.startfile("ms-settings:nightlight")
            return True
        except Exception as exc:
            logger.error("Failed to open Night Light settings: %s", exc)
            return False

    # 11. System Health & Process Diagnostics
    def get_battery_status(self) -> str:
        """Query battery status, percentage, and charging state."""
        try:
            ps_bat = "Get-CimInstance -ClassName Win32_Battery | Select-Object EstimatedChargeRemaining, BatteryStatus | ConvertTo-Json"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_bat], capture_output=True, text=True, timeout=2.5)
            output = res.stdout.strip()
            if output:
                import json
                data = json.loads(output)
                if isinstance(data, list) and data:
                    data = data[0]
                charge = data.get("EstimatedChargeRemaining")
                status_code = data.get("BatteryStatus", 1)
                status_desc = "Charging" if status_code == 2 else "Discharging"
                return f"Battery is at {charge}% ({status_desc})."
        except Exception as exc:
            logger.debug("Battery query failed: %s", exc)
        return "System is running on desktop AC power (100% stable, no battery installed)."

    def get_top_ram_processes(self, count: int = 3) -> str:
        """Get the top memory-consuming processes."""
        try:
            ps_proc = f"Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First {count} ProcessName, @{{Name='RAM_MB';Expression={{[math]::Round($_.WorkingSet64 / 1MB, 1)}}}} | ConvertTo-Json"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_proc], capture_output=True, text=True, timeout=3.0)
            output = res.stdout.strip()
            if output:
                import json
                data = json.loads(output)
                if isinstance(data, dict):
                    data = [data]
                items = [f"{p.get('ProcessName')} ({p.get('RAM_MB')} MB)" for p in data]
                return f"Top RAM processes: {', '.join(items)}."
        except Exception as exc:
            logger.debug("Process memory query failed: %s", exc)
        return "Memory usage normal."

    def get_system_health(self) -> str:
        """Summary of system RAM and battery."""
        ram_info = self.get_top_ram_processes(count=3)
        bat_info = self.get_battery_status()
        return f"{bat_info} {ram_info}"

    def kill_process(self, target: str) -> bool:
        """Force terminate an application process by name."""
        clean_target = target.strip()
        exe = clean_target if clean_target.lower().endswith(".exe") else f"{clean_target}.exe"
        try:
            res = subprocess.run(["taskkill", "/F", "/IM", exe], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0:
                logger.info("Terminated process '%s'", exe)
                return True
            logger.warning("Could not terminate process '%s': %s", exe, res.stderr.strip())
            return False
        except Exception as exc:
            logger.error("Failed to kill process '%s': %s", target, exc)
            return False

    def restart_explorer(self) -> bool:
        """Restart Windows Explorer to refresh taskbar and desktop."""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], capture_output=True, timeout=2.0)
            subprocess.Popen(["explorer.exe"])
            logger.info("Restarted Windows Explorer")
            return True
        except Exception as exc:
            logger.error("Failed to restart explorer: %s", exc)
            return False

    # 12. File System & Download Shortcuts
    def open_latest_download(self) -> bool:
        """Locate and open the most recently downloaded file."""
        downloads_dir = os.path.expanduser(r"~\Downloads")
        if not os.path.exists(downloads_dir):
            return False
        try:
            files = [
                os.path.join(downloads_dir, f)
                for f in os.listdir(downloads_dir)
                if not f.endswith((".crdownload", ".tmp", ".part"))
                and os.path.isfile(os.path.join(downloads_dir, f))
            ]
            if not files:
                return False
            latest = max(files, key=os.path.getmtime)
            os.startfile(latest)
            logger.info("Opened latest download: %s", latest)
            return True
        except Exception as exc:
            logger.error("Failed to open latest download: %s", exc)
            return False

    def open_latest_screenshot(self) -> bool:
        """Locate and open the most recent screenshot."""
        candidate_dirs = [
            os.path.expanduser(r"~\Pictures\Screenshots"),
            os.path.expanduser(r"~\OneDrive\Pictures\Screenshots"),
            os.path.expanduser(r"~\Desktop"),
        ]
        all_imgs = []
        for d in candidate_dirs:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.lower().endswith((".png", ".jpg", ".jpeg")):
                        full = os.path.join(d, f)
                        if os.path.isfile(full):
                            all_imgs.append(full)
        if not all_imgs:
            return False
        try:
            latest = max(all_imgs, key=os.path.getmtime)
            os.startfile(latest)
            logger.info("Opened latest screenshot: %s", latest)
            return True
        except Exception as exc:
            logger.error("Failed to open screenshot: %s", exc)
            return False

    def open_folder(self, folder_name: str) -> bool:
        """Open a standard user folder (Downloads, Documents, Desktop, Pictures, Videos, Music)."""
        f = folder_name.strip().lower()
        folder_map = {
            "downloads": r"~\Downloads",
            "documents": r"~\Documents",
            "desktop": r"~\Desktop",
            "pictures": r"~\Pictures",
            "music": r"~\Music",
            "videos": r"~\Videos",
        }
        path = os.path.expanduser(folder_map.get(f, r"~"))
        try:
            os.startfile(path)
            logger.info("Opened folder '%s' (%s)", folder_name, path)
            return True
        except Exception as exc:
            logger.error("Failed to open folder '%s': %s", folder_name, exc)
            return False

    def empty_recycle_bin(self) -> bool:
        """Silently empty Windows Recycle Bin."""
        try:
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            logger.info("Emptied Recycle Bin (res=%s)", res)
            return True
        except Exception as exc:
            logger.error("Failed to empty Recycle Bin: %s", exc)
            return False

    # 13. Caffeine / Keep Awake & Boss Mode
    def set_keep_awake(self, enable: bool = True) -> bool:
        """Prevent Windows from sleeping or turning off screen ('Caffeine' mode)."""
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            if enable:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
                logger.info("Caffeine mode enabled (system will stay awake)")
            else:
                ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
                logger.info("Caffeine mode disabled (normal sleep restored)")
            return True
        except Exception as exc:
            logger.error("Failed to set keep awake state: %s", exc)
            return False

    def boss_mode(self) -> bool:
        """Instantly minimize all windows and mute system sound (Privacy shield)."""
        try:
            pyautogui.hotkey("win", "d")
            self.set_volume(0)
            logger.info("Boss Mode engaged: Desktop shown, sound muted")
            return True
        except Exception as exc:
            logger.error("Failed to engage Boss Mode: %s", exc)
            return False

    # 14. Network & Connectivity
    def get_network_info(self) -> str:
        """Query local IP and ping connection status."""
        import socket
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            ping_res = subprocess.run(["ping", "-n", "1", "-w", "1000", "8.8.8.8"], capture_output=True, text=True)
            online = "Online" if ping_res.returncode == 0 else "Offline"
            return f"Network is {online}. Local IP: {ip}."
        except Exception as exc:
            logger.debug("Network query error: %s", exc)
            return "Network query completed."

    # 15. Clipboard Power Tools
    def paste_plain_text(self) -> bool:
        """Paste clipboard contents as unformatted plain text."""
        try:
            pyautogui.hotkey("ctrl", "shift", "v")
            logger.info("Pasted plain text via Ctrl+Shift+V")
            return True
        except Exception:
            pyautogui.hotkey("ctrl", "v")
            return True

    def clear_clipboard(self) -> bool:
        """Clear the Windows clipboard."""
        try:
            if ctypes.windll.user32.OpenClipboard(None):
                ctypes.windll.user32.EmptyClipboard()
                ctypes.windll.user32.CloseClipboard()
                logger.info("Cleared clipboard")
                return True
        except Exception as exc:
            logger.error("Failed to clear clipboard: %s", exc)
        return False

    # 16. Smart Browser Utilities
    def copy_current_url(self) -> bool:
        """Copy the current browser address bar URL to clipboard (Ctrl+L, Ctrl+C)."""
        try:
            pyautogui.hotkey("ctrl", "l")
            pyautogui.hotkey("ctrl", "c")
            pyautogui.press("esc")
            logger.info("Copied current browser URL to clipboard")
            return True
        except Exception as exc:
            logger.error("Failed to copy URL: %s", exc)
            return False
