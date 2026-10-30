from unittest.mock import MagicMock, patch
import pytest

from handless.screen.uia_inspector import UIAInspector, CONTROL_TYPE_MAP


@pytest.fixture
def inspector():
    with patch("handless.screen.uia_inspector.Desktop"):
        insp = UIAInspector()
        return insp


def test_connect_to_app_with_pid(inspector):
    with patch("handless.screen.uia_inspector.Application") as mock_app_cls:
        mock_app = MagicMock()
        mock_app_cls.return_value = mock_app

        res = inspector.connect_to_app(1234, timeout=1.5)
        assert res == mock_app
        mock_app.connect.assert_called_once_with(process=1234, timeout=1.5)


def test_connect_to_app_with_title_regex(inspector):
    with patch("handless.screen.uia_inspector.Application") as mock_app_cls:
        mock_app = MagicMock()
        mock_app_cls.return_value = mock_app

        res = inspector.connect_to_app("Notepad", timeout=2.0)
        assert res == mock_app
        mock_app.connect.assert_called_once()
        args, kwargs = mock_app.connect.call_args
        assert kwargs["timeout"] == 2.0
        assert "(?i).*Notepad.*" in kwargs["title_re"]


def test_connect_to_app_failure_returns_none(inspector):
    with patch("handless.screen.uia_inspector.Application") as mock_app_cls:
        mock_app = MagicMock()
        mock_app.connect.side_effect = Exception("Process not found")
        mock_app_cls.return_value = mock_app

        res = inspector.connect_to_app("NonExistentApp")
        assert res is None


def test_find_element_targeted_found(inspector):
    mock_win = MagicMock()
    mock_spec = MagicMock()
    mock_elem = MagicMock()

    mock_spec.exists.return_value = True
    mock_spec.wrapper_object.return_value = mock_elem
    mock_win.child_window.return_value = mock_spec

    result = inspector.find_element_targeted(
        target_name="Save",
        target_type="button",
        window_spec=mock_win,
    )

    assert result == mock_elem
    mock_win.child_window.assert_called_once()
    _, kwargs = mock_win.child_window.call_args
    assert kwargs["control_type"] == "Button"
    assert "Save" in kwargs["title_re"]


def test_find_element_targeted_not_found(inspector):
    mock_win = MagicMock()
    mock_spec = MagicMock()
    mock_spec.exists.return_value = False
    mock_win.child_window.return_value = mock_spec

    result = inspector.find_element_targeted(
        target_name="Cancel",
        target_type="button",
        window_spec=mock_win,
    )
    assert result is None


def test_find_element_uses_targeted_first(inspector):
    targeted_elem = MagicMock()
    with patch.object(inspector, "find_element_targeted", return_value=targeted_elem) as mock_targeted:
        with patch.object(inspector, "get_active_window", return_value=MagicMock()):
            res = inspector.find_element("Save", target_type="button")
            assert res == targeted_elem
            mock_targeted.assert_called_once()


def test_find_element_falls_back_to_fuzzy(inspector):
    mock_win = MagicMock()
    cand1 = MagicMock()
    cand1.window_text.return_value = "Save File"
    cand1.friendly_class_name.return_value = "Button"
    mock_win.descendants.return_value = [cand1]

    with patch.object(inspector, "find_element_targeted", return_value=None):
        with patch.object(inspector, "get_active_window", return_value=mock_win):
            res = inspector.find_element("save", target_type="button")
            assert res == cand1


def test_dump_control_tree_prints_hierarchy(inspector):
    mock_win = MagicMock()
    mock_win.print_control_identifiers = lambda depth: print("  | [Button] Save")

    with patch.object(inspector, "get_active_window", return_value=mock_win):
        tree = inspector.dump_control_tree(depth=2)
        assert "[Button] Save" in tree


def test_dump_control_tree_no_window(inspector):
    with patch.object(inspector, "get_active_window", return_value=None):
        tree = inspector.dump_control_tree()
        assert "No active window" in tree


def test_control_type_mapping():
    assert CONTROL_TYPE_MAP["button"] == "Button"
    assert CONTROL_TYPE_MAP["edit"] == "Edit"
    assert CONTROL_TYPE_MAP["combobox"] == "ComboBox"
    assert CONTROL_TYPE_MAP["dropdown"] == "ComboBox"
    assert CONTROL_TYPE_MAP["tree"] == "TreeItem"
