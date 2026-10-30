"""Unit tests for Chrome DevTools Protocol (CDP) Bridge."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from handless.screen.cdp_bridge import CDPBridge


def test_cdp_bridge_offline():
    """When remote debugging port is closed, is_available returns False cleanly."""
    bridge = CDPBridge(port=9999)
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        assert bridge.is_available() is False
        assert bridge.get_open_tabs() == []


def test_cdp_bridge_open_tabs():
    """Retrieves and parses open browser tabs when CDP port is active."""
    sample_tabs = [
        {
            "id": "tab-1",
            "title": "WhatsApp",
            "url": "https://web.whatsapp.com/",
            "type": "page",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/tab-1",
        },
        {
            "id": "tab-2",
            "title": "Google Docs",
            "url": "https://docs.google.com/document/d/123",
            "type": "page",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/tab-2",
        },
        {
            "id": "bg-1",
            "title": "Extension Background",
            "url": "chrome-extension://xyz",
            "type": "background_page",
        },
    ]

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(sample_tabs).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    bridge = CDPBridge(port=9222)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert bridge.is_available() is True
        tabs = bridge.get_open_tabs()
        assert len(tabs) == 2  # Only page/app tabs
        assert tabs[0]["title"] == "WhatsApp"
        assert tabs[0]["url"] == "https://web.whatsapp.com/"

        # Find tab by URL substring
        wa_tab = bridge.find_tab_by_url("web.whatsapp.com")
        assert wa_tab is not None
        assert wa_tab["id"] == "tab-1"

        meta = bridge.query_page_meta("tab-1")
        assert meta.get("is_whatsapp_web") is True
        assert meta.get("status") == "connected"

