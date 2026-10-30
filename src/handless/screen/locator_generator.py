"""Multi-Modal Resilient Locator Generator ("Dynamic-First, Coordinate-Fallback").

Generates production-grade, 3-tier resilient automation locators for any inspected element:
- Tier 1 (Primary Dynamic): Unique AutomationId or exact Name + ControlType.
- Tier 2 (Secondary Structural): Proximity anchor relative to sibling labels (e.g. "below label 'Username'").
- Tier 3 (Tertiary Coordinate & Vision): Normalized percentage coordinates (x_pct, y_pct) with OCR text fallback.

Produces executable Python snippets, voice command triggers, and macro workflow steps.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ResilientLocator:
    """Comprehensive 3-tier resilient locator definition for a UI element."""

    element_name: str
    control_type: str
    auto_id: str

    # Tier 1: Dynamic UIA Locator
    tier1_dynamic: Dict[str, Any]

    # Tier 2: Structural / Proximity Anchor Locator
    tier2_structural: Dict[str, Any]

    # Tier 3: Coordinate & Vision Fallback Locator
    tier3_coordinate: Dict[str, Any]

    # Natural voice trigger syntax
    voice_command: str

    # Executable Python code snippet
    python_code: str

    # JSON-serializable macro action dict
    macro_action: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def generate_resilient_locator(
    element: Dict[str, Any],
    window_rect: Optional[Dict[str, int]] = None,
    siblings: Optional[List[Dict[str, Any]]] = None,
) -> ResilientLocator:
    """Generate a 3-tier resilient locator recipe for an inspected UI element."""
    name = (element.get("name") or "").strip()
    auto_id = (element.get("auto_id") or "").strip()
    ctype = (element.get("control_type") or "Control").strip()
    rect = element.get("rect", {})

    left = rect.get("left", 0)
    top = rect.get("top", 0)
    width = rect.get("width", 0)
    height = rect.get("height", 0)
    cx = left + (width // 2)
    cy = top + (height // 2)

    # -----------------------------------------------------------------------
    # Tier 1: Primary Dynamic Locator
    # -----------------------------------------------------------------------
    tier1: Dict[str, Any] = {
        "strategy": "dynamic_uia",
        "confidence": 1.0,
    }
    if auto_id:
        tier1["auto_id"] = auto_id
        tier1["control_type"] = ctype
        tier1_code = f'window.child_window(auto_id="{auto_id}", control_type="{ctype}")'
    elif name:
        tier1["title"] = name
        tier1["control_type"] = ctype
        tier1_code = f'window.child_window(title="{name}", control_type="{ctype}")'
    else:
        tier1["control_type"] = ctype
        tier1["index"] = 0
        tier1_code = f'window.child_window(control_type="{ctype}")'
    tier1["code"] = tier1_code

    # -----------------------------------------------------------------------
    # Tier 2: Secondary Structural / Proximity Anchor Locator
    # -----------------------------------------------------------------------
    tier2: Dict[str, Any] = {
        "strategy": "structural_anchor",
        "anchor_name": None,
        "relation": None,
        "code": None,
    }
    if siblings:
        nearest_anchor = _find_nearest_label_anchor(left, top, siblings, current_name=name)
        if nearest_anchor:
            anchor_name, relation = nearest_anchor
            tier2["anchor_name"] = anchor_name
            tier2["relation"] = relation
            tier2["control_type"] = ctype
            tier2["code"] = (
                f'find_element("{name or ctype}", target_type="{ctype}", '
                f'relative_anchor="{anchor_name}", relative_relation="{relation}")'
            )

    if not tier2["code"]:
        tier2["code"] = f'find_element("{name or ctype}", target_type="{ctype}")'

    # -----------------------------------------------------------------------
    # Tier 3: Tertiary Coordinate & Vision Fallback Locator
    # -----------------------------------------------------------------------
    tier3: Dict[str, Any] = {
        "strategy": "coordinate_vision_fallback",
        "absolute_coords": {"x": cx, "y": cy, "width": width, "height": height},
        "normalized_pct": None,
        "ocr_label": name,
    }

    if window_rect and window_rect.get("width", 0) > 0 and window_rect.get("height", 0) > 0:
        win_w = window_rect["width"]
        win_h = window_rect["height"]
        win_l = window_rect.get("left", 0)
        win_t = window_rect.get("top", 0)

        rel_x = max(0, cx - win_l) / win_w
        rel_y = max(0, cy - win_t) / win_h
        rel_w = width / win_w
        rel_h = height / win_h

        tier3["normalized_pct"] = {
            "x_pct": round(rel_x, 3),
            "y_pct": round(rel_y, 3),
            "w_pct": round(rel_w, 3),
            "h_pct": round(rel_h, 3),
        }
        tier3["code"] = f'click_relative_coords(window, x_pct={round(rel_x, 3)}, y_pct={round(rel_y, 3)})'
    else:
        tier3["code"] = f'pyautogui.click({cx}, {cy})'

    # -----------------------------------------------------------------------
    # Voice Command & Executable Code
    # -----------------------------------------------------------------------
    if ctype in ("Edit", "TextBox"):
        voice_command = f'type into "{name}"' if name else 'type text'
    else:
        voice_command = f'click "{name}"' if name else f'click {ctype}'

    python_snippet = f"""# Resilient 3-Tier Locator for '{name or ctype}'
