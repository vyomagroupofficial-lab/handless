"""Unit tests for Multi-Modal Resilient Locator Generator."""

from __future__ import annotations

import pytest

from handless.screen.locator_generator import (
    ResilientLocator,
    _find_nearest_label_anchor,
    generate_resilient_locator,
)


def test_generate_resilient_locator_tier1_auto_id():
    """Generates dynamic locator using unique AutomationId if present."""
    elem = {
        "name": "Submit Form",
        "auto_id": "btn_submit_order",
        "control_type": "Button",
        "rect": {"left": 200, "top": 400, "width": 100, "height": 35},
    }

    locator = generate_resilient_locator(elem)
    assert isinstance(locator, ResilientLocator)
    assert locator.tier1_dynamic["auto_id"] == "btn_submit_order"
    assert 'auto_id="btn_submit_order"' in locator.tier1_dynamic["code"]
    assert 'click "Submit Form"' == locator.voice_command


def test_generate_resilient_locator_tier2_anchor():
    """Identifies nearest structural label anchor above or to the left of input."""
    input_elem = {
        "name": "",
        "auto_id": "",
        "control_type": "Edit",
        "rect": {"left": 200, "top": 150, "width": 250, "height": 30},
    }

    siblings = [
        {
            "name": "Password",
            "control_type": "Text",
            "rect": {"left": 200, "top": 120, "width": 100, "height": 20},  # Directly above
        },
        {
            "name": "Cancel",
            "control_type": "Button",
            "rect": {"left": 800, "top": 900, "width": 80, "height": 30},  # Far away
        },
    ]

    locator = generate_resilient_locator(input_elem, siblings=siblings)
    assert locator.tier2_structural["anchor_name"] == "Password"
    assert locator.tier2_structural["relation"] == "below"
    assert 'relative_anchor="Password"' in locator.tier2_structural["code"]


def test_generate_resilient_locator_tier3_coordinate_normalization():
    """Calculates normalized percentage coordinates based on window bounds."""
    elem = {
        "name": "Send",
        "auto_id": "send_btn",
        "control_type": "Button",
        "rect": {"left": 500, "top": 500, "width": 100, "height": 50},
    }

    win_rect = {"left": 0, "top": 0, "width": 1000, "height": 1000}
    locator = generate_resilient_locator(elem, window_rect=win_rect)

    norm = locator.tier3_coordinate["normalized_pct"]
    assert norm is not None
    # Center x: 500 + 50 = 550 / 1000 = 0.55
    # Center y: 500 + 25 = 525 / 1000 = 0.525
    assert norm["x_pct"] == 0.55
    assert norm["y_pct"] == 0.525
    assert "x_pct=0.55" in locator.tier3_coordinate["code"]


def test_generate_resilient_locator_snippets_and_macro():
    """Generates runnable 3-tier Python code snippet and macro action dict."""
    elem = {
        "name": "Search or start a new chat",
        "auto_id": "search_input",
        "control_type": "Edit",
        "rect": {"left": 100, "top": 150, "width": 300, "height": 40},
    }

    locator = generate_resilient_locator(elem)
    # Check Python code contains Tier 1, Tier 2, and Tier 3 blocks
    assert "Tier 1: Dynamic UIA Match" in locator.python_code
    assert "Tier 2: Structural Proximity Match" in locator.python_code
    assert "Tier 3: Coordinate Fallback" in locator.python_code

    # Check macro action format
    macro = locator.macro_action
    assert macro["action"] == "type"
    assert macro["target"] == "Search or start a new chat"
    assert macro["coords"] == [250, 170]

