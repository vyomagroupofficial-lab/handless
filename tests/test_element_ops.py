from unittest.mock import MagicMock
import pytest

from handless.actions.element_ops import ElementOperations


@pytest.fixture
def ops():
    return ElementOperations()


def test_select_menu_item_via_menu_select(ops):
    mock_win = MagicMock()
    mock_win.menu_select = MagicMock()

    success = ops.select_menu_item(mock_win, "File->Save")
    assert success is True
    mock_win.menu_select.assert_called_once_with("File->Save")


def test_select_menu_item_via_select(ops):
    mock_elem = MagicMock(spec=["select"])
    mock_elem.select = MagicMock()

    success = ops.select_menu_item(mock_elem, "File")
    assert success is True
    mock_elem.select.assert_called_once()


def test_select_menu_item_via_click_fallback(ops):
    mock_elem = MagicMock(spec=["click_input"])
    mock_elem.click_input = MagicMock()

    success = ops.select_menu_item(mock_elem, "Edit")
    assert success is True
    mock_elem.click_input.assert_called_once()


def test_select_combo_item_via_select_arg(ops):
    mock_combo = MagicMock()
    mock_combo.select = MagicMock()

    success = ops.select_combo_item(mock_combo, "Bold")
    assert success is True
    mock_combo.select.assert_called_once_with("Bold")


def test_select_combo_item_fallback_to_edit(ops):
    mock_combo = MagicMock(spec=["set_edit_text"])
    mock_combo.set_edit_text = MagicMock()

    success = ops.select_combo_item(mock_combo, "14pt")
    assert success is True
    mock_combo.set_edit_text.assert_called_once_with("14pt")


def test_expand_tree_item(ops):
    mock_item = MagicMock()
    mock_item.expand = MagicMock()

    success = ops.expand_tree_item(mock_item)
    assert success is True
    mock_item.expand.assert_called_once()


def test_expand_tree_item_com_interface(ops):
    mock_item = MagicMock(spec=["iface_expand_collapse"])
    mock_item.iface_expand_collapse = MagicMock()

    success = ops.expand_tree_item(mock_item)
    assert success is True
    mock_item.iface_expand_collapse.Expand.assert_called_once()


def test_collapse_tree_item(ops):
    mock_item = MagicMock()
    mock_item.collapse = MagicMock()

    success = ops.collapse_tree_item(mock_item)
    assert success is True
    mock_item.collapse.assert_called_once()


def test_set_value_edit_text(ops):
    mock_elem = MagicMock()
    mock_elem.set_edit_text = MagicMock()

    success = ops.set_value(mock_elem, "New Text")
    assert success is True
    mock_elem.set_edit_text.assert_called_once_with("New Text")


def test_none_elements_return_false(ops):
    assert ops.select_menu_item(None, "File") is False
    assert ops.select_combo_item(None, "Val") is False
    assert ops.expand_tree_item(None) is False
    assert ops.collapse_tree_item(None) is False
    assert ops.set_value(None, "Val") is False