def locate_and_click(window):
    # Tier 1: Dynamic UIA Match
    try:
        elem = {tier1["code"]}
        if elem.exists(timeout=0.3):
            elem.click_input()
            return True
    except Exception:
        pass

    # Tier 2: Structural Proximity Match
    try:
        elem = {tier2["code"]}
        if elem:
            elem.click_input()
            return True
    except Exception:
        pass

    # Tier 3: Coordinate Fallback
    {tier3["code"]}
    return True
"""

    macro_action = {
        "action": "click" if ctype != "Edit" else "type",
        "target": name or auto_id or ctype,
        "control_type": ctype,
        "auto_id": auto_id,
        "coords": [cx, cy],
        "voice_command": voice_command,
    }

    return ResilientLocator(
        element_name=name,
        control_type=ctype,
        auto_id=auto_id,
        tier1_dynamic=tier1,
        tier2_structural=tier2,
        tier3_coordinate=tier3,
        voice_command=voice_command,
        python_code=python_snippet,
        macro_action=macro_action,
    )


def _find_nearest_label_anchor(
    elem_left: int,
    elem_top: int,
    siblings: List[Dict[str, Any]],
    current_name: str = "",
) -> Optional[Tuple[str, str]]:
    """Find the nearest text/label sibling to serve as an anchor (e.g., above or left)."""
    best_anchor: Optional[str] = None
    best_relation: Optional[str] = None
    min_dist = 999999

    for sib in siblings:
        s_name = (sib.get("name") or "").strip()
        s_type = sib.get("control_type", "")
        if not s_name or s_name == current_name:
            continue
        if s_type not in ("Text", "Label", "Header", "Hyperlink"):
            continue

        s_rect = sib.get("rect", {})
        s_l = s_rect.get("left", 0)
        s_t = s_rect.get("top", 0)

        # 1. Label directly above input (e.g. password field)
        if s_t < elem_top and abs(s_l - elem_left) < 150:
            dist = elem_top - s_t
            if dist < min_dist and dist < 120:
                min_dist = dist
                best_anchor = s_name
                best_relation = "below"

        # 2. Label directly to the left (e.g. form fields)
        elif s_l < elem_left and abs(s_t - elem_top) < 40:
            dist = elem_left - s_l
            if dist < min_dist and dist < 250:
                min_dist = dist
                best_anchor = s_name
                best_relation = "right_of"

    if best_anchor and best_relation:
        return (best_anchor, best_relation)
    return None

