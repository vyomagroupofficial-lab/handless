"""Responsive layout helpers for the narrow copilot sidebar.

The sidebar screens are hand-built from rows of cards and pills. At the default
sidebar width those rows can ask for more horizontal space than the viewport
offers, which makes QScrollArea clip the right edge of every card. These helpers
let content shrink to the available width instead:

* ``FlowLayout`` wraps pill rows onto multiple lines.
* ``fit_to_width`` makes long labels word-wrap and lets inputs shrink.
* ``flow_pill_rows`` converts horizontal rows of pill buttons into flow rows.
* ``enable_horizontal_wheel`` lets the mouse wheel scroll horizontal strips.
* ``clear_inherited_frame_borders`` stops card ``QFrame { border }`` rules from
  drawing boxes around the labels inside the card (QLabel is a QFrame).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QWidget,
)


class FlowLayout(QLayout):
    """Left-to-right layout that wraps items onto new lines when out of width."""

    def __init__(self, parent: QWidget | None = None, h_spacing: int = 6, v_spacing: int = 6) -> None:
        super().__init__(parent)
        self._items = []
        self._h_spacing = h_spacing
        self._v_spacing = v_spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item) -> None:  # noqa: N802 (Qt API)
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QSize:  # noqa: N802
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_height = effective.x(), effective.y(), 0
        for item in self._items:
            if item.widget() is not None and item.widget().isHidden():
                continue
            hint = item.sizeHint()
            next_x = x + hint.width() + self._h_spacing
            if next_x - self._h_spacing > effective.right() + 1 and line_height > 0:
                x = effective.x()
                y += line_height + self._v_spacing
                next_x = x + hint.width() + self._h_spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + m.bottom()


def fit_to_width(root: QWidget, wrap_threshold: int = 110) -> None:
    """Let ``root``'s descendants shrink to the width they are given.

    Text labels wider than ``wrap_threshold`` get word wrap, line edits and
    combo boxes drop their content-based minimum widths.
    """
    for child in root.findChildren(QWidget):
        if isinstance(child, QLabel):
            if child.pixmap() is not None and not child.pixmap().isNull():
                continue
            if not child.text() or child.wordWrap():
                continue
            if child.sizeHint().width() > wrap_threshold:
                child.setWordWrap(True)
                policy = child.sizePolicy()
                policy.setHorizontalPolicy(QSizePolicy.Policy.Preferred)
                child.setSizePolicy(policy)
        elif isinstance(child, QLineEdit):
            if child.minimumWidth() == child.maximumWidth():
                # Fixed-width inputs (e.g. inline search) may shrink but keep their preferred size.
                preferred = child.minimumWidth()
                child.setMinimumWidth(60)
                child.setMaximumWidth(preferred)
            else:
                child.setMinimumWidth(0)
        elif isinstance(child, QComboBox):
            child.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            child.setMinimumContentsLength(6)


def _is_pill_row(layout: QHBoxLayout, min_buttons: int) -> bool:
    buttons = 0
    for i in range(layout.count()):
        item = layout.itemAt(i)
        widget = item.widget()
        if widget is None:
            if item.spacerItem() is not None:
                continue
            return False
        if not isinstance(widget, QPushButton) or not widget.text().strip():
            return False
        buttons += 1
    return buttons >= min_buttons


def _is_horizontal_strip(area: QAbstractScrollArea) -> bool:
    return area.verticalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff


def _inside_horizontal_strip(widget: QWidget) -> bool:
    parent = widget.parentWidget()
    while parent is not None:
        if isinstance(parent, QScrollArea) and _is_horizontal_strip(parent):
            return True
        parent = parent.parentWidget()
    return False


def flow_pill_rows(root: QWidget, min_buttons: int = 4) -> int:
    """Replace horizontal rows of text pill buttons under ``root`` with wrapping rows.

    Returns the number of rows converted.
    """
    converted = 0
    for host in [root, *root.findChildren(QWidget)]:
        layout = host.layout()
        if (
            isinstance(layout, QHBoxLayout)
            and _is_pill_row(layout, min_buttons)
            and not _inside_horizontal_strip(host)
        ):
            widgets = []
            while layout.count():
                item = layout.takeAt(0)
                if item.widget() is not None:
                    widgets.append(item.widget())
            spacing = max(layout.spacing(), 4)
            margins = layout.contentsMargins()
            QWidget().setLayout(layout)  # detach the old layout so the host accepts a new one
            flow = FlowLayout(host, h_spacing=spacing, v_spacing=spacing)
            flow.setContentsMargins(margins)
            for w in widgets:
                flow.addWidget(w)
            converted += 1
    return converted


class _HorizontalWheelFilter(QObject):
    """Maps vertical wheel motion onto the horizontal scrollbar of a strip."""

    def eventFilter(self, obj, event):  # noqa: N802
        if event.type() == QEvent.Type.Wheel:
            area = obj.parentWidget()
            bar = area.horizontalScrollBar() if isinstance(area, QScrollArea) else None
            if bar is not None and bar.maximum() > 0:
                delta = event.angleDelta().y() or event.angleDelta().x()
                bar.setValue(bar.value() - delta // 2)
                return True
        return False


_WHEEL_FILTER: _HorizontalWheelFilter | None = None


def enable_horizontal_wheel(root: QWidget) -> None:
    """Let the wheel scroll every horizontal-only scroll strip under ``root``."""
    global _WHEEL_FILTER
    if _WHEEL_FILTER is None:
        _WHEEL_FILTER = _HorizontalWheelFilter()
    for area in root.findChildren(QScrollArea):
        if _is_horizontal_strip(area):
            area.viewport().installEventFilter(_WHEEL_FILTER)


def _has_bare_qframe_rule(widget: QWidget) -> bool:
    sheet = widget.styleSheet().replace(" ", "")
    return "QFrame{" in sheet or "QFrame:hover{" in sheet


def clear_inherited_frame_borders(root: QWidget) -> None:
    """Give labels inside ``QFrame { ... }``-styled cards a transparent, borderless look."""
    for label in root.findChildren(QLabel):
        own = label.styleSheet()
        if "border" in own and "background" in own:
            continue
        parent = label.parentWidget()
        inherits_rule = False
        while parent is not None and parent is not root.parentWidget():
            if _has_bare_qframe_rule(parent):
                inherits_rule = True
                break
            parent = parent.parentWidget()
        if not inherits_rule:
            continue
        extra = []
        if "border" not in own:
            extra.append("border: none;")
        if "background" not in own:
            extra.append("background: transparent;")
        sep = "" if not own or own.rstrip().endswith(";") else ";"
        label.setStyleSheet(f"{own}{sep} {' '.join(extra)}".strip())
