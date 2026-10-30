"""Rich UI Automation Element Operations using pywinauto control wrappers.

Provides direct manipulation for menus, combo boxes, lists, tree items,
and edit controls beyond basic mouse clicks and keystrokes.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ElementOperations:
    """Dispatches rich UIA control operations via pywinauto wrappers."""

    def select_menu_item(self, window_or_element: Any, path: str) -> bool:
        """Select a menu path (e.g. 'File->Save As' or 'File') on window or element."""
        if window_or_element is None:
            return False

        # 1. Native menu_select on window or menu wrapper
        if hasattr(window_or_element, "menu_select"):
            try:
                window_or_element.menu_select(path)
                logger.info("Selected menu path '%s' via menu_select()", path)
                return True
            except Exception as exc:
                logger.debug("menu_select('%s') failed: %s", path, exc)

        # 2. Direct select() on MenuItemWrapper
        if hasattr(window_or_element, "select"):
            try:
                window_or_element.select()
                logger.info("Invoked select() on menu element")
                return True
            except Exception as exc:
                logger.debug("element.select() failed: %s", exc)

        # 3. Direct invoke() or click_input() fallback
        if hasattr(window_or_element, "invoke"):
            try:
                window_or_element.invoke()
                logger.info("Invoked menu element via invoke()")
                return True
            except Exception:
                pass

        if hasattr(window_or_element, "click_input"):
            try:
                window_or_element.click_input()
                logger.info("Clicked menu element via click_input()")
                return True
            except Exception as exc:
                logger.error("Failed to click menu element: %s", exc)

        return False

    def select_combo_item(self, element: Any, value: str) -> bool:
        """Select an item in a ComboBox or ListBox by text value or index."""
        if element is None:
            return False

        # 1. ComboBoxWrapper.select(item)
        if hasattr(element, "select"):
            try:
                element.select(value)
                logger.info("Selected '%s' in ComboBox/List via select()", value)
                return True
            except TypeError:
                # Some wrappers take 0 args for select() (e.g. ListItem)
                try:
                    element.select()
                    logger.info("Invoked 0-arg select() on item")
                    return True
                except Exception as ex2:
                    logger.debug("0-arg select() failed: %s", ex2)
            except Exception as exc:
                logger.debug("element.select('%s') failed: %s", value, exc)

        # 2. Edit-based combobox: set_edit_text
        if hasattr(element, "set_edit_text"):
            try:
                element.set_edit_text(value)
                logger.info("Set ComboBox text via set_edit_text('%s')", value)
                return True
            except Exception as exc:
                logger.debug("set_edit_text failed on ComboBox: %s", exc)

        # 3. pywinauto type_keys fallback
        if hasattr(element, "type_keys"):
            try:
                element.type_keys(value + "{ENTER}", with_spaces=True)
                logger.info("Typed '%s{ENTER}' into ComboBox", value)
                return True
            except Exception as exc:
                logger.error("Failed typing into ComboBox: %s", exc)

        return False

    def expand_tree_item(self, element: Any) -> bool:
        """Expand a TreeItem or expandable control."""
        if element is None:
            return False

        if hasattr(element, "expand"):
            try:
                element.expand()
                logger.info("Expanded element via expand()")
                return True
            except Exception as exc:
                logger.debug("element.expand() failed: %s", exc)

        if hasattr(element, "iface_expand_collapse"):
            try:
                element.iface_expand_collapse.Expand()
                logger.info("Expanded element via iface_expand_collapse.Expand()")
                return True
            except Exception as exc:
                logger.error("Expand pattern failed: %s", exc)

        # Click fallback if expandable
        if hasattr(element, "double_click_input"):
            try:
                element.double_click_input()
                return True
            except Exception:
                pass

        return False

    def collapse_tree_item(self, element: Any) -> bool:
        """Collapse a TreeItem or collapsable control."""
        if element is None:
            return False

        if hasattr(element, "collapse"):
            try:
                element.collapse()
                logger.info("Collapsed element via collapse()")
                return True
            except Exception as exc:
                logger.debug("element.collapse() failed: %s", exc)

        if hasattr(element, "iface_expand_collapse"):
            try:
                element.iface_expand_collapse.Collapse()
                logger.info("Collapsed element via iface_expand_collapse.Collapse()")
                return True
            except Exception as exc:
                logger.error("Collapse pattern failed: %s", exc)

        return False

    def set_value(self, element: Any, value: str) -> bool:
        """Directly set text value of an Edit or text-capable control."""
        if element is None:
            return False

        if hasattr(element, "set_edit_text"):
            try:
                element.set_edit_text(value)
                logger.info("Set text via set_edit_text()")
                return True
            except Exception as exc:
                logger.debug("set_edit_text() failed: %s", exc)

        if hasattr(element, "set_text"):
            try:
                element.set_text(value)
                logger.info("Set text via set_text()")
                return True
            except Exception as exc:
                logger.debug("set_text() failed: %s", exc)

        if hasattr(element, "set_window_text"):
            try:
                element.set_window_text(value)
                return True
            except Exception:
                pass

        return False
