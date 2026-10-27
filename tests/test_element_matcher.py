import pytest
from handless.screen.element_matcher import score_element, find_best_element_match


class MockUIElement:
    def __init__(self, name: str, auto_id: str, class_name: str, visible: bool = True, enabled: bool = True):
        self._name = name
        self._auto_id = auto_id
        self._class = class_name
        self._visible = visible
        self._enabled = enabled

    def window_text(self):
        return self._name

    def automation_id(self):
        return self._auto_id

    def friendly_class_name(self):
        return self._class

    def is_visible(self):
        return self._visible

    def is_enabled(self):
        return self._enabled


def test_score_element_exact():
    score = score_element(
        target_query="Search",
        target_type="button",
        element_name="Search",
        element_auto_id="searchBtn",
        element_type="Button",
    )
    assert score >= 1.0


def test_score_element_fuzzy_with_type():
    score = score_element(
        target_query="submit button",
        target_type="button",
        element_name="Submit Form",
        element_auto_id="btnSubmit",
        element_type="Button",
    )
    assert score >= 0.85


def test_find_best_element_match():
    candidates = [
        MockUIElement("Cancel", "cancelBtn", "Button"),
        MockUIElement("Search the web", "searchBox", "Edit"),
        MockUIElement("Search", "btnSearch", "Button"),
        MockUIElement("Settings", "settingsBtn", "Button"),
    ]

    match = find_best_element_match(
        target_query="search",
        candidates=candidates,
        target_type="button",
    )
    assert match is not None
    score, elem = match
    assert elem.window_text() == "Search"
    assert elem.friendly_class_name() == "Button"
