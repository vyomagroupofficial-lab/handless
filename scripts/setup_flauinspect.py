"""FlaUInspect Setup and Launcher Tool for Vyoma Handless Developers.

Downloads the official FlaUInspect release (v1.4.1) from GitHub and extracts
it into the local tools/ directory. FlaUInspect allows developers to inspect
UIA properties (AutomationId, ControlType, BoundingRectangle, Name) of any
Windows desktop application in real-time.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

FLAUINSPECT_URL = "https://github.com/FlaUI/FlaUInspect/releases/download/v1.4.1/FlaUInspect.zip"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"
FLAUINSPECT_DIR = TOOLS_DIR / "FlaUInspect"
FLAUINSPECT_EXE = FLAUINSPECT_DIR / "FlaUInspect.exe"


def is_installed() -> bool:
    """Check if FlaUInspect executable exists."""
    return FLAUINSPECT_EXE.is_file()


def download_and_extract(force: bool = False) -> bool:
    """Download and extract FlaUInspect zip into tools/FlaUInspect."""
    if is_installed() and not force:
        print(f"[✓] FlaUInspect is already installed at: {FLAUINSPECT_EXE}")
        return True

    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = TOOLS_DIR / "FlaUInspect.zip"

    print(f"[*] Downloading FlaUInspect from {FLAUINSPECT_URL} ...")
    try:
        req = urllib.request.Request(
            FLAUINSPECT_URL,
            headers={"User-Agent": "Vyoma-Handless-Setup"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp, open(zip_path, "wb") as out_f:
            shutil.copyfileobj(resp, out_f)
        print(f"[✓] Downloaded to {zip_path}")
    except Exception as exc:
        print(f"[!] Failed to download FlaUInspect: {exc}")
        print("    You can manually download FlaUInspect.zip from:")
        print("    https://github.com/FlaUI/FlaUInspect/releases")
        print(f"    and extract it into: {FLAUINSPECT_DIR}")
        return False

    print(f"[*] Extracting to {FLAUINSPECT_DIR} ...")
    try:
        FLAUINSPECT_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(FLAUINSPECT_DIR)
        print(f"[✓] Extracted FlaUInspect to {FLAUINSPECT_DIR}")
    except Exception as exc:
        print(f"[!] Failed to extract zip file: {exc}")
        return False
    finally:
        if zip_path.exists():
            zip_path.unlink()

    return is_installed()


def launch_tool() -> bool:
    """Launch the FlaUInspect executable if available."""
    if not is_installed():
        print(f"[!] FlaUInspect not found at {FLAUINSPECT_EXE}. Run without --launch first to download it.")
        return False

    print(f"[*] Launching FlaUInspect ({FLAUINSPECT_EXE}) ...")
    try:
        subprocess.Popen([str(FLAUINSPECT_EXE)], shell=False)
        print("[✓] FlaUInspect launched successfully.")
        return True
    except Exception as exc:
        print(f"[!] Failed to launch FlaUInspect: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and launch FlaUInspect for UI element inspection.")
    parser.add_argument("--launch", "-l", action="store_true", help="Launch FlaUInspect after checking/installing")
    parser.add_argument("--force", "-f", action="store_true", help="Force redownload even if already present")
    parser.add_argument("--check", "-c", action="store_true", help="Check installation status only")

    args = parser.parse_args()

    if args.check:
        if is_installed():
            print(f"[✓] FlaUInspect is installed at {FLAUINSPECT_EXE}")
            return 0
        else:
            print("[x] FlaUInspect is NOT installed.")
            return 1

    if not is_installed() or args.force:
        success = download_and_extract(force=args.force)
        if not success:
            return 1

    if args.launch:
        return 0 if launch_tool() else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
