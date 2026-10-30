"""Unit tests for Spatial Landmark and Relative Directional Tracking System."""

from unittest.mock import MagicMock
import pytest

from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType
from handless.screen.element_matcher import (
    find_best_element_match,
    is_element_in_zone,
    is_relative_to_anchor,
    normalize_zone_name,
    score_element,
)


class DummyRect:
    def __init__(self, left, top, right, bottom):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    def width(self):
        return self.right - self.left

    def height(self):
        return self.bottom - self.top


def test_normalize_zone_name():
    assert normalize_zone_name("top right corner") == "top_right"
    assert normalize_zone_name("upper right") == "top_right"
    assert normalize_zone_name("top-left corner") == "top_left"
    assert normalize_zone_name("bottom right area") == "bottom_right"
    assert normalize_zone_name("lower left") == "bottom_left"
    assert normalize_zone_name("center") == "center"
    assert normalize_zone_name("middle") == "center"
    assert normalize_zone_name(None) is None


def test_is_element_in_zone():
    parent = DummyRect(0, 0, 1000, 800)

    # Top right element
    el_tr = DummyRect(800, 50, 950, 90)
    assert is_element_in_zone(el_tr, parent, "top_right") is True
    assert is_element_in_zone(el_tr, parent, "bottom_left") is False

    # Bottom left element
    el_bl = DummyRect(50, 700, 150, 750)
    assert is_element_in_zone(el_bl, parent, "bottom_left") is True
    assert is_element_in_zone(el_bl, parent, "top_right") is False

    # Center element
    el_center = DummyRect(450, 380, 550, 420)
    assert is_element_in_zone(el_center, parent, "center") is True


def test_is_relative_to_anchor():
    anchor = DummyRect(400, 300, 500, 340)

    # Right of anchor
    el_right = DummyRect(520, 310, 580, 335)
    assert is_relative_to_anchor(el_right, anchor, "next_to") is True
    assert is_relative_to_anchor(el_right, anchor, "right_of") is True

    # Below anchor
    el_below = DummyRect(420, 360, 480, 400)
    assert is_relative_to_anchor(el_below, anchor, "below") is True
    assert is_relative_to_anchor(el_below, anchor, "above") is False

    # Near anchor
    el_near = DummyRect(450, 350, 490, 370)
    assert is_relative_to_anchor(el_near, anchor, "near") is True


def test_find_best_element_match_spatial_landmark():
    parent_rect = DummyRect(0, 0, 1000, 800)

    el1 = MagicMock()
    el1.window_text.return_value = "Close"
    el1.automation_id.return_value = "btn_close_left"
    el1.friendly_class_name.return_value = "Button"
    el1.is_visible.return_value = True
    el1.is_enabled.return_value = True
    el1.rectangle.return_value = DummyRect(50, 50, 90, 80)  # top left

    el2 = MagicMock()
    el2.window_text.return_value = "Close"
    el2.automation_id.return_value = "btn_close_right"
    el2.friendly_class_name.return_value = "Button"
    el2.is_visible.return_value = True
    el2.is_enabled.return_value = True
    el2.rectangle.return_value = DummyRect(920, 30, 960, 60)  # top right

    # Target: top right
    res = find_best_element_match(
        target_query="close",
        candidates=[el1, el2],
        spatial_landmark="top_right",
        parent_rect=parent_rect,
    )
    assert res is not None
    _, best = res
    assert best == el2


def test_find_best_element_match_heuristic_send_button():
    parent_rect = DummyRect(0, 0, 1000, 800)

    # An icon button with no text but auto_id='run_prompt' in bottom right
    send_btn = MagicMock()
    send_btn.window_text.return_value = ""
    send_btn.automation_id.return_value = "btn_send_arrow"
    send_btn.friendly_class_name.return_value = "Button"
    send_btn.is_visible.return_value = True
    send_btn.is_enabled.return_value = True
    send_btn.rectangle.return_value = DummyRect(850, 720, 890, 750)

    res = find_best_element_match(
        target_query="send",
        candidates=[send_btn],
        parent_rect=parent_rect,
    )
    assert res is not None
    score, elem = res
    assert elem == send_btn
    assert score >= 0.85


def test_local_parser_spatial_landmarks():
    parser = LocalRuleParser()

    # 1. "click the button in the top right corner"
    res1 = parser.interpret("click the button in the top right corner")
    assert res1 is not None
    assert res1.actions[0].action_type == ActionType.CLICK
    assert res1.actions[0].target == "button"
    assert res1.actions[0].target_type == "button"
    assert res1.actions[0].spatial_landmark == "top_right"

    # 2. "click the x in top right"
    res2 = parser.interpret("click the x in top right")
    assert res2 is not None
    assert res2.actions[0].action_type == ActionType.CLICK
    assert res2.actions[0].target == "x"
    assert res2.actions[0].spatial_landmark == "top_right"

    # 3. "click the profile icon in the top left"
    res3 = parser.interpret("click the profile icon in the top left")
    assert res3 is not None
    assert res3.actions[0].action_type == ActionType.CLICK
    assert res3.actions[0].spatial_landmark == "top_left"

    # 4. "click the send button below how are you"
    res4 = parser.interpret("click the send button below how are you")
    assert res4 is not None
    assert res4.actions[0].action_type == ActionType.CLICK
    assert res4.actions[0].target == "send"
    assert res4.actions[0].relative_relation == "below"
    assert res4.actions[0].relative_anchor == "how are you"

    # 5. "click the button next to sonu"
    res5 = parser.interpret("click the button next to sonu")
    assert res5 is not None
    assert res5.actions[0].action_type == ActionType.CLICK
    assert res5.actions[0].target == "button"
    assert res5.actions[0].relative_relation == "next_to"
    assert res5.actions[0].relative_anchor == "sonu"

