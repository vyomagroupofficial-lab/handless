"""Fuzzy Element Matcher using rapidfuzz.

Ranks accessible UI controls against natural speech queries (e.g. 'search button',
'file menu', 'save') using string similarity, control type hints, and visibility.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

TYPE_ALIASES = {
    "button": ["button", "splitbutton"],
    "edit": ["edit", "document", "textbox"],
    "menu": ["menuitem", "menu", "menubar"],
    "tab": ["tabitem", "tab"],
    "link": ["hyperlink", "link"],
    "list": ["list", "listitem", "combobox"],
}


def score_element(
    target_query: str,
    target_type: Optional[str],
    element_name: str,
    element_auto_id: str,
    element_type: str,
    is_visible: bool = True,
    is_enabled: bool = True,
) -> float:
    """Calculate match score from 0.0 to 1.0."""
    if not is_visible or not is_enabled:
        return 0.0

    q = target_query.strip().lower()
    name = (element_name or "").strip().lower()
    auto_id = (element_auto_id or "").strip().lower()
    ctype = (element_type or "").strip().lower()

    if not q:
        return 0.0

    # 1. Exact match
    if q == name or q == auto_id:
        score = 1.0
    # 2. Substring containment
    elif q in name or name in q:
        score = 0.9
    elif auto_id and (q in auto_id or auto_id in q):
        score = 0.85
    # 3. Fuzzy ratio
    else:
        ratio = fuzz.token_sort_ratio(q, name) / 100.0
        partial = fuzz.partial_ratio(q, name) / 100.0
        score = max(ratio, partial)

    # 4. Control type bonus or penalty
    if target_type:
        tt = target_type.strip().lower()
        valid_types = TYPE_ALIASES.get(tt, [tt])
        if any(vt in ctype for vt in valid_types):
            score = min(1.0, score + 0.1)
        elif score > 0.5:
            score = max(0.0, score - 0.15)

    return score


def find_best_element_match(
    target_query: str,
    candidates: List[Any],
    target_type: Optional[str] = None,
    min_score: float = 0.65,
) -> Optional[Tuple[float, Any]]:
    """Scan candidate UI elements and return the highest scoring match."""
    scored: List[Tuple[float, Any]] = []

    for el in candidates:
        try:
            name = el.window_text()
            auto_id = el.automation_id()
            ctype = el.friendly_class_name()
            visible = el.is_visible()
            enabled = el.is_enabled()
        except Exception:
            continue

        score = score_element(
            target_query=target_query,
            target_type=target_type,
            element_name=name,
            element_auto_id=auto_id,
            element_type=ctype,
            is_visible=visible,
            is_enabled=enabled,
        )

        if score >= min_score:
            scored.append((score, el))

    if not scored:
        return None

    # Sort descending by score
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_elem = scored[0]
    logger.debug("Best match for '%s': '%s' (score=%.2f)", target_query, best_elem.window_text(), best_score)
    return best_score, best_elem
