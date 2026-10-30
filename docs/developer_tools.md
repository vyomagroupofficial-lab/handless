# Developer Tools & UI Inspection Guide

This guide explains how to use UI inspection tools—specifically **FlaUInspect** and the built-in `handless diag` utility—to discover control properties across Windows applications and improve element targeting in Vyoma Handless.

---

## 1. FlaUInspect Overview

[FlaUInspect](https://github.com/FlaUI/FlaUInspect) is an open-source, WPF-based UI Automation inspection tool built on the FlaUI library. It functions as a modern, reliable replacement for Microsoft's legacy `Inspect.exe`.

### Key Capabilities
- **Real-time Hover Inspection**: Hover over any UI element on screen to highlight its bounding box and display its UIA tree path.
- **Full UIA Property Inspection**: Inspect `AutomationId`, `ControlType`, `Name`, `ClassName`, `BoundingRectangle`, `IsEnabled`, `IsOffscreen`, and supported UIA control patterns.
- **UIA2 and UIA3 Mode Switching**: View properties in both legacy UI Automation (UIA2) and modern COM-based UI Automation (UIA3).

---

## 2. Installation & Quickstart

Use the bundled helper script to download and launch FlaUInspect:

```powershell
# 1. Download and extract FlaUInspect to tools/FlaUInspect/
python scripts/setup_flauinspect.py

# 2. Download (if needed) and launch the GUI immediately:
python scripts/setup_flauinspect.py --launch

# 3. Check installation status:
python scripts/setup_flauinspect.py --check
```

The tool is downloaded from official GitHub releases and placed into `tools/FlaUInspect/FlaUInspect.exe`. The `tools/` directory is excluded in `.gitignore` so binaries remain out of version control.

---

## 3. Inspected Properties & Handless Mapping

When you inspect an element in FlaUInspect, several core properties map directly into Handless automation subsystems:

| FlaUInspect Property | Description | Handless Usage |
|---|---|---|
| **`AutomationId`** | Unique developer-assigned identifier for a control | Passed into `UIAInspector.find_element_targeted(auto_id=...)` and heavily prioritized in `element_matcher.py` (weight: 100). |
| **`ControlType`** | UIA Control Type (e.g. `Button`, `Edit`, `ComboBox`, `MenuItem`) | Mapped via `CONTROL_TYPE_MAP` in `uia_inspector.py` to filter candidates and speed up `child_window()` searches. |
| **`Name`** | Accessible text label or window text | Compared against voice command targets using exact matching and fuzzy token similarity (`RapidFuzz`) in `element_matcher.py`. |
| **`BoundingRectangle`** | Screen coordinates `(left, top, right, bottom)` | Centroid coordinates `(cx, cy)` are calculated for fallback mouse clicking when COM invocation fails. |
| **`PatternsSupported`** | Available automation patterns (e.g. `Invoke`, `Value`, `ExpandCollapse`, `SelectionItem`) | Used by `ElementOperations` in `element_ops.py` to select, expand, collapse, or type directly into controls. |

---

## 4. Practical Workflow: Improving Element Matching

When adding support for a tricky or custom desktop application:

1. **Launch FlaUInspect**:
   ```powershell
   python scripts/setup_flauinspect.py --launch
   ```
2. **Hover over the target control**:
   Move the mouse over the control in the target application (e.g. a "Save" icon or search box in Spotify or VS Code).
3. **Inspect the Properties Panel**:
   - Note whether `Name` is populated (e.g. `"Search"`).
   - Check if an `AutomationId` exists (e.g. `"search-input"` or `"btnSave"`).
   - Check the `ControlType` (e.g. `"Edit"` vs `"Pane"` vs `"Custom"`).
4. **Use in Handless Code or Tests**:
   - If `AutomationId` is static and known, use targeted search:
     ```python
     elem = uia_inspector.find_element_targeted(target_name="Save", auto_id="btnSave", target_type="button")
     ```
   - If the application uses non-standard control types (e.g. a `Pane` behaving like a `Button`), update `CONTROL_TYPE_MAP` in `src/handless/screen/uia_inspector.py` or tune matching rules in `src/handless/screen/element_matcher.py`.

---

## 5. Built-in CLI Diagnostics: `handless diag`

For rapid command-line inspections without opening a GUI, Handless includes a built-in diagnostics command:

```powershell
# Dump the control tree of the currently active window (default depth: 3)
python -m handless.app diag

# Specify a custom depth:
python -m handless.app diag 2
```

This uses `pywinauto`'s native control tree dumper to output all descendant controls, class names, and automation IDs directly in your terminal. This structured output is also automatically fed into Google Gemini vision context prompts during complex command disambiguation.
