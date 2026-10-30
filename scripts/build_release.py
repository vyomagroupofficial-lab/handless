"""Automated Release Build Script for Vyoma Handless.

Compiles Vyoma Handless into a standalone Windows binary via PyInstaller
and packages it with all necessary assets, configurations, and runtime dependencies.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
ASSETS_DIR = ROOT_DIR / "src" / "handless" / "assets"
ICON_PNG = ASSETS_DIR / "handless-bot-withoutbg.png"


def build_executable():
    print("=" * 60)
    print("  Vyoma Handless — Standalone Windows Release Compiler")
    print("=" * 60)

    # 1. Clean previous build artifacts
    for p in (DIST_DIR, BUILD_DIR):
        if p.exists():
            print(f"Cleaning {p}...")
            shutil.rmtree(p, ignore_errors=True)

    # 2. PyInstaller command line
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        "VyomaHandless",
        "--paths",
        str(ROOT_DIR / "src"),
        # Custom hooks dir to override broken webrtcvad hook
        "--additional-hooks-dir",
        str(ROOT_DIR / "hooks"),
        # Add assets
        "--add-data",
        f"{ASSETS_DIR};handless/assets",
        # Hidden imports
        "--hidden-import",
        "pydantic",
        "--hidden-import",
        "keyring.backends.Windows",
        "--hidden-import",
        "pywinauto",
        "--hidden-import",
        "pywinauto.controls.uia_controls",
        "--hidden-import",
        "pywinauto.controls.uiawrapper",
        "--hidden-import",
        "comtypes",
        "--hidden-import",
        "sounddevice",
        "--hidden-import",
        "httpx",
        "--hidden-import",
        "websockets",
        "--hidden-import",
        "google.genai",
        "--hidden-import",
        "mss",
        "--hidden-import",
        "PIL",
        # Entrypoint script
        str(ROOT_DIR / "src" / "handless" / "app.py"),
    ]

    print("\nRunning PyInstaller build...")
    print(" ".join(cmd))
    res = subprocess.run(cmd, cwd=str(ROOT_DIR))

    if res.returncode != 0:
        print("\n[ERROR] PyInstaller build failed with exit code:", res.returncode)
        sys.exit(res.returncode)

    out_exe = DIST_DIR / "VyomaHandless" / "VyomaHandless.exe"
    if out_exe.exists():
        size_mb = out_exe.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 60)
        print(f"  [SUCCESS] Binary compiled successfully: {out_exe}")
        print(f"  Main Executable Size: {size_mb:.2f} MB")
        print("=" * 60)

        # Create a release ZIP
        zip_path = DIST_DIR / "VyomaHandless-v0.1.0-windows-x64.zip"
        print(f"\nPackaging portable release zip: {zip_path}...")
        shutil.make_archive(
            str(DIST_DIR / "VyomaHandless-v0.1.0-windows-x64"),
            "zip",
            root_dir=str(DIST_DIR),
            base_dir="VyomaHandless",
        )
        print(f"Release archive created: {zip_path} ({zip_path.stat().st_size / (1024*1024):.2f} MB)")
    else:
        print("\n[ERROR] Output executable not found at:", out_exe)
        sys.exit(1)


if __name__ == "__main__":
    build_executable()
