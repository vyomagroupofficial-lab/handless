import pytest
from handless.screen.element_matcher import score_element, find_best_element_match


class MockRect:
    def __init__(self, left=100, top=100, width=120, height=80):
        self.left = left
        self.top = top
        self._w = width
        self._h = height

    def width(self):
        return self._w

    def height(self):
        return self._h


class MockUIElement:
    def __init__(self, name: str, auto_id: str, class_name: str, visible: bool = True, enabled: bool = True, rect: MockRect = None):
        self._name = name
        self._auto_id = auto_id
        self._class = class_name
        self._visible = visible
        self._enabled = enabled
        self._rect = rect or MockRect()

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

    def rectangle(self):
        return self._rect


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


def test_youtube_search_box_priority_over_button():
    candidates = [
        MockUIElement("Search", "search-icon-button", "Button"),
        MockUIElement("Search", "search-input", "Edit"),
    ]
    # When target_type is "edit"
    match = find_best_element_match(
        target_query="search",
        candidates=candidates,
        target_type="edit",
    )
    assert match is not None
    _, elem = match
    assert elem.friendly_class_name() == "Edit"
    assert elem.automation_id() == "search-input"

    # When query is "search" with no target_type, Edit should beat Button due to search input boost
    match_default = find_best_element_match(
        target_query="search",
        candidates=candidates,
        target_type=None,
    )
    assert match_default is not None
    _, elem_default = match_default
    assert elem_default.friendly_class_name() == "Edit"


def test_ff_matches_ffff_profile():
    candidates = [
        MockUIElement("Sonu", "profile-sonu", "Button"),
        MockUIElement("Vibepixel", "profile-vibepixel", "Button"),
        MockUIElement("ffff", "profile-ffff", "Button"),
    ]
    # Speech query with typo "the ff prfile"
    match = find_best_element_match(
        target_query="the ff prfile",
        candidates=candidates,
    )
    assert match is not None
    score, elem = match
    assert elem.window_text() == "ffff"
    assert score >= 0.85


def test_ordinal_and_selection_fallback():
    candidates = [
        MockUIElement("Sonu", "p1", "Button", rect=MockRect(left=200, top=100, width=100, height=100)),
        MockUIElement("Vibepixel", "p2", "Button", rect=MockRect(left=350, top=100, width=100, height=100)),
        MockUIElement("ffff", "p3", "Button", rect=MockRect(left=500, top=100, width=100, height=100)),
    ]
    # "first profile"
    m1 = find_best_element_match("first profile", candidates)
    assert m1 is not None
    assert m1[1].window_text() == "Sonu"

    # "second profile"
    m2 = find_best_element_match("second profile", candidates)
    assert m2 is not None
    assert m2[1].window_text() == "Vibepixel"

    # "a profile from the selection" -> defaults to first available
    m3 = find_best_element_match("a profile from the selection", candidates)
    assert m3 is not None
    assert m3[1].window_text() == "Sonu"


def test_whatsapp_contact_selection_priority_over_search_edit():
    """In WhatsApp/chat, selecting a contact matches the chat item (DataItem), never the search Edit box."""
    candidates = [
        # The search box currently contains "Vaishu"
        MockUIElement("Vaishu", "search-input", "Edit"),
        # The search results list contains the chat item
        MockUIElement(
            "Vaishu Yesterday Follow this link to join my WhatsApp group: https://chat.whatsapp.com/HDfTJ8BMcMaJmaUGYlbklT Pinned chat Starred chat",
            "chat-vaishu",
            "DataItem",
        ),
        MockUIElement("Vaishnavi Xavier's", "chat-vaishnavi", "DataItem"),
    ]

    # 1. With explicit target_type="contact"
    match_contact = find_best_element_match("vaishu", candidates, target_type="contact")
    assert match_contact is not None
    _, elem_contact = match_contact
    assert elem_contact.friendly_class_name() == "DataItem"
    assert "Yesterday" in elem_contact.window_text()

    # 2. With target_type=None, contact DataItem still beats the search Edit box
    match_none = find_best_element_match("vaishu", candidates, target_type=None)
    assert match_none is not None
    _, elem_none = match_none
    assert elem_none.friendly_class_name() == "DataItem"
    assert "Yesterday" in elem_none.window_text()


