"""Application Launcher for Windows.

Locates and launches Windows desktop applications via known executable aliases,
system URI schemes, Start Menu shortcut indexes, and os.startfile.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

COMMON_APP_MAP: Dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "file explorer": "explorer",
    "explorer": "explorer",
    "terminal": "wt",
    "windows terminal": "wt",
    "cmd": "cmd",
    "command prompt": "cmd",
    "powershell": "powershell",
    "vs code": "code",
    "visual studio code": "code",
    "spotify": "spotify",
    "discord": "discord",
    "settings": "ms-settings:",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "task manager": "taskmgr",
}


class ApplicationLauncher:
    """Finds and starts Windows applications."""

    def __init__(self) -> None:
        self._start_menu_cache: Dict[str, str] = {}
        self._build_start_menu_cache()

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

    def launch(self, app_name: str) -> bool:
        """Launch an application given a natural name query."""
        clean_name = app_name.strip().lower()

        # 1. Check known alias table
        if clean_name in COMMON_APP_MAP:
            target = COMMON_APP_MAP[clean_name]
            if self._execute_target(target):
                return True

        # 2. Check if it's directly on PATH
        which_path = shutil.which(clean_name)
        if which_path and self._execute_target(which_path):
            return True

        # 3. Check Start Menu shortcuts using exact and fuzzy matching
        if clean_name in self._start_menu_cache:
            if self._execute_target(self._start_menu_cache[clean_name]):
                return True

        # Fuzzy search start menu shortcuts
        best_score = 0.0
        best_target = None
        for name, lnk_path in self._start_menu_cache.items():
            score = fuzz.ratio(clean_name, name)
            if score > best_score:
                best_score = score
                best_target = lnk_path

        if best_score > 70 and best_target:
            logger.info("Fuzzy launched Start Menu shortcut '%s' (score=%.1f)", best_target, best_score)
            return self._execute_target(best_target)

        # 4. As last resort, try direct os.startfile
        return self._execute_target(clean_name)

    def _execute_target(self, target: str) -> bool:
        try:
            logger.info("Launching target: %s", target)
            if target.startswith("ms-"):
                os.startfile(target)
                return True

            # Use os.startfile for Windows shell associations (.lnk, urls, exes)
            os.startfile(target)
            return True
        except Exception:
            # Fallback to subprocess
            try:
                subprocess.Popen(target, shell=True)
                return True
            except Exception as exc:
                logger.error("Failed to launch %s: %s", target, exc)
                return False
