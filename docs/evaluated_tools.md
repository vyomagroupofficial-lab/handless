# Repository & Tooling Evaluation: Microsoft winapp CLI

This document records the architectural evaluation of the [Microsoft winapp CLI](https://github.com/microsoft/winappCli) for the Vyoma Handless project.

---

## 1. Tool Overview

`winapp` is an open-source command-line tool developed by Microsoft designed for modern Windows Application SDK (WinAppSDK / WinUI 3) developer workflows.

### Primary Capabilities
- **Windows SDK Management**: Discovering, installing, and managing Windows SDK versions.
- **Application Identity & Manifests**: Generating and validating `AppxManifest.xml` files and Windows app identity.
- **Package Management & Signing**: Packaging applications into MSIX bundles and managing developer code-signing certificates.
- **Build Orchestration**: Building and deploying native C++ or C# WinUI 3 / XAML applications.

---

## 2. Evaluation for Vyoma Handless

| Evaluation Criterion | Vyoma Handless Architecture | winapp CLI Fit |
|---|---|---|
| **Runtime Language** | Python 3.11+ (CPython) | Native C++ / C# Windows App SDK (WinUI 3) |
| **GUI Framework** | PySide6 (Qt for Python) | XAML / WinUI 3 |
| **Automation Engine** | Microsoft UI Automation COM (via `pywinauto`) | Windows SDK Packaging Tooling |
| **Distribution Format** | Portable `.exe` (PyInstaller) / `pip install` | MSIX / AppX packages |
| **Runtime Dependencies** | Standalone Python packages (`pyproject.toml`) | External CLI tool (not importable in Python) |

### Verdict: **Skip (No Runtime or Build Integration)**

`winapp` CLI addresses Windows App SDK build and MSIX packaging requirements. Vyoma Handless does not use WinAppSDK, XAML, or MSIX packaging. Adding `winapp` to the runtime or developer dependencies would add substantial external toolchain complexity with zero functional value to voice capture, intent parsing, UI Automation, or screen interaction.

---

## 3. Future Reconsideration Triggers

The decision not to integrate `winapp` should be revisited only if:
1. **Windows Store Distribution**: Handless is packaged for the Microsoft Store as a sandboxed or packaged MSIX app.
2. **Native WinAppSDK Shell**: The front-end user interface is rewritten from PySide6 to native C#/WinUI 3.
3. **App Identity Requirements**: Handless requires packaged Windows App Identity for specific Windows 11 system notification APIs or background task registrations that unpackaged Win32/Python applications cannot access.
