"""User interface package."""
from .settings_panel import SettingsPanel
from .styles import CREAM_PALETTE, SETTINGS_PANEL_QSS, VOICE_BAR_QSS, SIDEBAR_QSS
from .tray_icon import HandlessTrayIcon
from .voice_bar import VoiceBar
from .sidebar import SidebarWindow
from .element_inspector import DesktopElementInspector, ElementHighlightOverlay
from .floating_widget import FloatingCopilotWidget

__all__ = [
    "CREAM_PALETTE",
    "HandlessTrayIcon",
    "SETTINGS_PANEL_QSS",
    "SettingsPanel",
    "VOICE_BAR_QSS",
    "VoiceBar",
    "SIDEBAR_QSS",
    "SidebarWindow",
    "DesktopElementInspector",
    "ElementHighlightOverlay",
    "FloatingCopilotWidget",
]
