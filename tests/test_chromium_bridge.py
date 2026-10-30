"""Unit tests for Chromium & Browser Deep Tracking Bridge."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from handless.screen.chromium_bridge import (
    CHROMIUM_PROCESS_NAMES,
    CHROMIUM_WINDOW_CLASSES,
    is_chromium_window,
    partition_browser_elements,
    wake_chromium_accessibility,
)


def test_is_chromium_window_invalid():
    """Invalid HWNDs return False cleanly without crashing."""
    assert is_chromium_window(0) is False
    assert is_chromium_window(-1) is False


def test_is_chromium_window_class_match():
    """Matching Chromium window classes correctly identified."""
    with patch("win32gui.GetClassName", return_value="Chrome_WidgetWin_1"):
        with patch("win32process.GetWindowThreadProcessId", return_value=(0, 9999)):
            assert is_chromium_window(12345) is True


def test_is_chromium_window_process_match():
    """Chromium / Electron process names recognized."""
    with patch("win32gui.GetClassName", return_value="CustomWindowClass"):
        with patch("win32process.GetWindowThreadProcessId", return_value=(0, 8888)):
            with patch("win32api.OpenProcess", return_value=123):
                with patch("win32process.GetModuleFileNameEx", return_value="C:\\Program Files\\WhatsApp\\WhatsApp.exe"):
                    with patch("win32api.CloseHandle"):
                        assert is_chromium_window(54321) is True


def test_wake_chromium_accessibility():
    """Wake handshake triggers AccessibleObjectFromWindow on top-level and render targets."""
    mock_oleacc = MagicMock()
    # Simulate S_OK (0)
    mock_oleacc.AccessibleObjectFromWindow.return_value = 0

    with patch("ctypes.windll.oleacc", mock_oleacc):
        with patch("handless.screen.chromium_bridge.get_chromium_render_hwnds", return_value=[6789]):
            success = wake_chromium_accessibility(1234)
            # Should be called for both target 1234 and child render 6789
            assert mock_oleacc.AccessibleObjectFromWindow.call_count >= 1


def test_partition_browser_elements():
    """Elements partitioned into Browser Shell vs Inside-Page Web Content."""
    elements = [
        # Browser Toolbar Shell
        {
            "name": "Address and search bar",
            "control_type": "Edit",
            "rect": {"left": 100, "top": 45, "width": 800, "height": 30},
        },
        # Web Page DOM Content (e.g. WhatsApp Web chat item)
        {
            "name": "Vyoma Oversight",
            "control_type": "ListItem",
            "rect": {"left": 150, "top": 280, "width": 300, "height": 60},
        },
        # Web Page Input
        {
            "name": "Type a message",
            "control_type": "Edit",
            "rect": {"left": 450, "top": 850, "width": 600, "height": 45},
        },
    ]

    window_rect = {"left": 0, "top": 0, "width": 1920, "height": 1080}
    partitioned = partition_browser_elements(elements, window_title="WhatsApp - Google Chrome", window_rect=window_rect)

    assert len(partitioned) == 3

    # Toolbar item should be SHELL
    assert partitioned[0]["is_web_content"] is False
    assert partitioned[0]["source_tag"] == "[SHELL]"

    # WhatsApp chat item should be WEB
    assert partitioned[1]["is_web_content"] is True
    assert partitioned[1]["source_tag"] == "[WEB]"
    assert partitioned[1]["category"] == "web_dom"

    # WhatsApp input should be WEB
    assert partitioned[2]["is_web_content"] is True
    assert partitioned[2]["source_tag"] == "[WEB]"
