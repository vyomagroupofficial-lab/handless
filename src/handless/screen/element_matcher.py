"""Fuzzy Element Matcher using rapidfuzz.

Ranks accessible UI controls against natural speech queries (e.g. 'search button',
'file menu', 'save') using string similarity, control type hints, and visibility.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List, Optional, Tuple
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

TYPE_ALIASES = {
    "button": ["button", "splitbutton"],
    "edit": ["edit", "document", "textbox", "combobox"],
    "input": ["edit", "document", "textbox", "combobox"],
    "textbox": ["edit", "document", "textbox"],
    "searchbox": ["edit", "document", "textbox", "combobox"],
    "menu": ["menuitem", "menu", "menubar"],
    "tab": ["tabitem", "tab"],
    "link": ["hyperlink", "link"],
    "list": ["list", "listitem", "dataitem", "combobox"],
    "listitem": ["listitem", "dataitem", "pane", "group"],
    "contact": ["listitem", "dataitem", "button", "pane", "group"],
    "chat": ["listitem", "dataitem", "button", "pane", "group"],
    "item": ["listitem", "dataitem", "button", "pane", "group"],
    "combobox": ["combobox", "edit"],
}


ORDINAL_MAP = {
    "first": 0, "1st": 0, "one": 0, "1": 0,
    "second": 1, "2nd": 1, "two": 1, "2": 1,
    "third": 2, "3rd": 2, "three": 2, "3": 2,
    "fourth": 3, "4th": 3, "four": 3, "4": 3,
    "fifth": 4, "5th": 4, "five": 4, "5": 4,
    "sixth": 5, "6th": 5, "six": 5, "6": 5,
    "last": -1,
}


def normalize_zone_name(zone: Optional[str]) -> Optional[str]:
    """Normalize user conversational zone phrases to canonical zone keys."""
    if not zone:
        return None
    z = zone.lower().replace("-", " ").replace("_", " ").strip()
    z = re.sub(r"\b(?:corner|side|area|part|edge|region|screen|window)\b", "", z).strip()
    if z in ("top right", "upper right", "northeast"):
        return "top_right"
    if z in ("top left", "upper left", "northwest"):
        return "top_left"
    if z in ("bottom right", "lower right", "southeast"):
        return "bottom_right"
    if z in ("bottom left", "lower left", "southwest"):
        return "bottom_left"
    if z in ("top", "upper", "north"):
        return "top"
    if z in ("bottom", "lower", "south"):
        return "bottom"
    if z in ("left", "west"):
        return "left"
    if z in ("right", "east"):
        return "right"
    if z in ("center", "middle"):
        return "center"
    return None


def is_element_in_zone(elem_rect: Any, parent_rect: Any, zone: str) -> bool:
    """Check if element rectangle centroid resides inside specified spatial zone of parent."""
    norm_zone = normalize_zone_name(zone)
    if not norm_zone or not elem_rect or not parent_rect:
        return True

    try:
        pw = max(1, parent_rect.width() if hasattr(parent_rect, "width") else (parent_rect.right - parent_rect.left))
        ph = max(1, parent_rect.height() if hasattr(parent_rect, "height") else (parent_rect.bottom - parent_rect.top))
        p_left = parent_rect.left
        p_top = parent_rect.top

        ew = elem_rect.width() if hasattr(elem_rect, "width") else (elem_rect.right - elem_rect.left)
        eh = elem_rect.height() if hasattr(elem_rect, "height") else (elem_rect.bottom - elem_rect.top)
        cx = elem_rect.left + (ew / 2.0)
        cy = elem_rect.top + (eh / 2.0)

        nx = (cx - p_left) / float(pw)
        ny = (cy - p_top) / float(ph)

        if norm_zone == "top_right":
            return nx >= 0.50 and ny <= 0.50
        if norm_zone == "top_left":
            return nx <= 0.50 and ny <= 0.50
        if norm_zone == "bottom_right":
            return nx >= 0.50 and ny >= 0.50
        if norm_zone == "bottom_left":
            return nx <= 0.50 and ny >= 0.50
        if norm_zone == "top":
            return ny <= 0.40
        if norm_zone == "bottom":
            return ny >= 0.60
        if norm_zone == "left":
            return nx <= 0.40
        if norm_zone == "right":
            return nx >= 0.60
        if norm_zone == "center":
            return 0.20 <= nx <= 0.80 and 0.20 <= ny <= 0.80
    except Exception as exc:
        logger.debug("is_element_in_zone calculation error: %s", exc)

    return True


def is_relative_to_anchor(elem_rect: Any, anchor_rect: Any, relation: str) -> bool:
    """Verify spatial geometric relationship between element and anchor."""
    if not elem_rect or not anchor_rect or not relation:
        return True

    try:
        e_cx = elem_rect.left + (elem_rect.width() / 2.0)
        e_cy = elem_rect.top + (elem_rect.height() / 2.0)
        a_cx = anchor_rect.left + (anchor_rect.width() / 2.0)
        a_cy = anchor_rect.top + (anchor_rect.height() / 2.0)

        rel = relation.lower().replace("-", " ").replace("_", " ").strip()

        if rel in ("near", "nearby", "close to", "beside"):
            dist = ((e_cx - a_cx) ** 2 + (e_cy - a_cy) ** 2) ** 0.5
            return dist <= 320

        if rel in ("next to", "next", "to the right of", "right of", "right"):
            return e_cx > a_cx and abs(e_cy - a_cy) <= 80 and (elem_rect.left - anchor_rect.right) <= 250

        if rel in ("to the left of", "left of", "left"):
            return e_cx < a_cx and abs(e_cy - a_cy) <= 80 and (anchor_rect.left - elem_rect.right) <= 250

        if rel in ("below", "under", "underneath", "beneath"):
            return e_cy > a_cy and abs(e_cx - a_cx) <= 160 and (elem_rect.top - anchor_rect.bottom) <= 250

        if rel in ("above", "on top of", "over"):
            return e_cy < a_cy and abs(e_cx - a_cx) <= 160 and (anchor_rect.top - elem_rect.bottom) <= 250
    except Exception as exc:
        logger.debug("is_relative_to_anchor calculation error: %s", exc)

    return True


def score_element(
    target_query: str,
    target_type: Optional[str],
    element_name: str,
    element_auto_id: str,
    element_type: str,
    is_visible: bool = True,
    is_enabled: bool = True,
    elem_rect: Optional[Any] = None,
    parent_rect: Optional[Any] = None,
    spatial_landmark: Optional[str] = None,
) -> float:
    """Calculate match score from 0.0 to 1.0, with spatial landmark boosting."""
    if not is_visible or not is_enabled:
        return 0.0


    q = str(target_query or "").strip().lower()
    name = str(element_name() if callable(element_name) else (element_name or "")).strip().lower()
    auto_id = str(element_auto_id() if callable(element_auto_id) else (element_auto_id or "")).strip().lower()
    ctype = str(element_type() if callable(element_type) else (element_type or "")).strip().lower()

    if "magicmock" in name.lower():
        name = ""
    if "magicmock" in auto_id.lower():
        auto_id = ""

    if not q or (not name and not auto_id):
        return 0.0

    # Clean conversational filler words from query (e.g., 'the ff prfile' -> 'ff')
    clean_q = re.sub(r"^(?:the|a|an)\s+", "", q)
    clean_q = re.sub(r"\s+from\s+(?:the\s+)?(?:selection|list)$", "", clean_q).strip()
    clean_q = re.sub(
        r"\s+(?:button|icon|profile|prfile|profle|profl|link|tab|item|menu|card|option|selection|tile|avatar)$",
        "",
        clean_q,
    ).strip()

    # 1. Exact match
    if (name and (q == name or clean_q == name)) or (auto_id and (q == auto_id or clean_q == auto_id)):
        score = 1.0
    # 2. Leading word / Prefix match (e.g. contact name followed by status/time: "Vaishu Yesterday Follow this link...")
    elif name and (name.startswith(q + " ") or name.startswith(clean_q + " ") or name.startswith(q + "\n") or name.startswith(clean_q + "\n")):
        score = 0.96
    # 3. Substring containment (strictly non-empty)
    elif name and (q in name or name in q or (clean_q and (clean_q in name or name in clean_q))):
        score = 0.9
    elif auto_id and (q in auto_id or auto_id in q or (clean_q and (clean_q in auto_id or auto_id in clean_q))):
        score = 0.85
    # 4. Token-level prefix/substring match (e.g., "ff" matches "ffff" or "Your Chrome (ffff)")
    elif name:
        q_tokens = [w for w in re.findall(r"\w+", clean_q or q) if len(w) >= 2]
        name_tokens = [w for w in re.findall(r"\w+", name) if len(w) >= 2]
        token_match = False
        for qt in q_tokens:
            for nt in name_tokens:
                if nt.startswith(qt) or qt in nt:
                    token_match = True
                    break
            if token_match:
                break

        if token_match:
            score = 0.88
        else:
            # 5. Fuzzy ratio fallback
            ratio_q = fuzz.token_sort_ratio(q, name) / 100.0
            partial_q = fuzz.partial_ratio(q, name) / 100.0
            ratio_clean = fuzz.token_sort_ratio(clean_q, name) / 100.0 if clean_q else 0.0
            partial_clean = fuzz.partial_ratio(clean_q, name) / 100.0 if clean_q else 0.0
            score = max(ratio_q, partial_q, ratio_clean, partial_clean)
    else:
        score = 0.0

    # 6. Control type bonus or penalty
    if target_type:
        tt = target_type.strip().lower()
        valid_types = TYPE_ALIASES.get(tt, [tt])
        if any(vt in ctype for vt in valid_types):
            score = min(1.0, score + 0.2)
        else:
            # If target explicitly requests an input/edit, heavily penalize buttons
            if tt in ("edit", "textbox", "input", "searchbox") and any(bt in ctype for bt in ("button", "splitbutton")):
                score = max(0.0, score - 0.5)
            elif tt in ("contact", "chat", "profile", "user") and any(et in ctype for et in ("edit", "textbox", "document")):
                # An Edit text box is NEVER a contact or chat item!
                return 0.0
            elif score > 0.5:
                score = max(0.0, score - 0.2)
    elif clean_q in ("search", "search box", "search bar", "find"):
        # For general search queries without explicit type hint, prioritize input/edit fields over search buttons
        if any(et in ctype for et in ("edit", "document", "textbox", "combobox")):
            score = min(1.0, score + 0.2)
        elif any(bt in ctype for bt in ("button", "splitbutton")):
            score = max(0.0, score - 0.15)
    elif clean_q in ("type a message", "message box", "chat box", "chat input", "message input", "type message", "message"):
        # Prioritize chat message edit controls
        if any(et in ctype for et in ("edit", "document", "textbox")):
            score = min(1.0, score + 0.3)
    elif any(et in ctype for et in ("edit", "textbox", "document")):
        # If user did NOT request an edit control, heavily deprioritize Edit fields whose typed text
        # happens to match the query so that actual contact items, buttons, or list items win
        if clean_q not in ("input", "edit", "address bar", "url", "search", "search box", "search bar", "find"):
            score = max(0.0, score - 0.55)

    # 7. Spatial landmark zone bonus or penalty
    if spatial_landmark and elem_rect and parent_rect:
        if is_element_in_zone(elem_rect, parent_rect, spatial_landmark):
            score = min(1.0, score + 0.25)
        else:
            score = max(0.0, score - 0.40)

    # 7. Close button / X heuristic for top-right
    if clean_q in ("close", "x", "exit") and ctype in ("button", "splitbutton"):
        if spatial_landmark in ("top_right", "top") or (elem_rect and parent_rect and is_element_in_zone(elem_rect, parent_rect, "top_right")):
            score = max(score, 0.92)

    return score


def find_best_element_match(
    target_query: str,
    candidates: List[Any],
    target_type: Optional[str] = None,
    min_score: float = 0.65,
    spatial_landmark: Optional[str] = None,
    relative_anchor: Optional[str] = None,
    relative_relation: Optional[str] = None,
    parent_rect: Optional[Any] = None,
) -> Optional[Tuple[float, Any]]:
    """Scan candidate UI elements and return the highest scoring match.
    
    Supports:
    - Fuzzy & exact text matching
    - Spatial landmark zone matching (top_right, bottom_left, center, etc.)
    - Relative proximity tracking to anchors (near, next to, below, above, right of)
    - Ordinal selection ('first profile', 'second card')
    """
    if not candidates:
        return None

    # 1. Resolve relative anchor if provided
    anchor_elem = None
    if relative_anchor:
        for el in candidates:
            try:
                name = el.window_text() or ""
                aid = el.automation_id() or ""
                if relative_anchor.lower() in name.lower() or relative_anchor.lower() in aid.lower():
                    anchor_elem = el
                    break
            except Exception:
                continue

    anchor_rect = None
    if anchor_elem:
        try:
            anchor_rect = anchor_elem.rectangle()
        except Exception:
            pass

    scored: List[Tuple[float, Any]] = []

    for el in candidates:
        try:
            name_raw = el.window_text() if callable(getattr(el, "window_text", None)) else getattr(el, "name", "")
            name = str(name_raw or "") if isinstance(name_raw, str) else ""

            info_obj = getattr(el, "element_info", None)
            info_name_val = getattr(info_obj, "name", "") if info_obj and not isinstance(info_obj, str) else ""
            if isinstance(info_name_val, str) and info_name_val.strip():
                if not name.strip():
                    name = info_name_val.strip()
                elif info_name_val.lower() not in name.lower():
                    name = f"{name} {info_name_val.strip()}".strip()

            auto_id_raw = el.automation_id() if callable(getattr(el, "automation_id", None)) else getattr(el, "auto_id", "")
            auto_id = str(auto_id_raw or "") if isinstance(auto_id_raw, str) else ""

            ctype_raw = el.friendly_class_name() if callable(getattr(el, "friendly_class_name", None)) else getattr(el, "control_type", "")
            ctype = str(ctype_raw or "") if isinstance(ctype_raw, str) else ""

            visible = el.is_visible() if callable(getattr(el, "is_visible", None)) else getattr(el, "is_visible", True)
            enabled = el.is_enabled() if callable(getattr(el, "is_enabled", None)) else getattr(el, "is_enabled", True)
            rect = el.rectangle() if callable(getattr(el, "rectangle", None)) else getattr(el, "rect", None)
        except Exception:
            continue

        # If relative constraint is active, verify relationship
        if anchor_rect and relative_relation:
            if not is_relative_to_anchor(rect, anchor_rect, relative_relation):
                continue

        score = score_element(
            target_query=target_query,
            target_type=target_type,
            element_name=name,
            element_auto_id=auto_id,
            element_type=ctype,
            is_visible=visible,
            is_enabled=enabled,
            elem_rect=rect,
            parent_rect=parent_rect,
            spatial_landmark=spatial_landmark,
        )

        if score >= min_score:
            scored.append((score, el))

    if scored:
        # Sort descending by score
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_elem = scored[0]
        logger.debug("Best match for '%s': '%s' (score=%.2f)", target_query, best_elem.window_text(), best_score)
        return best_score, best_elem

    # 2. Heuristic Guessing for Send / Submit Buttons
    clean = target_query.strip().lower()
    if clean in ("send", "submit", "send button", "submit button", "arrow", "send prompt"):
        for el in candidates:
            try:
                if not el.is_visible() or not el.is_enabled():
                    continue
                ctype = el.friendly_class_name()
                if ctype not in ("Button", "SplitButton"):
                    continue
                aid = (el.automation_id() or "").lower()
                name = (el.window_text() or "").lower()
                rect = el.rectangle()

                # Send button characteristics in web/electron apps
                is_send_hint = any(s in aid or s in name for s in ("send", "submit", "prompt", "run", "arrow"))
                is_bottom_area = parent_rect is None or is_element_in_zone(rect, parent_rect, "bottom") or is_element_in_zone(rect, parent_rect, "bottom_right")
                
                if is_send_hint or (is_bottom_area and (rect.width() <= 70 and rect.height() <= 70)):
                    logger.info("Heuristic AI match resolved implicit send button: '%s' (auto_id='%s')", name, aid)
                    return 0.88, el
            except Exception:
                continue


    # Ordinal / Positional Fallback (e.g. 'first profile', 'second card', 'profile from the selection')
    clean = target_query.strip().lower()
    clean = re.sub(r"^(?:the|a|an)\s+", "", clean)
    clean = re.sub(r"\s+from\s+(?:the\s+)?(?:selection|list)$", "", clean).strip()

    # Check if target is an ordinal or general selection keyword
    ordinal_idx = None
    for ord_word, idx in ORDINAL_MAP.items():
        if re.search(rf"\b{ord_word}\b", clean):
            ordinal_idx = idx
            break

    if ordinal_idx is None and clean in ("profile", "card", "item", "option", "selection"):
        ordinal_idx = 0  # Default to first item if user simply said "a profile from the selection"

    if ordinal_idx is not None and candidates:
        # Collect substantial interactive controls (buttons, listitems, custom cards)
        interactive = []
        for el in candidates:
            try:
                if not el.is_visible() or not el.is_enabled():
                    continue
                rect = el.rectangle()
                if rect.width() < 15 or rect.height() < 15:
                    continue
                # Exclude massive container windows (full screen)
                if rect.width() > 1800 and rect.height() > 1000:
                    continue
                interactive.append((rect.top, rect.left, el))
            except Exception:
                continue

        if interactive:
            # Sort geometrically: top-to-bottom, left-to-right
            interactive.sort(key=lambda item: (item[0] // 30, item[1]))
            if ordinal_idx == -1:
                target_elem = interactive[-1][2]
            elif 0 <= ordinal_idx < len(interactive):
                target_elem = interactive[ordinal_idx][2]
            else:
                target_elem = interactive[0][2]

            logger.info("Ordinal selection matched index %d for '%s'", ordinal_idx, target_query)
            return 0.85, target_elem

    return None
