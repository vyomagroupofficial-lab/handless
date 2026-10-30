"""Application Launcher for Windows.

Locates and launches Windows desktop applications via known executable aliases,
system URI schemes, Start Menu shortcut indexes, Windows StartApps (shell:AppsFolder),
Registry App Paths, and Web Application URLs.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import winreg
from pathlib import Path
from typing import Dict, List, Optional
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

COMMON_APP_MAP: Dict[str, str] = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "brave": "brave",
    "opera": "opera",
    
    # Text / Editors
    "notepad": "notepad",
    "notepad++": "notepad++",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "code": "code",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",

    # Utilities
    "calculator": "calc",
    "calc": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "terminal": "wt",
    "windows terminal": "wt",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "task manager": "taskmgr",
    "paint": "mspaint",
    "settings": "ms-settings:",
    "github desktop": "githubdesktop",
    "snipping tool": "snippingtool",
    "snip": "snippingtool",
    "control panel": "control",
    "device manager": "devmgmt.msc",
    "disk management": "diskmgmt.msc",
    "camera": "microsoft.windows.camera:",
    "photos": "ms-photos:",
    "clock": "ms-clock:",
    "alarms": "ms-clock:",
    "store": "ms-windows-store:",
    "microsoft store": "ms-windows-store:",
    "weather": "msnweather:",
    "maps": "bingmaps:",

    # Media, Social & Communication
    "spotify": "spotify:",
    "discord": "discord",
    "whatsapp": "whatsapp:",
    "chatgpt": "chatgpt",
    "telegram": "telegram",
    "slack": "slack",
    "zoom": "zoom",
    "steam": "steam://open/main",
}

WEB_APP_MAP: Dict[str, str] = {
    "whatsapp": "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://www.github.com",
    "gmail": "https://mail.google.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "chatgpt": "https://chatgpt.com",
    "reddit": "https://www.reddit.com",
    "netflix": "https://www.netflix.com",
    "linkedin": "https://www.linkedin.com",
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "amazon": "https://www.amazon.com",
    "youtube music": "https://music.youtube.com",
    "spotify web": "https://open.spotify.com",
    "google maps": "https://maps.google.com",
    "google drive": "https://drive.google.com",
    "google docs": "https://docs.google.com",
    "google sheets": "https://sheets.google.com",
    "google calendar": "https://calendar.google.com",
    "wikipedia": "https://www.wikipedia.org",
    "twitch": "https://www.twitch.tv",
    "notion": "https://www.notion.so",
}


class ApplicationLauncher:
    """Finds and starts Windows applications and web services."""

    def __init__(self) -> None:
        self._start_menu_cache: Dict[str, str] = {}
        self._start_apps_cache: Dict[str, str] = {}
        self._app_paths_cache: Dict[str, str] = {}

        self._build_start_menu_cache()
        self._build_app_paths_cache()
        self._build_start_apps_cache()

    def _build_start_menu_cache(self) -> None:
        """Index .lnk shortcut files from user and system start menus."""
        paths = [
            Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("PROGRAMDATA", "")) / r"Microsoft\Windows\Start Menu\Programs",
        ]

        for p in paths:
            if not p.exists():
                continue
            for lnk in p.glob("**/*.lnk"):
                name = lnk.stem.lower()
                self._start_menu_cache[name] = str(lnk)

    def _build_app_paths_cache(self) -> None:
        """Index executable paths registered under Windows App Paths registry keys."""
        for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            try:
                key = winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        i += 1
                        try:
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                val, _ = winreg.QueryValueEx(subkey, "")
                                clean_val = val.strip('"')
                                if os.path.exists(clean_val):
                                    norm_key = subkey_name.lower().replace(".exe", "")
                                    self._app_paths_cache[norm_key] = clean_val
                        except Exception:
                            pass
                    except OSError:
                        break
            except Exception:
                pass

    def _build_start_apps_cache(self) -> None:
        """Index all Windows applications via PowerShell Get-StartApps (UWP & Win32)."""
        try:
            ps_cmd = 'Get-StartApps | ConvertTo-Json'
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                timeout=6,
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                if isinstance(data, list):
                    for item in data:
                        name = item.get("Name", "").strip().lower()
                        appid = item.get("AppID", "").strip()
                        if name and appid:
                            self._start_apps_cache[name] = appid
                elif isinstance(data, dict):
                    name = data.get("Name", "").strip().lower()
                    appid = data.get("AppID", "").strip()
                    if name and appid:
                        self._start_apps_cache[name] = appid
        except Exception as exc:
            logger.debug("Could not query Get-StartApps: %s", exc)

    def launch(self, app_name: str) -> bool:
        """Launch an application or web app given a natural name query."""
        if not app_name or not app_name.strip():
            return False

        clean_name = app_name.strip().lower()
        # Clean common prefixes/suffixes
        for prefix in ("open ", "launch ", "start ", "run ", "the ", "app ", "a "):
            if clean_name.startswith(prefix):
                clean_name = clean_name[len(prefix):].strip()
        for suffix in (" app", " application", " program", " desktop"):
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)].strip()

        if not clean_name:
            return False

        logger.info("Attempting to launch application: '%s'", clean_name)

        # 1. Check known alias table (URIs or direct names)
        if clean_name in COMMON_APP_MAP:
            target = COMMON_APP_MAP[clean_name]
            # If target is a URI scheme (e.g. ms-settings:, spotify:, whatsapp:)
            if target.startswith("ms-") or target.endswith(":") or "://" in target:
                if self._execute_uri(target):
                    return True

            # If target exists in App Paths
            if target in self._app_paths_cache:
                if self._execute_target(self._app_paths_cache[target]):
                    return True

            # If target is on PATH
            which_target = shutil.which(target)
            if which_target and self._execute_target(which_target):
                return True

        # 2. Check Windows StartApps (Exact or Fuzzy Match)
        if clean_name in self._start_apps_cache:
            app_id = self._start_apps_cache[clean_name]
            if self._execute_start_app(app_id):
                return True

        # Fuzzy search StartApps
        best_score = 0.0
        best_app_id = None
        for name, app_id in self._start_apps_cache.items():
            score = fuzz.ratio(clean_name, name)
            if score > best_score:
                best_score = score
                best_app_id = app_id

        if best_score > 70 and best_app_id:
            logger.info("Fuzzy matched StartApp '%s' (score=%.1f)", best_app_id, best_score)
            if self._execute_start_app(best_app_id):
                return True

        # 3. Check App Paths Registry (Exact or Fuzzy)
        if clean_name in self._app_paths_cache:
            if self._execute_target(self._app_paths_cache[clean_name]):
                return True

        for name, exe_path in self._app_paths_cache.items():
            if fuzz.ratio(clean_name, name) > 75:
                if self._execute_target(exe_path):
                    return True

        # 4. Check if directly on PATH
        which_path = shutil.which(clean_name) or shutil.which(f"{clean_name}.exe")
        if which_path and self._execute_target(which_path):
            return True

        # 5. Check Start Menu .lnk shortcuts
        if clean_name in self._start_menu_cache:
            if self._execute_target(self._start_menu_cache[clean_name]):
                return True

        best_score = 0.0
        best_target = None
        for name, lnk_path in self._start_menu_cache.items():
            score = fuzz.ratio(clean_name, name)
            if score > best_score:
                best_score = score
                best_target = lnk_path

        if best_score > 70 and best_target:
            logger.info("Fuzzy launched Start Menu shortcut '%s' (score=%.1f)", best_target, best_score)
            if self._execute_target(best_target):
                return True

        # 6. Check Known Web App Fallback
        if clean_name in WEB_APP_MAP:
            logger.info("Launching known web application URL for '%s'", clean_name)
            return self._execute_uri(WEB_APP_MAP[clean_name])

        # 7. Check if user specified a domain or URL
        if clean_name.startswith(("http://", "https://")) or any(
            clean_name.endswith(tld) for tld in (".com", ".org", ".net", ".io", ".dev", ".ai")
        ):
            url = clean_name if clean_name.startswith("http") else f"https://{clean_name}"
            return self._execute_uri(url)

        # 8. As last resort, try direct os.startfile only if single token or valid short target
        words = clean_name.split()
        if len(words) <= 3 and not any(w in clean_name for w in ("profile", "selection", "card", "item", "button", "window")):
            try:
                os.startfile(clean_name)
                return True
            except Exception as exc:
                logger.warning("Direct launch failed for '%s': %s", clean_name, exc)
                return False
        else:
            logger.info("Target '%s' is not an executable application.", clean_name)
            return False

    def _execute_start_app(self, app_id: str) -> bool:
        """Launch a Windows application via explorer.exe shell:AppsFolder."""
        try:
            logger.info("Launching Windows StartApp: %s", app_id)
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{app_id}"])
            return True
        except Exception as exc:
            logger.error("Failed to launch StartApp %s: %s", app_id, exc)
            return False

    def _execute_uri(self, uri: str) -> bool:
        """Open a system URI or web URL."""
        try:
            logger.info("Opening URI: %s", uri)
            os.startfile(uri)
            return True
        except Exception as exc:
            logger.debug("Failed to open URI '%s': %s", uri, exc)
            return False

    def _execute_target(self, target: str) -> bool:
        """Launch an executable file or shortcut."""
        try:
            logger.info("Launching target path: %s", target)
            os.startfile(target)
            return True
        except Exception:
            # Fallback to direct process spawn if file exists
            if os.path.exists(target) or shutil.which(target):
                try:
                    subprocess.Popen([target] if os.path.exists(target) else target, shell=True)
                    return True
                except Exception as exc:
                    logger.error("Failed to spawn process %s: %s", target, exc)
                    return False
            return False
