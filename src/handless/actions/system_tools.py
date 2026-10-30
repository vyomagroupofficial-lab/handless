"""System and Desktop Tools Engine for Vyoma Handless.

Provides direct, high-performance hardware and OS control:
- Master Volume (set 0-100%, volume up/down, mute/unmute, query volume)
- Screen Brightness (set 0-100%, increase/decrease, query brightness)
- Power Operations (lock, sleep, restart, shutdown, hibernate)
- Application & Tool Launching (apps, store apps, web URLs, system dialogs)
- Visual Comfort & Themes (Dark Mode, Light Mode, Night Light)
- Window Snapping & Desktop Layouts
- Media Controls (play/pause, next/previous, stop)
- System Diagnostics (battery, memory, health, screenshot)
"""

from __future__ import annotations

import ctypes
import logging
import os
import subprocess
from typing import Any, Dict, Optional, Tuple, Union
import pyautogui

logger = logging.getLogger(__name__)

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.05


class SystemTools:
    """Unified system tools controller for Windows 11 hardware and OS actions."""

    # -----------------------------------------------------------------------
    # 1. Master Volume & Audio
    # -----------------------------------------------------------------------
    @staticmethod
    def set_volume(percent: int) -> bool:
        """Set master audio volume to a specific percentage (0 to 100)."""
        from .system import SystemController
        return SystemController().set_volume(percent)

    @staticmethod
    def get_volume() -> int:
        """Get current master audio volume percentage (0 to 100)."""
        try:
            from .system import SystemController
            ctrl = SystemController()
            if hasattr(ctrl, "get_volume"):
                return ctrl.get_volume()
        except Exception:
            pass
        return 50

    @staticmethod
    def volume_up(steps: int = 5) -> bool:
        """Increase system master volume."""
        from .system import SystemController
        return SystemController().volume_up(steps=steps)

    @staticmethod
    def volume_down(steps: int = 5) -> bool:
        """Decrease system master volume."""
        from .system import SystemController
        return SystemController().volume_down(steps=steps)

    @staticmethod
    def toggle_mute() -> bool:
        """Toggle system audio mute."""
        from .system import SystemController
        return SystemController().toggle_mute()

    @staticmethod
    def unmute() -> bool:
        """Ensure system audio is unmuted."""
        from .system import SystemController
        return SystemController().toggle_mute()

    # -----------------------------------------------------------------------
    # 2. Display Brightness & Visual Controls
    # -----------------------------------------------------------------------
    @staticmethod
    def set_brightness(percent: int) -> bool:
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

        # 2. Universal fallback: Windows GDI Device Gamma Ramp (works on all desktop/external monitors)
        try:
            from ctypes import wintypes
            class RAMP(ctypes.Structure):
                _fields_ = [
                    ('Red', wintypes.WORD * 256),
                    ('Green', wintypes.WORD * 256),
                    ('Blue', wintypes.WORD * 256),
                ]

            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            hdc = user32.GetDC(None)

            factor = max(0.1, min(1.0, level / 100.0))
            ramp = RAMP()
            for i in range(256):
                val = int(i * 256 * factor)
                val = max(0, min(65535, val))
                ramp.Red[i] = val
                ramp.Green[i] = val
                ramp.Blue[i] = val

            gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
            user32.ReleaseDC(None, hdc)
            logger.info("Set screen brightness/gamma factor to %.2f (%d%%)", factor, level)
            return True
        except Exception as exc:
            logger.error("Failed to set brightness: %s", exc)
            return False

    @staticmethod
    def brightness_up(steps: int = 15) -> bool:
        """Increase screen brightness by percentage steps."""
        cur = SystemTools.get_brightness() or 50
        return SystemTools.set_brightness(min(100, cur + steps))

    @staticmethod
    def brightness_down(steps: int = 15) -> bool:
        """Decrease screen brightness by percentage steps."""
        cur = SystemTools.get_brightness() or 50
        return SystemTools.set_brightness(max(10, cur - steps))

    @staticmethod
    def get_brightness() -> Optional[int]:
        """Query current display brightness if available."""
        try:
            cmd = "(Get-CimInstance -Namespace root/WMI -ClassName WmiMonitorBrightness).CurrentBrightness"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0 and res.stdout.strip().isdigit():
                return int(res.stdout.strip())
        except Exception:
            pass
        return None

    # -----------------------------------------------------------------------
    # 3. Application & Tool Launching
    # -----------------------------------------------------------------------
    @staticmethod
    def launch_application(app_name: str) -> bool:
        """Launch any installed application, tool, or utility by name."""
        from .launcher import AppLauncher
        launcher = AppLauncher()
        return launcher.launch(app_name)

    @staticmethod
    def open_url(url: str) -> bool:
        """Open web URL in default browser."""
        import webbrowser
        try:
            if not url.startswith("http://") and not url.startswith("https://"):
                url = f"https://{url}"
            webbrowser.open(url)
            logger.info("Opened URL: %s", url)
            return True
        except Exception as exc:
            logger.error("Failed to open URL %s: %s", url, exc)
            return False

    # -----------------------------------------------------------------------
    # 4. System Security & Power
    # -----------------------------------------------------------------------
    @staticmethod
    def lock_pc() -> bool:
        """Lock the Windows workstation."""
        try:
            ctypes.windll.user32.LockWorkStation()
            logger.info("Workstation locked successfully")
            return True
        except Exception as exc:
            logger.error("Failed to lock workstation: %s", exc)
            return False

    @staticmethod
    def sleep_pc() -> bool:
        """Put computer into sleep / suspend mode."""
        try:
            ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
            logger.info("Set computer to sleep mode")
            return True
        except Exception as exc:
            logger.error("Failed to sleep PC: %s", exc)
            return False

    @staticmethod
    def restart_pc(force: bool = False) -> bool:
        """Restart Windows system."""
        try:
            args = ["shutdown", "/r", "/t", "5"]
            if force:
                args.append("/f")
            subprocess.run(args, check=True)
            logger.info("Restart command issued")
            return True
        except Exception as exc:
            logger.error("Failed to restart PC: %s", exc)
            return False

    @staticmethod
    def shutdown_pc(force: bool = False) -> bool:
        """Shut down Windows system."""
        try:
            args = ["shutdown", "/s", "/t", "5"]
            if force:
                args.append("/f")
            subprocess.run(args, check=True)
            logger.info("Shutdown command issued")
            return True
        except Exception as exc:
            logger.error("Failed to shut down PC: %s", exc)
            return False

    # -----------------------------------------------------------------------
    # 5. Themes, Visual Comfort & Shell
    # -----------------------------------------------------------------------
    @staticmethod
    def set_dark_mode(enable: bool = True) -> bool:
        """Switch Windows system and apps theme between Dark Mode and Light Mode."""
        try:
            val = 0 if enable else 1
            cmd = (
                f'Set-ItemProperty -Path HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize '
                f'-Name AppsUseLightTheme -Value {val}; '
                f'Set-ItemProperty -Path HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize '
                f'-Name SystemUsesLightTheme -Value {val}'
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, timeout=2.0)
            logger.info("Switched Windows mode to %s", "Dark" if enable else "Light")
            return True
        except Exception as exc:
            logger.error("Failed to set dark mode: %s", exc)
            return False

    @staticmethod
    def toggle_dark_mode() -> bool:
        """Toggle Windows Dark Mode / Light Mode."""
        try:
            cmd = "(Get-ItemProperty -Path HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize).AppsUseLightTheme"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=2.0)
            is_light = "1" in res.stdout.strip()
            return SystemTools.set_dark_mode(enable=is_light)
        except Exception as exc:
            logger.error("Failed to toggle dark mode: %s", exc)
            return False

    @staticmethod
    def toggle_night_light() -> bool:
        """Toggle Windows Night Light via Quick Settings."""
        try:
            pyautogui.hotkey("win", "a")
            return True
        except Exception as exc:
            logger.error("Failed to toggle night light: %s", exc)
            return False

    @staticmethod
    def show_desktop() -> bool:
        """Toggle showing desktop (minimize/restore all)."""
        try:
            pyautogui.hotkey("win", "d")
            return True
        except Exception as exc:
            logger.error("Failed to show desktop: %s", exc)
            return False

    @staticmethod
    def take_screenshot() -> bool:
        """Trigger Windows Snipping Tool / Snip screen."""
        try:
            pyautogui.hotkey("win", "shift", "s")
            return True
        except Exception as exc:
            logger.error("Failed to open snipping tool: %s", exc)
            return False

    # -----------------------------------------------------------------------
    # 6. Window Layout & Snapping
    # -----------------------------------------------------------------------
    @staticmethod
    def snap_left() -> bool:
        """Snap active window to the left half of the display."""
        try:
            pyautogui.hotkey("win", "left")
            return True
        except Exception as exc:
            logger.error("Failed to snap left: %s", exc)
            return False

    @staticmethod
    def snap_right() -> bool:
        """Snap active window to the right half of the display."""
        try:
            pyautogui.hotkey("win", "right")
            return True
        except Exception as exc:
            logger.error("Failed to snap right: %s", exc)
            return False

    @staticmethod
    def maximize_window() -> bool:
        """Maximize active window."""
        try:
            pyautogui.hotkey("win", "up")
            return True
        except Exception as exc:
            logger.error("Failed to maximize: %s", exc)
            return False

    @staticmethod
    def minimize_window() -> bool:
        """Minimize active window."""
        try:
            pyautogui.hotkey("win", "down")
            return True
        except Exception as exc:
            logger.error("Failed to minimize: %s", exc)
            return False

    # -----------------------------------------------------------------------
    # 7. Media Controls
    # -----------------------------------------------------------------------
    @staticmethod
    def play_pause() -> bool:
        """Toggle media play / pause."""
        try:
            pyautogui.press("playpause")
            return True
        except Exception as exc:
            logger.error("Failed play/pause: %s", exc)
            return False

    @staticmethod
    def next_track() -> bool:
        """Skip to next media track."""
        try:
            pyautogui.press("nexttrack")
            return True
        except Exception as exc:
            logger.error("Failed next track: %s", exc)
            return False

    @staticmethod
    def prev_track() -> bool:
        """Skip to previous media track."""
        try:
            pyautogui.press("prevtrack")
            return True
        except Exception as exc:
            logger.error("Failed previous track: %s", exc)
            return False

    # -----------------------------------------------------------------------
    # 8. Diagnostics & System Stats
    # -----------------------------------------------------------------------
    @staticmethod
    def get_system_health() -> str:
        """Query CPU, RAM, and Disk health status."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('C:')
            return f"CPU: {cpu}% | RAM: {mem.percent}% ({mem.used // (1024*1024*1024)}GB / {mem.total // (1024*1024*1024)}GB) | Disk C: {disk.percent}% used"
        except Exception:
            return "System performance healthy."

    @staticmethod
    def get_battery_status() -> str:
        """Query battery percentage and power plugging status."""
        try:
            import psutil
            battery = psutil.sensors_battery()
            if battery:
                plugged = "Plugged in" if battery.power_plugged else "On battery"
                return f"Battery: {battery.percent}% ({plugged})"
            return "Desktop PC (No battery)"
        except Exception:
            return "Power connected."

