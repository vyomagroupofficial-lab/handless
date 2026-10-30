"""Automatic detection of active meeting applications (Zoom, Google Meet, WhatsApp, Teams).
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Application signatures: (keywords in window title, friendly name, brand color, svg icon name)
MEETING_APP_PATTERNS = [
    (["zoom meeting", "zoom workplace", "zoom cloud meetings"], "Zoom", "#2D8CFF", "zoom"),
    (["meet -", "meet.google.com", "google meet"], "Google Meet", "#00897B", "meet"),
    (["microsoft teams", "teams meeting"], "Microsoft Teams", "#6264A7", "teams"),
    (["whatsapp", "whatsapp video call", "whatsapp voice call"], "WhatsApp", "#25D366", "whatsapp"),
    (["discord", "- discord"], "Discord", "#5865F2", "discord"),
    (["slack call", "slack huddle", "huddle in #"], "Slack Huddle", "#E01E5A", "slack"),
    (["webex", "cisco webex"], "Cisco Webex", "#00BCEB", "webex"),
    (["skype"], "Skype", "#00AFF0", "skype"),
]


def detect_active_meeting_app() -> Tuple[str, str, str]:
    """Detect if any meeting application or browser tab is running on the desktop.

    Returns:
        Tuple of (App Name, Brand Color Hex, Icon Key)
        e.g. ("Zoom", "#2D8CFF", "zoom") or ("General Call", "#10B981", "call")
    """
    try:
        import pygetwindow as gw  # type: ignore

        windows = gw.getAllTitles()
        for title in windows:
            if not title or not title.strip():
                continue
            lower_title = title.lower()
            for keywords, app_name, brand_color, icon_key in MEETING_APP_PATTERNS:
                if any(kw in lower_title for kw in keywords):
                    logger.debug("Detected active meeting window: '%s' -> %s", title, app_name)
                    return app_name, brand_color, icon_key
    except Exception as exc:
        logger.debug("Could not query window titles for meeting detection: %s", exc)

    return "General Call", "#10B981", "call"

