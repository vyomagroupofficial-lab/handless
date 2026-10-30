"""Unit tests for Floating Copilot Action Widget."""

import os
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from handless.ui.floating_widget import FloatingCopilotWidget


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_floating_widget_creation(qapp):
    opened = []
    widget = FloatingCopilotWidget(
        on_open_sidebar=lambda: opened.append(True),
    )
    assert widget.width() == 58
    assert widget.height() == 58
    assert widget.orb is not None

    # Test click handler
    widget._handle_click()
    assert len(opened) == 1


def test_floating_widget_animation(qapp):
    widget = FloatingCopilotWidget()
    widget.show_animated()
    assert widget.isVisible()

    done = []
    widget.hide_animated(on_finish=lambda: done.append(True))
    assert widget._fade_anim.state() is not None


def test_floating_widget_hover_events(qapp):
    widget = FloatingCopilotWidget()
    assert widget._hovered is False

    # Simulate hover enter
    widget.enterEvent(None)
    assert widget._hovered is True
    assert widget.orb._is_active is True

    # Simulate hover leave
    widget.leaveEvent(None)
    assert widget._hovered is False
    assert widget.orb._is_active is False


def test_floating_widget_timer_lifecycle(qapp):
    """Timer should only run when widget is visible, preventing background paint crashes."""
    widget = FloatingCopilotWidget()
    # Initially hidden
    assert not widget.isVisible()
    assert not widget.bot_logo._timer.isActive()

    # Show widget -> timer starts
    widget.show()
    assert widget.bot_logo._timer.isActive()

    # Hide widget -> timer stops
    widget.hide()
    assert not widget.bot_logo._timer.isActive()


