"""Automated Release Build Script for Vyoma Handless.

Compiles Vyoma Handless into a standalone Windows binary via PyInstaller, then
packages it as:
  * dist/VyomaHandless-Setup-<version>.exe   guided installer (Inno Setup 6)
  * dist/VyomaHandless-v<version>-windows-x64.zip   portable build

Pass --no-installer to skip the Inno Setup step.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
ASSETS_DIR = ROOT_DIR / "src" / "handless" / "assets"
ICON_PNG = ASSETS_DIR / "handless-bot-withoutbg.png"
PACKAGING_DIR = ROOT_DIR / "packaging"
ICON_ICO = PACKAGING_DIR / "handless.ico"
INSTALLER_ISS = PACKAGING_DIR / "installer.iss"


def read_version() -> str:
    text = (ROOT_DIR / "src" / "handless" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', text)
    if not match:
        raise SystemExit("Could not read __version__ from src/handless/__init__.py")
    return match.group(1)


def write_version_file(version: str) -> Path:
    """Windows VERSIONINFO resource so Task Manager and Explorer show the product name."""
    parts = [int(p) for p in re.findall(r"\d+", version)[:4]]
    parts += [0] * (4 - len(parts))
    tup = tuple(parts)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    path = BUILD_DIR / "version_info.txt"
    path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tup}, prodvers={tup}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Vyoma Group'),
      StringStruct('FileDescription', 'Vyoma Handless'),
      StringStruct('FileVersion', '{version}'),
      StringStruct('InternalName', 'VyomaHandless'),
      StringStruct('OriginalFilename', 'VyomaHandless.exe'),
      StringStruct('ProductName', 'Vyoma Handless'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return path


WHISPER_DIR = ROOT_DIR / "models" / "sherpa-onnx-whisper-base.en"
WHISPER_FILES = ("base.en-encoder.int8.onnx", "base.en-decoder.int8.onnx", "base.en-tokens.txt")


def bundled_model_args() -> list:
    """Bundle the offline Whisper int8 model so voice works without any API key.

    Fetch it first with: python scripts/fetch_whisper_model.py
    """
    missing = [f for f in WHISPER_FILES if not (WHISPER_DIR / f).exists()]
    if missing:
        print(f"[WARNING] Offline Whisper model not bundled (missing {', '.join(missing)}).")
        return []
    args = []
    for f in WHISPER_FILES:
        args += ["--add-data", f"{WHISPER_DIR / f};models/{WHISPER_DIR.name}"]
    return args


def find_iscc() -> Path | None:
    candidates = [
        os.environ.get("ISCC_PATH", ""),
        shutil.which("iscc") or "",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Inno Setup 6", "ISCC.exe"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return Path(c)
    return None


def build_installer(version: str) -> Path:
    iscc = find_iscc()
    if iscc is None:
        raise SystemExit("[ERROR] Inno Setup 6 (ISCC.exe) not found. Install it: winget install JRSoftware.InnoSetup")
    source_dir = DIST_DIR / "VyomaHandless"
    print(f"\nCompiling installer with {iscc}...")
    # Compress through a temp folder next to the build, not the (possibly full) system drive
    tmp_dir = BUILD_DIR / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, TMP=str(tmp_dir), TEMP=str(tmp_dir))
    res = subprocess.run(
        [str(iscc), "/Qp", f"/DAppVersion={version}", f"/DSourceDir={source_dir}", str(INSTALLER_ISS)],
        cwd=str(PACKAGING_DIR),
        env=env,
    )
    if res.returncode != 0:
        raise SystemExit(f"[ERROR] Inno Setup failed with exit code {res.returncode}")
    setup = DIST_DIR / f"VyomaHandless-Setup-{version}.exe"
    print(f"Installer created: {setup} ({setup.stat().st_size / (1024*1024):.2f} MB)")
    return setup


def build_executable(make_installer: bool = True):
    version = read_version()
    print("=" * 60)
    print("  Vyoma Handless — Standalone Windows Release Compiler")
    print("=" * 60)

    # 1. Clean previous build artifacts
    for p in (DIST_DIR, BUILD_DIR):
        if p.exists():
            print(f"Cleaning {p}...")
            shutil.rmtree(p, ignore_errors=True)

    version_file = write_version_file(version)

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
        "--icon",
        str(ICON_ICO),
        "--version-file",
        str(version_file),
        "--paths",
        str(ROOT_DIR / "src"),
        # Custom hooks dir to override broken webrtcvad hook
        "--additional-hooks-dir",
        str(ROOT_DIR / "hooks"),
        # Add assets
        "--add-data",
        f"{ASSETS_DIR};handless/assets",
        *bundled_model_args(),
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
        "--hidden-import",
        "sherpa_onnx",
        # Packages that load native DLLs from their own folder at import time
        "--collect-all",
        "vosk",
        "--collect-all",
        "sherpa_onnx",
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
        zip_base = DIST_DIR / f"VyomaHandless-v{version}-windows-x64"
        zip_path = Path(f"{zip_base}.zip")  # not with_suffix: the version's dots look like a suffix
        print(f"\nPackaging portable release zip: {zip_path}...")
        shutil.make_archive(
            str(zip_base),
            "zip",
            root_dir=str(DIST_DIR),
            base_dir="VyomaHandless",
        )
        print(f"Release archive created: {zip_path} ({zip_path.stat().st_size / (1024*1024):.2f} MB)")

        if make_installer:
            build_installer(version)
    else:
        print("\n[ERROR] Output executable not found at:", out_exe)
        sys.exit(1)


if __name__ == "__main__":
    build_executable(make_installer="--no-installer" not in sys.argv)
